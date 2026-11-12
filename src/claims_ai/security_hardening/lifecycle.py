"""Bounded authenticated SQLite lifecycle ledger. It stores no credentials or sessions."""

import hmac
import json
import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from hashlib import sha256
from pathlib import Path
from threading import RLock
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from claims_ai.identity.keys import epoch
from claims_ai.models import Contract, Sha256
from claims_ai.security_hardening.contracts import Anchor, Grant, Permission

ZERO = "0" * 64
FORMAT = "m21-lifecycle-v1"
DDL = (
    "CREATE TABLE context (format TEXT NOT NULL, binding TEXT NOT NULL)",
    "CREATE TABLE events (revision INTEGER PRIMARY KEY, payload TEXT NOT NULL, mac TEXT NOT NULL)",
    "CREATE TRIGGER immutable_update BEFORE UPDATE ON events "
    "BEGIN SELECT RAISE(ABORT,'append_only'); END",
    "CREATE TRIGGER immutable_delete BEFORE DELETE ON events "
    "BEGIN SELECT RAISE(ABORT,'append_only'); END",
)


class LifecycleError(ValueError):
    def __init__(self) -> None:
        super().__init__("lifecycle_unavailable_or_denied")


class Event(Contract):
    revision: Annotated[int, Field(strict=True, ge=1, le=256)]
    action: Literal["issue", "revoke", "disable"]
    grant: Grant | None = None
    target: UUID
    occurred_at: Annotated[int, Field(strict=True, ge=0)]
    previous: Sha256

    @model_validator(mode="after")
    def exact_payload(self) -> Self:
        if (self.action == "issue") != (self.grant is not None):
            raise ValueError("lifecycle payload mismatch")
        if self.grant is not None and self.target != self.grant.grant_id:
            raise ValueError("lifecycle target mismatch")
        return self


def encoded(event: Event) -> str:
    return json.dumps(event.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))


def rows(connection: sqlite3.Connection) -> list[tuple[object, ...]]:
    return connection.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()


