"Bounded SQLite transactions and independently replayed projections; no cloud store."

import os
import sqlite3
import stat
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid5

from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.contracts import PrincipalKind
from claims_ai.models import Contract
from claims_ai.outcomes.authority import Authority, PublicationPermit
from claims_ai.outcomes.contracts import Action, AuditEvent, Command, OutcomeError, StoredCase
from claims_ai.outcomes.reducer import HOST_ACTIONS, reduce
from claims_ai.rules.specification import digest
from claims_ai.workflow.engine import code_fingerprint

NS = UUID("20202020-2020-4020-8020-202020202020")
ZERO = "0" * 64
TABLES = {
    "meta": "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)",
    "cases": (
        "CREATE TABLE cases (claim_id TEXT PRIMARY KEY, revision INTEGER NOT "
        "NULL, payload TEXT NOT NULL)"
    ),
    "artifacts": "CREATE TABLE artifacts (approval_id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
    "assessments": (
        "CREATE TABLE assessments (approval_id TEXT PRIMARY KEY, claim_id TEXT "
        "NOT NULL REFERENCES cases(claim_id), assessment_id TEXT NOT NULL UNIQUE,"
        " payload TEXT NOT NULL)"
    ),
    "decisions": (
        "CREATE TABLE decisions (event_id TEXT PRIMARY KEY REFERENCES "
        "audit(event_id), claim_id TEXT NOT NULL, payload TEXT NOT NULL)"
    ),
    "assignments": (
        "CREATE TABLE assignments (claim_id TEXT NOT NULL REFERENCES "
        "cases(claim_id), role TEXT NOT NULL, payload TEXT NOT NULL, PRIMARY "
        "KEY(claim_id, role))"
    ),
    "audit": (
        "CREATE TABLE audit (event_id TEXT PRIMARY KEY, claim_id TEXT NOT NULL "
        "REFERENCES cases(claim_id), revision INTEGER NOT NULL, payload TEXT NOT "
        "NULL, UNIQUE(claim_id, revision))"
    ),
    "receipts": (
        "CREATE TABLE receipts (claim_id TEXT NOT NULL, actor_id TEXT NOT NULL, "
        "request_id TEXT NOT NULL, request_sha256 TEXT NOT NULL, event_id TEXT "
        "NOT NULL UNIQUE REFERENCES audit(event_id), PRIMARY KEY(claim_id, "
        "actor_id, request_id))"
    ),
    "outbox": (
        "CREATE TABLE outbox (event_id TEXT PRIMARY KEY REFERENCES "
        "audit(event_id), claim_id TEXT NOT NULL, payload TEXT NOT NULL, status "
        "TEXT NOT NULL, attempts INTEGER NOT NULL)"
    ),
    "delivery_events": (
        "CREATE TABLE delivery_events (event_id TEXT NOT NULL REFERENCES "
        "outbox(event_id), attempt INTEGER NOT NULL, result TEXT NOT NULL, "
        "PRIMARY KEY(event_id, attempt))"
    ),
    "deliveries": (
        "CREATE TABLE deliveries (event_id TEXT PRIMARY KEY REFERENCES "
        "outbox(event_id), event_sha256 TEXT NOT NULL)"
    ),
}
IMMUTABLE = (
    "artifacts",
    "assessments",
    "decisions",
    "audit",
    "receipts",
    "delivery_events",
    "deliveries",
)


def schema(connection: sqlite3.Connection) -> None:
    for statement in TABLES.values():
        connection.execute(statement)
    for table in IMMUTABLE:
        for operation in ("UPDATE", "DELETE"):
            connection.execute(
                f"CREATE TRIGGER {table}_{operation.lower()} BEFORE {operation} ON {table} "
                "BEGIN SELECT RAISE(ABORT, 'append_only'); END"
            )
    connection.execute("PRAGMA user_version=1")


