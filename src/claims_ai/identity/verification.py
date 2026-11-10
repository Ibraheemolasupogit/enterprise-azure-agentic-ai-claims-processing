"""Strict signed synthetic identity checks with explicit offline discovery and revocation."""

import json
import logging
import re
from collections.abc import Callable
from threading import RLock
from typing import Protocol
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from claims_ai.identity.contracts import (
    AuthorityKind,
    TokenClaims,
    VerificationPolicy,
    VerifiedIdentity,
    principal_for,
)
from claims_ai.identity.keys import KeyDiscovery, LocalKeyRing, epoch
from claims_ai.logging import LogEvent, log_event

CLAIM_KEYS = set(TokenClaims.model_fields) - {"schema_version", "synthetic"}


class IdentityVerifier(Protocol):
    authority_kind: AuthorityKind

    def verify(self, credential: str) -> VerifiedIdentity | None: ...


class UnconfiguredEntraVerifier:
    """Target integration seam: never falls back to local credentials or contacts a provider."""

    authority_kind = AuthorityKind.ENTRA

    def verify(self, credential: str) -> VerifiedIdentity | None:
        return None


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, value in pairs:
        if name in result:
            raise ValueError("ambiguous identity input")
        result[name] = value
    return result


def json_object(segment: str) -> tuple[dict[str, object], bytes]:
    content = jwt.utils.base64url_decode(segment)
    value = json.loads(content.decode("utf-8"), object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError("identity object required")
    return value, content


def issue(
    keys: LocalKeyRing,
    policy: VerificationPolicy,
    cases: tuple[str, ...],
    *,
    now: int,
    lifetime: int = 300,
    token_id: UUID | None = None,
) -> str:
    if type(lifetime) is not int or not 0 < lifetime <= policy.max_lifetime_seconds:
        raise ValueError("invalid synthetic token lifetime")
    principal = principal_for(policy.subject, policy.role)
    claims = TokenClaims.model_validate_json(
        json.dumps(
            {
                "iss": policy.issuer,
                "aud": policy.audience,
                "tid": str(policy.tenant_id),
                "azp": str(policy.application_id),
                "sub": str(policy.subject),
                "principal_kind": principal.kind.value,
                "roles": [policy.role.value],
                "case_ids": list(cases),
                "authority": AuthorityKind.SYNTHETIC.value,
                "iat": now,
                "nbf": now,
                "exp": now + lifetime,
                "jti": str(token_id or uuid4()),
            }
        )
    )
    return keys.sign(claims.model_dump(mode="json", exclude={"schema_version", "synthetic"}))


class SyntheticTokenVerifier:
    authority_kind = AuthorityKind.SYNTHETIC

    def __init__(
        self,
        policy: VerificationPolicy,
        keys: KeyDiscovery,
        *,
        clock: Callable[[], int] = epoch,
        logger: logging.Logger | None = None,
    ) -> None:
        self.policy = VerificationPolicy.model_validate(policy)
        if keys.authority_kind != AuthorityKind.SYNTHETIC:
            raise ValueError("synthetic identity requires local host-loaded keys")
        self._keys, self._clock = keys, clock
        self._revoked: set[UUID] = set()
        self._disabled = False
        self._last_time: int | None = None
        self._lock = RLock()
        self._logger = logger or logging.getLogger("claims_ai.identity")

    def revoke_token(self, token_id: UUID) -> None:
        with self._lock:
            if not isinstance(token_id, UUID):
                raise ValueError("invalid identity revocation request")
            if token_id not in self._revoked and len(self._revoked) >= 64:
                self._disabled = True
                raise ValueError("revocation capacity exhausted; verifier closed")
            self._revoked.add(token_id)

    def revoke_principal(self) -> None:
        with self._lock:
            self._disabled = True

    def verify(self, credential: str) -> VerifiedIdentity | None:
        with self._lock:
            result = None
            try:
                if self._disabled or len(credential) > 8192:
                    raise ValueError("identity unavailable")
                parts = credential.split(".")
                if len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts):
                    raise ValueError("invalid identity encoding")
                header, _ = json_object(parts[0])
                if (
                    set(header) != {"alg", "typ", "kid"}
                    or header["alg"] != "RS256"
                    or header["typ"] != "at+jwt"
                    or not isinstance(header["kid"], str)
                    or re.fullmatch(r"local-[0-9]{4}", header["kid"]) is None
                ):
                    raise ValueError("untrusted signing instructions")
                payload, raw = json_object(parts[1])
                if set(payload) != CLAIM_KEYS:
                    raise ValueError("identity claim set mismatch")
                claims = TokenClaims.model_validate_json(raw)
                for name in ("tid", "azp", "sub", "jti"):
                    if payload[name] != str(getattr(claims, name)):
                        raise ValueError("noncanonical identity")
                now = self._clock()
                if (
                    type(now) is not int
                    or now < 0
                    or self._last_time is not None
                    and now < self._last_time
                ):
                    self._disabled = True
                    raise ValueError("identity clock unavailable")
                self._last_time = now
                policy = self.policy
                if (
                    type(now) is not int
                    or now < 0
                    or claims.iss != policy.issuer
                    or claims.aud != policy.audience
                    or claims.tid != policy.tenant_id
                    or claims.azp != policy.application_id
                    or claims.sub != policy.subject
                    or claims.roles != (policy.role,)
                    or claims.nbf != claims.iat
                    or not claims.iat <= now < claims.exp
                    or not 0 < claims.exp - claims.iat <= policy.max_lifetime_seconds
                    or claims.jti in self._revoked
                ):
                    raise ValueError("identity policy mismatch")
                public = self._keys.resolve(header["kid"], now)
                if not isinstance(public, rsa.RSAPublicKey) or public.key_size < 2048:
                    raise ValueError("signing key unavailable")
                jwt.decode(
                    credential,
                    public,
                    algorithms=["RS256"],
                    issuer=policy.issuer,
                    audience=policy.audience,
                    options={
                        "require": sorted(CLAIM_KEYS),
                        "strict_aud": True,
                        "verify_exp": False,
                        "verify_nbf": False,
                        "verify_iat": False,
                    },
                )
                result = VerifiedIdentity(claims=claims)
            except Exception:
                result = None
            try:
                log_event(
                    self._logger,
                    LogEvent.IDENTITY_VERIFICATION,
                    fields={"status": "ok" if result is not None else "denied"},
                )
            except Exception:
                return None
            return result
