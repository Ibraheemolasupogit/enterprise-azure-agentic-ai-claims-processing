"""Bounded opaque local capabilities with absolute monotonic expiry and host revocation."""

import math
import re
import secrets
from collections.abc import Callable
from dataclasses import dataclass, field
from hashlib import sha256
from threading import RLock
from time import monotonic


@dataclass(frozen=True)
class Record[T]:
    value: T = field(repr=False)
    expires: float


class Capabilities[T]:
    def __init__(self, *, timer: Callable[[], float] = monotonic) -> None:
        self._timer = timer
        self._records: dict[str, Record[T]] = {}
        self._last = float("-inf")
        self._healthy = True
        self._lock = RLock()

    def _now(self) -> float:
        try:
            now = self._timer()
        except Exception:
            self._healthy = False
            raise ValueError("local capability clock unavailable") from None
        if (
            isinstance(now, bool)
            or not isinstance(now, (int, float))
            or not math.isfinite(now)
            or now < self._last
        ):
            self._healthy = False
        if not self._healthy:
            raise ValueError("local capability clock unavailable")
        self._last = now
        self._records = {k: v for k, v in self._records.items() if v.expires > now}
        return now

    def issue(self, value: T, *, ttl: float = 900) -> str:
        with self._lock:
            now = self._now()
            if (
                isinstance(ttl, bool)
                or not isinstance(ttl, (int, float))
                or not math.isfinite(ttl)
                or not 0 < ttl <= 900
            ):
                raise ValueError("invalid local capability lifetime")
            if len(self._records) >= 64:
                raise ValueError("local capability capacity exceeded")
            token = secrets.token_urlsafe(32)
            fingerprint = sha256(token.encode()).hexdigest()
            if fingerprint in self._records:
                raise ValueError("local capability collision")
            self._records[fingerprint] = Record(value, now + ttl)
            return token

    def resolve(self, token: str) -> T | None:
        with self._lock:
            try:
                self._now()
            except (ValueError, TypeError, OverflowError):
                return None
            if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
                return None
            record = self._records.get(sha256(token.encode()).hexdigest())
            return record.value if record is not None else None

    def revoke(self, token: str) -> None:
        with self._lock:
            self._records.pop(sha256(token.encode()).hexdigest(), None)
