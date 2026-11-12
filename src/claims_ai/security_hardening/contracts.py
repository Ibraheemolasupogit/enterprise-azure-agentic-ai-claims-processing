"""Versioned authority matrix; verified claims never manufacture host capabilities."""

from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from claims_ai.identity.contracts import ProductionCookieRequirements
from claims_ai.models import ClaimId, Contract, Sha256


class IdentityClass(StrEnum):
    REVIEWER = "human_reviewer"
    SUPERVISOR = "human_supervisor"
    WORKLOAD = "intake_workload"
    PUBLISHER = "assessment_publisher"
    GATEWAY = "mcp_gateway"
    BACKEND = "mcp_backend"


class Permission(StrEnum):
    REVIEW = "api_review"
    INTAKE = "api_intake"
    PROCESS = "api_process"
    OUTCOME = "human_case_outcome"
    SUPERVISE = "supervisor_override_reopen"
    PUBLISH = "assessment_publication"
    MCP_READ = "mcp_governed_read"
    BACKEND = "backend_execution"


MATRIX: dict[IdentityClass, frozenset[Permission]] = {
    IdentityClass.REVIEWER: frozenset({Permission.REVIEW, Permission.OUTCOME}),
    IdentityClass.SUPERVISOR: frozenset(
        {Permission.REVIEW, Permission.OUTCOME, Permission.SUPERVISE}
    ),
    IdentityClass.WORKLOAD: frozenset({Permission.INTAKE, Permission.PROCESS}),
    IdentityClass.PUBLISHER: frozenset({Permission.PUBLISH}),
    IdentityClass.GATEWAY: frozenset({Permission.MCP_READ}),
    IdentityClass.BACKEND: frozenset({Permission.BACKEND}),
}


class Grant(Contract):
    format: Literal["m21-grant-v1"] = "m21-grant-v1"
    grant_id: UUID
    principal_id: UUID
    identity_class: IdentityClass
    case_ids: Annotated[tuple[ClaimId, ...], Field(min_length=1, max_length=16)]
    permissions: Annotated[tuple[Permission, ...], Field(min_length=1, max_length=3)]
    binding_sha256: Sha256
    issued_at: Annotated[int, Field(strict=True, ge=0)]
    expires_at: Annotated[int, Field(strict=True, ge=1)]

    @model_validator(mode="after")
    def least_privilege(self) -> Self:
        if (
            len(set(self.case_ids)) != len(self.case_ids)
            or len(set(self.permissions)) != len(self.permissions)
            or not set(self.permissions) <= MATRIX[self.identity_class]
            or not 0 < self.expires_at - self.issued_at <= 900
        ):
            raise ValueError("invalid least privilege grant")
        # Supervisor status may not silently survive removal of its explicit permission.
        if self.identity_class == IdentityClass.SUPERVISOR and Permission.SUPERVISE not in (
            self.permissions
        ):
            raise ValueError("supervisor grant requires explicit authority")
        return self


class Anchor(Contract):
    """Independently retained trusted head; never load this from the untrusted DB itself."""

    revision: Annotated[int, Field(strict=True, ge=0, le=256)]
    head: Sha256


class DeploymentContract(Contract):
    """Target-only safe deployment shape. Passing does not activate any cloud profile."""

    format: Literal["m21-deployment-v1"] = "m21-deployment-v1"
    enabled: Literal[False] = False
    live_provider: Literal[False] = False
    gateway_audience: Literal["api://northstar.invalid/mcp-gateway-v1"] = (
        "api://northstar.invalid/mcp-gateway-v1"
    )
    backend_audience: Literal["api://northstar.invalid/mcp-backend-v1"] = (
        "api://northstar.invalid/mcp-backend-v1"
    )
    gateway_application: UUID
    backend_application: UUID
    backend_authentication: Literal["managed_identity_target_only"] = "managed_identity_target_only"
    forwarded_identity_trusted: Literal[False] = False
    direct_backend_public_access: Literal[False] = False
    tls_required: Literal[True] = True
    private_ingress_required: Literal[True] = True
    secret_source: Literal["key_vault_reference_target_only"] = "key_vault_reference_target_only"
    secret_reference: Annotated[str, Field(pattern=r"^kvref://[a-z0-9-]{3,63}/[a-z0-9-]{1,63}$")]
    cookie: ProductionCookieRequirements = ProductionCookieRequirements()

    @model_validator(mode="after")
    def separate_applications(self) -> Self:
        if self.gateway_application == self.backend_application:
            raise ValueError("gateway and backend application identities must differ")
        return self