class Lifecycle:
    """Explicit creation only; reopen requires the SAME independent context and integrity key.

    An independent anchor detects coherent rollback. This is a trusted-host local
    ledger, not WORM storage, a credential vault, or a cross-service transaction.
    """

    def __init__(
        self,
        path: Path,
        *,
        context_sha256: str,
        integrity_key: bytes,
        create: bool = False,
        anchor: Anchor | None = None,
        clock: Callable[[], int] = epoch,
    ) -> None:
        self.path = path.parent.resolve(strict=True) / path.name
        if (
            len(context_sha256) != 64
            or any(c not in "0123456789abcdef" for c in context_sha256)
            or not isinstance(integrity_key, bytes)
            or len(integrity_key) != 32
        ):
            raise LifecycleError()
        if not create and anchor is None:
            raise LifecycleError()
        self.context, self._key = context_sha256, integrity_key
        self._clock, self._last, self._lock = clock, -1, RLock()
        self._anchor = Anchor.model_validate(anchor) if anchor else Anchor(revision=0, head=ZERO)
        with sqlite3.connect(":memory:") as reference:
            for sql in DDL:
                reference.execute(sql)
            self._schema = rows(reference)
        self._private_parent()
        if create:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            try:
                with sqlite3.connect(self.path) as connection:
                    for sql in DDL:
                        connection.execute(sql)
                    connection.execute("PRAGMA user_version=1")
                    connection.execute("INSERT INTO context VALUES (?,?)", (FORMAT, self.context))
            except Exception:
                raise LifecycleError() from None
        # Never initialize, truncate, repair or fallback on reopen failure.
        with self._transaction() as connection:
            self._read(connection)

    def _private_parent(self) -> None:
        parent = self.path.parent.stat()
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.geteuid()
            or parent.st_mode & 0o077
        ):
            raise LifecycleError()

    def _now(self) -> int:
        now = self._clock()
        if type(now) is not int or now < 0 or now < self._last:
            self._last = 2**63
            raise LifecycleError()
        self._last = now
        return now

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            connection = None
            try:
                self._private_parent()
                info = self.path.stat(follow_symlinks=False)
                if (
                    not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.geteuid()
                    or info.st_mode & 0o077
                    or info.st_nlink != 1
                    or not 0 < info.st_size <= 1048576
                ):
                    raise LifecycleError()
                connection = sqlite3.connect(
                    self.path.as_uri() + "?mode=rw", uri=True, timeout=0.5, isolation_level=None
                )
                connection.execute("PRAGMA trusted_schema=OFF")
                connection.execute("PRAGMA synchronous=FULL")
                if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
                    raise LifecycleError()
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.execute("COMMIT")
            except Exception:
                if connection is not None and connection.in_transaction:
                    connection.execute("ROLLBACK")
                raise LifecycleError() from None
            finally:
                if connection is not None:
                    connection.close()

    def _mac(self, payload: str) -> str:
        return hmac.new(
            self._key, (FORMAT + "/" + self.context + "/" + payload).encode(), sha256
        ).hexdigest()

    def _read(
        self, connection: sqlite3.Connection
    ) -> tuple[dict[UUID, Grant], set[UUID], set[UUID], list[Event], str]:
        if (
            rows(connection) != self._schema
            or connection.execute("PRAGMA user_version").fetchone() != (1,)
            or connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]
            or connection.execute("SELECT * FROM context").fetchall() != [(FORMAT, self.context)]
        ):
            raise LifecycleError()
        raw = connection.execute("SELECT * FROM events ORDER BY revision LIMIT 257").fetchall()
        if len(raw) > 256:
            raise LifecycleError()
        grants: dict[UUID, Grant] = {}
        revoked: set[UUID] = set()
        disabled: set[UUID] = set()
        events: list[Event] = []
        previous, last_time = ZERO, 0
        anchor_ok = self._anchor == Anchor(revision=0, head=ZERO)
        for index, (revision, payload, mac) in enumerate(raw, 1):
            if len(payload) > 8192 or not hmac.compare_digest(self._mac(payload), mac):
                raise LifecycleError()
            e = Event.model_validate_json(payload)
            if (
                encoded(e) != payload
                or revision != index
                or e.revision != index
                or e.previous != previous
                or e.occurred_at < last_time
            ):
                raise LifecycleError()
            if e.action == "issue":
                g = e.grant
                if (
                    g is None
                    or g.grant_id in grants
                    or g.principal_id in disabled
                    or g.issued_at != e.occurred_at
                    or len(grants) >= 64
                ):
                    raise LifecycleError()
                grants[g.grant_id] = g
            elif e.action == "revoke":
                if e.target not in grants or e.target in revoked:
                    raise LifecycleError()
                revoked.add(e.target)
            else:
                if e.target in disabled or len(disabled) >= 64:
                    raise LifecycleError()
                disabled.add(e.target)
            previous, last_time = mac, e.occurred_at
            if self._anchor.revision == index and self._anchor.head == mac:
                anchor_ok = True
            events.append(e)
        if not anchor_ok or self._now() < last_time:
            raise LifecycleError()
        # Remember the newest verified head in this instance as a local rollback floor.
        self._anchor = Anchor(revision=len(events), head=previous)
        return grants, revoked, disabled, events, previous

    def checkpoint(self) -> Anchor:
        with self._transaction() as connection:
            self._read(connection)
            return self._anchor

    def _append(
        self,
        action: Literal["issue", "revoke", "disable"],
        target: UUID,
        grant: Grant | None = None,
    ) -> None:
        with self._transaction() as connection:
            grants, revoked, disabled, events, previous = self._read(connection)
            if len(events) >= 256:
                raise LifecycleError()
            now = self._now()
            if action == "issue":
                if (
                    grant is None
                    or grant.grant_id in grants
                    or grant.principal_id in disabled
                    or grant.issued_at != now
                    or len(grants) >= 64
                ):
                    raise LifecycleError()
            elif action == "revoke":
                if target not in grants or target in revoked:
                    raise LifecycleError()
            elif target in disabled or len(disabled) >= 64:
                raise LifecycleError()
            event = Event(
                revision=len(events) + 1,
                action=action,
                target=target,
                grant=grant,
                occurred_at=now,
                previous=previous,
            )
            payload = encoded(event)
            connection.execute(
                "INSERT INTO events VALUES (?,?,?)", (event.revision, payload, self._mac(payload))
            )
            # _read replays semantic constraints and verifies the uncommitted new event.
            self._read(connection)

    def issue(self, grant: Grant) -> None:
        grant = Grant.model_validate(grant)
        self._append("issue", grant.grant_id, grant)

    def revoke(self, grant_id: UUID) -> None:
        self._append("revoke", grant_id)

    def disable(self, principal_id: UUID) -> None:
        self._append("disable", principal_id)

    def require(self, grant: Grant, permissions: frozenset[Permission]) -> None:
        grant = Grant.model_validate(grant)
        with self._transaction() as connection:
            grants, revoked, disabled, _, _ = self._read(connection)
            now = self._now()
            if (
                grants.get(grant.grant_id) != grant
                or grant.grant_id in revoked
                or grant.principal_id in disabled
                or not grant.issued_at <= now < grant.expires_at
                or not permissions
                or not permissions <= set(grant.permissions)
            ):
                raise LifecycleError()
