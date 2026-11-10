"""Host-loaded key discovery only: no URL resolution, JWKS fetch or fallback algorithm."""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from threading import RLock
from typing import Protocol

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from claims_ai.identity.contracts import AuthorityKind


def epoch() -> int:
    return int(time.time())


class KeyDiscovery(Protocol):
    authority_kind: AuthorityKind

    def resolve(self, kid: str, now: int) -> rsa.RSAPublicKey | None: ...


@dataclass(frozen=True)
class SigningKey:
    private: rsa.RSAPrivateKey = field(repr=False)
    not_before: int
    expires: int


class LocalKeyRing:
    authority_kind = AuthorityKind.SYNTHETIC

    def __init__(self, *, clock: Callable[[], int] = epoch) -> None:
        self._clock = clock
        self._keys: dict[str, SigningKey] = {}
        self._generation = 0
        self._current: str | None = None
        self._lock = RLock()
        self.rotate()

    def rotate(self) -> str:
        with self._lock:
            if len(self._keys) >= 4 or self._generation >= 8:
                raise ValueError("local key rotation capacity exceeded")
            now = self._clock()
            if type(now) is not int or now < 0:
                raise ValueError("local signing clock unavailable")
            self._generation += 1
            kid = f"local-{self._generation:04d}"
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            self._keys[kid] = SigningKey(key, now, now + 600)
            self._current = kid
            return kid

    @property
    def current(self) -> str:
        with self._lock:
            if self._current is None:
                raise ValueError("no active local signing key")
            return self._current

    def retire(self, kid: str) -> None:
        with self._lock:
            self._keys.pop(kid, None)
            if self._current == kid:
                self._current = None

    def resolve(self, kid: str, now: int) -> rsa.RSAPublicKey | None:
        with self._lock:
            key = self._keys.get(kid)
            if key is None or not key.not_before <= now < key.expires:
                return None
            return key.private.public_key()

    def sign(self, claims: Mapping[str, object]) -> str:
        with self._lock:
            kid = self.current
            key = self._keys[kid]
            if not key.not_before <= self._clock() < key.expires:
                raise ValueError("local signing key expired")
            return jwt.encode(
                dict(claims), key.private, algorithm="RS256", headers={"kid": kid, "typ": "at+jwt"}
            )
