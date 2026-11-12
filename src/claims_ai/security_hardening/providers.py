"""Pinned Entra-shaped OFFLINE fixtures, intentionally incompatible with live adapters."""

import json
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from hashlib import sha256
from typing import Annotated, Literal, Self
from uuid import UUID

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import Field, model_validator

from claims_ai.identity.contracts import VerificationPolicy
from claims_ai.identity.keys import epoch
from claims_ai.identity.verification import json_object
from claims_ai.logging import LogEvent, log_event
from claims_ai.models import Contract, Sha256
from claims_ai.security_hardening.contracts import IdentityClass

ROLE = {
    IdentityClass.REVIEWER: "Claims.Reviewer",
    IdentityClass.SUPERVISOR: "Claims.Supervisor",
    IdentityClass.WORKLOAD: "Claims.Intake",
    IdentityClass.PUBLISHER: "Claims.Assessment.Publish",
    IdentityClass.GATEWAY: "Claims.Gateway.Invoke",
    IdentityClass.BACKEND: "Claims.Backend.Read",
}
AUDIENCE = {
    IdentityClass.REVIEWER: "api://northstar.invalid/claims-api-v1",
    IdentityClass.SUPERVISOR: "api://northstar.invalid/claims-api-v1",
    IdentityClass.WORKLOAD: "api://northstar.invalid/claims-api-v1",
    IdentityClass.PUBLISHER: "api://northstar.invalid/assessment-publication-v1",
    IdentityClass.GATEWAY: "api://northstar.invalid/mcp-gateway-v1",
    IdentityClass.BACKEND: "api://northstar.invalid/mcp-backend-v1",
}


class ProviderProfile(Contract):
    format: Literal["m21-provider-v1"] = "m21-provider-v1"
    provider: Literal["entra_offline_fixture_v1"] = "entra_offline_fixture_v1"
    simulated: Literal[True] = True
    live_enabled: Literal[False] = False
    tenant_id: UUID
    application_id: UUID
    object_id: UUID
    identity_class: IdentityClass
    issuer: str
    audience: str
    role: str
    algorithms: Literal["RS256"] = "RS256"
    max_lifetime_seconds: Annotated[int, Field(strict=True, ge=1, le=300)] = 300

    @model_validator(mode="after")
    def exact_resource(self) -> Self:
        if (
            self.issuer != f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
            or self.audience != AUDIENCE[self.identity_class]
            or self.role != ROLE[self.identity_class]
        ):
            raise ValueError("offline provider/resource profile mismatch")
        return self


@dataclass(frozen=True)
class PinnedKey:
    public: rsa.RSAPublicKey
    not_before: int
    expires: int


class FixtureIdentity(Contract):
    """No Principal, ReviewSession or authority-kind conversion is provided."""

    provider: Literal["entra_offline_fixture_v1"] = "entra_offline_fixture_v1"
    simulated: Literal[True] = True
    profile_sha256: Sha256
    object_id: UUID
    identity_class: IdentityClass
    expires_at: int


def profile_hash(profile: ProviderProfile, keys: Mapping[str, PinnedKey]) -> str:
    from claims_ai.rules.specification import digest

    return digest(
        {
            "profile": profile.model_dump(mode="json"),
            "keys": {
                k: {
                    "sha256": sha256(
                        v.public.public_bytes(
                            serialization.Encoding.DER,
                            serialization.PublicFormat.SubjectPublicKeyInfo,
                        )
                    ).hexdigest(),
                    "nbf": v.not_before,
                    "exp": v.expires,
                }
                for k, v in sorted(keys.items())
            },
        }
    )


