"""Pinned-key synthetic JWT verification, exclusively for local gateway-boundary tests."""

import time
from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from claims_ai.mcp_http.contracts import VerifiedGateway

ISSUER = "https://northstar.invalid/synthetic-gateway-issuer"
AUDIENCE = "api://northstar.invalid/local-claims-backend"
ROLE = "Claims.Backend.Read"


class GatewayVerifier(Protocol):
    def verify(self, credential: str) -> VerifiedGateway | None: ...


class DenyAll:
    def verify(self, credential: str) -> None:
        return None


@dataclass(frozen=True)
class SyntheticVerifier:
    """No Entra/JWKS client: public key and expected identities come only from the test host."""

    public_key: bytes = field(repr=False)
    expected_subject: UUID
    expected_application: UUID

    def verify(self, credential: str) -> VerifiedGateway | None:
        try:
            claims = jwt.decode(
                credential,
                self.public_key,
                algorithms=["RS256"],
                issuer=ISSUER,
                audience=AUDIENCE,
                options={
                    "require": ["iss", "aud", "sub", "azp", "roles", "exp", "nbf", "iat", "jti"]
                },
            )
            subject, application = UUID(claims["sub"]), UUID(claims["azp"])
            UUID(claims["jti"])
            if (
                subject != self.expected_subject
                or application != self.expected_application
                or claims["roles"] != [ROLE]
                or claims["exp"] - claims["iat"] > 60
                or claims["exp"] <= claims["iat"]
            ):
                return None
            return VerifiedGateway(subject, application)
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            return None


class SyntheticIssuer:
    """Ephemeral, in-memory test credentials; never persist keys or issued tokens in artifacts."""

    def __init__(self) -> None:
        self._private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        self.subject, self.application = uuid4(), uuid4()
        self.verifier = SyntheticVerifier(
            self._private.public_key().public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ),
            self.subject,
            self.application,
        )

    def issue(self, **changes: object) -> str:
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": str(self.subject),
            "azp": str(self.application),
            "roles": [ROLE],
            "iat": now,
            "nbf": now,
            "exp": now + 60,
            "jti": str(uuid4()),
            **changes,
        }
        return jwt.encode(claims, self._private, algorithm="RS256")