def schema_rows(connection: sqlite3.Connection) -> list[tuple[object, ...]]:
    return connection.execute(
        "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()


def encoded(value: Contract) -> str:
    return json_bytes(value.model_dump(mode="json")).decode()


def decode[T: Contract](kind: type[T], raw: str) -> T:
    if len(raw) > 12582912:
        raise OutcomeError("storage_capacity")
    value = kind.model_validate_json(raw)
    if encoded(value) != raw:
        raise OutcomeError("noncanonical_storage")
    return value


def utc_now() -> datetime:
    return datetime.now(UTC)


class OutcomeStore:
    """Each operation opens a connection; BEGIN IMMEDIATE supplies cross-process CAS.

    The host independently reprovisions approval sources and current sessions. SQLite
    data never issues credentials. No automatic schema/runtime migration or repair.
    """

    def __init__(
        self,
        path: Path,
        authority: Authority,
        *,
        create: bool = False,
        clock: Callable[[], datetime] = utc_now,
        fault: Callable[[str], None] = lambda point: None,
        expected_heads: dict[str, str] | None = None,
    ) -> None:
        self.path = path.parent.resolve(strict=True) / path.name
        self.authority, self.clock, self.fault = authority, clock, fault
        parent = self.path.parent.stat(follow_symlinks=False)
        if (
            not stat.S_ISDIR(parent.st_mode)
            or parent.st_uid != os.geteuid()
            or parent.st_mode & 0o077
        ):
            raise OutcomeError("private_storage_directory_required")
        if create:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            os.close(fd)
            with sqlite3.connect(self.path) as connection:
                schema(connection)
                connection.executemany(
                    "INSERT INTO meta VALUES (?,?)",
                    [("format", "m20-sqlite-v1"), ("runtime", code_fingerprint())],
                )
        with self.transaction() as connection:
            states, events = self.verify(connection)
            if (
                expected_heads is not None
                and {k: v[-1].event_sha256 for k, v in events.items()} != expected_heads
            ):
                raise OutcomeError("external_head_mismatch")
            del states

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        info = self.path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or info.st_nlink != 1
            or info.st_size > 67108864
        ):
            raise OutcomeError("invalid_storage_file")
        connection: sqlite3.Connection | None = None
        try:
            connection = sqlite3.connect(f"{self.path.as_uri()}?mode=rw", uri=True, timeout=0.5)
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA synchronous=FULL")
            connection.execute("PRAGMA trusted_schema=OFF")
            if connection.execute("PRAGMA journal_mode").fetchone() != ("delete",):
                raise OutcomeError("incompatible_journal_mode")
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except OutcomeError:
            raise
        except ValueError as failure:
            raise OutcomeError("corrupt_or_invalid_state") from failure
        except sqlite3.Error as failure:
            raise OutcomeError("storage_unavailable_or_corrupt") from failure
        finally:
            if connection is not None:
                connection.close()  # rolls back any transaction that did not commit

    def verify(
        self, c: sqlite3.Connection
    ) -> tuple[dict[str, StoredCase], dict[str, list[AuditEvent]]]:
        with sqlite3.connect(":memory:") as reference:
            schema(reference)
            if schema_rows(c) != schema_rows(reference) or c.execute(
                "PRAGMA user_version"
            ).fetchone() != (1,):
                raise OutcomeError("incompatible_schema")
        if (
            c.execute("PRAGMA quick_check").fetchall() != [("ok",)]
            or c.execute("PRAGMA foreign_key_check").fetchall()
        ):
            raise OutcomeError("corrupt_storage")
        if dict(c.execute("SELECT key,value FROM meta")) != {
            "format": "m20-sqlite-v1",
            "runtime": code_fingerprint(),
        }:
            raise OutcomeError("incompatible_runtime")
        rows = c.execute(
            "SELECT event_id,claim_id,revision,payload FROM audit ORDER BY claim_id,revision"
        ).fetchall()
        if len(rows) > 256 or c.execute("SELECT COUNT(*) FROM cases").fetchone()[0] > 8:
            raise OutcomeError("storage_capacity")
        states: dict[str, StoredCase] = {}
        events: dict[str, list[AuditEvent]] = {}
        expected: dict[str, list[tuple[object, ...]]] = {
            k: []
            for k in (
                "cases",
                "artifacts",
                "assessments",
                "assignments",
                "decisions",
                "receipts",
                "outbox",
                "deliveries",
            )
        }
        artifacts: dict[str, str] = {}
        for event_id, claim_id, revision, raw in rows:
            event = decode(AuditEvent, raw)
            before = states.get(claim_id)
            prior = events.get(claim_id, [])
            if (
                event.command.claim_id != claim_id
                or event.event_id != UUID(event_id)
                or event.after.revision != revision
                or event.previous_sha256 != (prior[-1].event_sha256 if prior else ZERO)
            ):
                raise OutcomeError("audit_identity_mismatch")
            if event.event_id != uuid5(
                NS, f"{claim_id}/{event.actor.principal_id}/{event.command.request_id}"
            ):
                raise OutcomeError("audit_identity_mismatch")
            if prior and event.command.occurred_at < prior[-1].command.occurred_at:
                raise OutcomeError("audit_time_mismatch")
            after, transitions = reduce(self.authority, before, event.command, event.actor)
            if event.after != after or event.transitions != transitions:
                raise OutcomeError("audit_semantics_mismatch")
            states[claim_id] = after
            events.setdefault(claim_id, []).append(event)
            if event.command.action in {Action.REGISTER, Action.REVALIDATE}:
                approval = self.authority.approval(after.approval_id)
                artifacts[str(approval.approval_id)] = encoded(approval.bundle)
            if event.command.action == Action.PUBLISH:
                approval = self.authority.approval(after.approval_id)
                expected["assessments"].append(
                    (
                        str(approval.approval_id),
                        claim_id,
                        approval.assessment.assessment_id,
                        encoded(approval.assessment),
                    )
                )
            if event.command.decision is not None:
                expected["decisions"].append((event_id, claim_id, encoded(event.command.decision)))
            expected["receipts"].append(
                (
                    claim_id,
                    str(event.actor.principal_id),
                    str(event.command.request_id),
                    digest(event.command.model_dump(mode="json")),
                    event_id,
                )
            )
            payload = json_bytes(
                {
                    "claim_id": claim_id,
                    "event_sha256": event.event_sha256,
                    "purpose": "local_synthetic_audit_projection_only",
                }
            ).decode()
            deliveries = c.execute(
                "SELECT attempt,result FROM delivery_events WHERE event_id=? ORDER BY attempt",
                (event_id,),
            ).fetchall()
            status = "pending"
            for attempt, (number, result) in enumerate(deliveries, start=1):
                if (
                    number != attempt
                    or attempt > 3
                    or status != "pending"
                    or result not in {"delivered", "unavailable"}
                ):
                    raise OutcomeError("delivery_history_invalid")
                status = (
                    "delivered" if result == "delivered" else "dead" if attempt == 3 else "pending"
                )
            expected["outbox"].append((event_id, claim_id, payload, status, len(deliveries)))
            if status == "delivered":
                expected["deliveries"].append((event_id, event.event_sha256))
        expected["artifacts"] = list(artifacts.items())
        for claim_id, state in states.items():
            expected["cases"].append((claim_id, state.revision, encoded(state)))
            expected["assignments"].extend(
                (claim_id, a.principal.role.value if a.principal.role else "", encoded(a))
                for a in state.assignments
            )
        for table, wanted in expected.items():
            if sorted(c.execute(f"SELECT * FROM {table}").fetchall()) != sorted(wanted):
                raise OutcomeError("projection_or_artifact_mismatch")
        total = sum(
            c.execute(f"SELECT COALESCE(SUM(LENGTH(payload)),0) FROM {t}").fetchone()[0]
            for t in (
                "cases",
                "artifacts",
                "assessments",
                "decisions",
                "assignments",
                "audit",
                "outbox",
            )
        )
        if total > 33554432:
            raise OutcomeError("storage_capacity")
        return states, events

    def read(self, token: str, claim_id: str) -> StoredCase:
        actor = self.authority.actor(token, claim_id)
        with self.transaction() as c:
            states, _ = self.verify(c)
            state = states.get(claim_id)
            if state is None:
                raise OutcomeError("case_unavailable")
            if actor.kind != PrincipalKind.HOST:
                self.authority.assigned(actor, state)
            return state

    def execute(
        self, token: str, command: Command, *, permit: PublicationPermit | None = None
    ) -> AuditEvent:
        command = Command.model_validate(command)
        actor = self.authority.actor(token, command.claim_id)
        if (
            command.action in {Action.REGISTER, Action.PUBLISH, Action.REVALIDATE}
            and permit is not self.authority.permit
        ):
            raise OutcomeError("publication_permit_required")
        if (command.action in HOST_ACTIONS) != (actor.kind == PrincipalKind.HOST):
            raise OutcomeError("operation_not_authorized")
        now = self.clock()
        if now.utcoffset() is None or command.occurred_at > now:
            raise OutcomeError("invalid_time")
        with self.transaction() as c:
            states, events = self.verify(c)
            before = states.get(command.claim_id)
            if actor.kind == PrincipalKind.HUMAN:
                if before is None:
                    raise OutcomeError("case_unavailable")
                self.authority.assigned(actor, before)
            old = c.execute(
                (
                    "SELECT request_sha256,event_id FROM receipts WHERE claim_id=? AN"
                    "D actor_id=? AND request_id=?"
                ),
                (command.claim_id, str(actor.principal_id), str(command.request_id)),
            ).fetchone()
            if old:
                if old[0] != digest(command.model_dump(mode="json")):
                    raise OutcomeError("changed_duplicate")
                return next(e for e in events[command.claim_id] if str(e.event_id) == old[1])
            prior = events.get(command.claim_id, [])
            if prior and command.occurred_at < prior[-1].command.occurred_at:
                raise OutcomeError("invalid_time")
            try:
                after, transitions = reduce(self.authority, before, command, actor)
            except OutcomeError:
                raise
            except ValueError as failure:
                raise OutcomeError("invalid_transition") from failure
            event_id = uuid5(NS, f"{command.claim_id}/{actor.principal_id}/{command.request_id}")
            values = dict(
                actor=actor,
                command=command,
                after=after,
                transitions=transitions,
                previous_sha256=prior[-1].event_sha256 if prior else ZERO,
                event_id=event_id,
            )
            prototype = {
                "schema_version": "1.0",
                "synthetic": True,
                "format": "m20-audit-v1",
                **values,
            }
            # Normalize nested DTOs/UUIDs through JSON mode before hashing.
            from pydantic_core import to_jsonable_python

            event = AuditEvent.model_validate(
                {**values, "event_sha256": digest(to_jsonable_python(prototype))}
            )
            c.execute(
                (
                    "INSERT INTO cases VALUES (?,?,?) ON CONFLICT(claim_id) DO UPDATE"
                    " SET revision=excluded.revision,payload=excluded.payload"
                ),
                (command.claim_id, after.revision, encoded(after)),
            )
            c.execute("DELETE FROM assignments WHERE claim_id=?", (command.claim_id,))
            c.executemany(
                "INSERT INTO assignments VALUES (?,?,?)",
                [
                    (
                        command.claim_id,
                        a.principal.role.value if a.principal.role else "",
                        encoded(a),
                    )
                    for a in after.assignments
                ],
            )
            if command.action in {Action.REGISTER, Action.REVALIDATE}:
                approval = self.authority.approval(after.approval_id)
                c.execute(
                    "INSERT INTO artifacts VALUES (?,?)",
                    (str(approval.approval_id), encoded(approval.bundle)),
                )
            if command.action == Action.PUBLISH:
                approval = self.authority.approval(after.approval_id)
                c.execute(
                    "INSERT INTO assessments VALUES (?,?,?,?)",
                    (
                        str(approval.approval_id),
                        command.claim_id,
                        approval.assessment.assessment_id,
                        encoded(approval.assessment),
                    ),
                )
            self.fault("after_projection")
            c.execute(
                "INSERT INTO audit VALUES (?,?,?,?)",
                (str(event_id), command.claim_id, after.revision, encoded(event)),
            )
            if command.decision is not None:
                c.execute(
                    "INSERT INTO decisions VALUES (?,?,?)",
                    (str(event_id), command.claim_id, encoded(command.decision)),
                )
            c.execute(
                "INSERT INTO receipts VALUES (?,?,?,?,?)",
                (
                    command.claim_id,
                    str(actor.principal_id),
                    str(command.request_id),
                    digest(command.model_dump(mode="json")),
                    str(event_id),
                ),
            )
            payload = json_bytes(
                {
                    "claim_id": command.claim_id,
                    "event_sha256": event.event_sha256,
                    "purpose": "local_synthetic_audit_projection_only",
                }
            ).decode()
            c.execute(
                "INSERT INTO outbox VALUES (?,?,?,?,?)",
                (str(event_id), command.claim_id, payload, "pending", 0),
            )
            self.fault("after_audit")
            self.verify(c)
            self.fault("before_commit")
        self.fault("after_commit")
        return event

    def dispatch(
        self, token: str, claim_id: str, event_id: UUID, *, unavailable: bool = False
    ) -> str:
        actor = self.authority.actor(token, claim_id)
        if actor.kind != PrincipalKind.HOST:
            raise OutcomeError("operation_not_authorized")
        with self.transaction() as c:
            _, events = self.verify(c)
            event = next((e for e in events.get(claim_id, []) if e.event_id == event_id), None)
            if event is None:
                raise OutcomeError("outbox_unavailable")
            status, attempts = c.execute(
                "SELECT status,attempts FROM outbox WHERE event_id=?", (str(event_id),)
            ).fetchone()
            if status != "pending":
                return str(status)
            attempts += 1
            result = "unavailable" if unavailable else "delivered"
            status = "delivered" if not unavailable else "dead" if attempts == 3 else "pending"
            c.execute(
                "INSERT INTO delivery_events VALUES (?,?,?)", (str(event_id), attempts, result)
            )
            if not unavailable:
                c.execute(
                    "INSERT INTO deliveries VALUES (?,?)", (str(event_id), event.event_sha256)
                )
            self.fault("after_sink")
            c.execute(
                "UPDATE outbox SET status=?,attempts=? WHERE event_id=?",
                (status, attempts, str(event_id)),
            )
            self.verify(c)
            self.fault("before_delivery_commit")
        self.fault("after_delivery_commit")
        return str(status)
