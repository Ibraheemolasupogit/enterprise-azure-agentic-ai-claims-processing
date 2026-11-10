"""Synthetic verification contracts and explicit unavailable real-provider boundary."""

from enum import StrEnum
from typing import Annotated, Final, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from claims_ai.human_review.contracts import Principal, PrincipalKind
from claims_ai.models import ClaimId, Contract, ReviewerRole

ISSUER: Final = "https://northstar.invalid/identity/v1"
API_AUDIENCE: Final = "api://northstar.invalid/claims-api-v1"
MCP_AUDIENCE: Final = "api://northstar.invalid/mcp-backend-v1"


class AuthorityKind(StrEnum):
    SYNTHETIC = "local_synthetic_authority"
    ENTRA = "entra_target_not_configured"


class IdentityRole(StrEnum):
    REVIEWER = "Claims.Reviewer"
    SUPERVISOR = "Claims.Supervisor"
    INTAKE = "Claims.Intake"
    BACKEND = "Claims.Backend.Read"


def principal_for(subject: UUID, role: IdentityRole) -> Principal:
    kind, reviewer_role = {
        IdentityRole.REVIEWER: (PrincipalKind.HUMAN, ReviewerRole.REVIEWER),
        IdentityRole.SUPERVISOR: (PrincipalKind.HUMAN, ReviewerRole.SUPERVISOR),
        IdentityRole.INTAKE: (PrincipalKind.HOST, None),
        IdentityRole.BACKEND: (PrincipalKind.MCP, None),
    }[role]
    return Principal(principal_id=subject, kind=kind, role=reviewer_role)


class VerificationPolicy(Contract):
    issuer: Literal["https://northstar.invalid/identity/v1"] = ISSUER
    audience: Literal[
        "api://northstar.invalid/claims-api-v1", "api://northstar.invalid/mcp-backend-v1"
    ]
    tenant_id: UUID
    application_id: UUID
    subject: UUID
    role: IdentityRole
    max_lifetime_seconds: Annotated[int, Field(strict=True, ge=1, le=300)] = 300

    @model_validator(mode="after")
    def separate_resources(self) -> Self:
        if (self.audience == MCP_AUDIENCE) != (self.role == IdentityRole.BACKEND):
            raise ValueError("backend and application identity resources are separate")
        return self


class TokenClaims(Contract):
    iss: Literal["https://northstar.invalid/identity/v1"]
    aud: Literal["api://northstar.invalid/claims-api-v1", "api://northstar.invalid/mcp-backend-v1"]
    tid: UUID
    azp: UUID
    sub: UUID
    principal_kind: PrincipalKind
    roles: Annotated[tuple[IdentityRole, ...], Field(min_length=1, max_length=1)]
    case_ids: Annotated[tuple[ClaimId, ...], Field(min_length=1, max_length=16)]
    authority: Literal["local_synthetic_authority"]
    iat: Annotated[int, Field(strict=True, ge=0)]
    nbf: Annotated[int, Field(strict=True, ge=0)]
    exp: Annotated[int, Field(strict=True, ge=0)]
    jti: UUID

    @model_validator(mode="after")
    def unique_scope(self) -> Self:
        if len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError("case scope must be exact and unique")
        if self.principal_kind != principal_for(self.sub, self.roles[0]).kind:
            raise ValueError("human and workload identity cannot be interchanged")
        return self


class VerifiedIdentity(Contract):
    authority_kind: Literal[AuthorityKind.SYNTHETIC] = AuthorityKind.SYNTHETIC
    claims: TokenClaims

    @property
    def principal(self) -> Principal:
        return principal_for(self.claims.sub, self.claims.roles[0])


class ProductionCookieRequirements(Contract):
    """Target-only deployment requirements, not an enabled HTTPS/Entra UI profile."""

    name: Literal["__Host-northstar_reviewer"] = "__Host-northstar_reviewer"
    secure: Literal[True] = True
    httponly: Literal[True] = True
    samesite: Literal["strict"] = "strict"
    path: Literal["/"] = "/"
    domain: Literal[None] = None
    tls_required: Literal[True] = True