class OfflineFixtureVerifier:
    """No IdentityVerifier implementation: success cannot be exchanged for host access."""

    def __init__(
        self,
        profile: ProviderProfile,
        keys: Mapping[str, PinnedKey],
        *,
        clock: Callable[[], int] = epoch,
        logger: logging.Logger | None = None,
    ) -> None:
        self.profile = ProviderProfile.model_validate(profile)
        self._keys = dict(keys)
        if not 1 <= len(keys) <= 4 or any(
            not re.fullmatch(r"fixture-[0-9]{4}", k)
            or not isinstance(v.public, rsa.RSAPublicKey)
            or v.public.key_size < 2048
            or type(v.not_before) is not int
            or type(v.expires) is not int
            or not 0 <= v.not_before < v.expires
            for k, v in keys.items()
        ):
            raise ValueError("invalid pinned offline signing context")
        self.context_sha256 = profile_hash(self.profile, self._keys)
        self._clock, self._last = clock, -1
        self._logger = logger or logging.getLogger("claims_ai.security_hardening")

    def verify(self, token: str) -> FixtureIdentity | None:
        result = None
        try:
            if not isinstance(token, str) or len(token) > 8192:
                raise ValueError("invalid fixture")
            parts = token.split(".")
            if len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts):
                raise ValueError("invalid fixture")
            header, _ = json_object(parts[0])
            if (
                set(header) != {"kid", "alg", "typ"}
                or header["alg"] != "RS256"
                or header["typ"] != "JWT"
                or not isinstance(header["kid"], str)
                or header["kid"] not in self._keys
            ):
                raise ValueError("untrusted fixture header")
            claims, _ = json_object(parts[1])
            p = self.profile
            human = p.identity_class in {IdentityClass.REVIEWER, IdentityClass.SUPERVISOR}
            expected: dict[str, object] = {
                "iss": p.issuer,
                "aud": p.audience,
                "tid": str(p.tenant_id),
                "azp": str(p.application_id),
                "oid": str(p.object_id),
                "ver": "2.0",
                "roles": [p.role],
                "idtyp": "user" if human else "app",
            }
            if human:
                expected["scp"] = "Claims.Review"
            if set(claims) != set(expected) | {"iat", "nbf", "exp", "jti"} or any(
                claims[k] != v or type(claims[k]) is not type(v) for k, v in expected.items()
            ):
                raise ValueError("fixture profile mismatch")
            now = self._clock()
            if type(now) is not int or now < self._last or now < 0:
                self._last = 2**63
                raise ValueError("fixture clock unavailable")
            self._last = now
            iat, nbf, exp = (claims[k] for k in ("iat", "nbf", "exp"))
            if (
                type(iat) is not int
                or type(nbf) is not int
                or type(exp) is not int
                or nbf != iat
                or not iat <= now < exp
                or not 0 < exp - iat <= p.max_lifetime_seconds
                or not isinstance(claims["jti"], str)
                or str(UUID(claims["jti"])) != claims["jti"]
            ):
                raise ValueError("invalid fixture lifetime")
            key = self._keys[header["kid"]]
            if not key.not_before <= now < key.expires:
                raise ValueError("pinned key expired")
            jwt.decode(
                token,
                key.public,
                algorithms=["RS256"],
                issuer=p.issuer,
                audience=p.audience,
                options={
                    "strict_aud": True,
                    "verify_iat": False,
                    "verify_nbf": False,
                    "verify_exp": False,
                    "require": sorted(claims),
                },
            )
            result = FixtureIdentity(
                profile_sha256=self.context_sha256,
                object_id=p.object_id,
                identity_class=p.identity_class,
                expires_at=exp,
            )
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


def load_fixture(path: str) -> tuple[OfflineFixtureVerifier, str]:
    """Explicit pinned local fixture only, bounded read; no network or live-provider factory."""
    from pathlib import Path

    with Path(path).open("rb", buffering=0) as stream:
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError("fixture capacity")
    data = json.loads(raw)
    profile = ProviderProfile.model_validate(data["profile"])
    key = serialization.load_pem_public_key(data["public_key"].encode())
    if not isinstance(key, rsa.RSAPublicKey):
        raise ValueError("fixture RSA public key required")
    return (
        OfflineFixtureVerifier(
            profile,
            {"fixture-0001": PinnedKey(key, data["epoch"], data["epoch"] + 600)},
            clock=lambda: data["epoch"],
        ),
        data["token"],
    )


class SyntheticProviderProfile(Contract):
    """Version tag around unchanged M18 local policy; no widening of its claim contract."""

    format: Literal["m21-provider-v1"] = "m21-provider-v1"
    provider: Literal["local_synthetic_v1"] = "local_synthetic_v1"
    simulated: Literal[True] = True
    live_enabled: Literal[False] = False
    policy: VerificationPolicy
    public_key_sha256: Sha256


def synthetic_context(policy: VerificationPolicy, public_pem: bytes) -> str:
    from claims_ai.rules.specification import digest

    return digest(
        SyntheticProviderProfile(
            policy=policy, public_key_sha256=sha256(public_pem).hexdigest()
        ).model_dump(mode="json")
    )
