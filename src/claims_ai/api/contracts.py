"""Version-one HTTP contracts; clients cannot submit grants, policies or human identities."""

from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from claims_ai.agents.contracts import AgentDraft
from claims_ai.human_review.contracts import (
    Principal,
    PrincipalKind,
    QueueEntry,
    ReviewBinding,
    ReviewState,
)
from claims_ai.models import (
    CaseState,
    Claim,
    ClaimId,
    Contract,
    PositiveInt,
    ReviewerRole,
    Sha256,
    Version,
)
from claims_ai.rules.contracts import RuleEvaluation
from claims_ai.workflow.contracts import ReviewTask, State


class ApiLimits(Contract):
    port: Annotated[int, Field(strict=True, ge=1024, le=65535)] = 8766
    max_request_bytes: Annotated[int, Field(strict=True, ge=256, le=65536)] = 16384
    max_response_bytes: Annotated[int, Field(strict=True, ge=65536, le=16777216)] = 8388608
    body_timeout_seconds: Annotated[float, Field(strict=True, gt=0, le=10, allow_inf_nan=False)] = (
        5.0
    )
    max_inflight: Annotated[int, Field(strict=True, ge=1, le=16)] = 8
    max_cases: Annotated[int, Field(strict=True, ge=1, le=16)] = 16
    max_receipts: Annotated[int, Field(strict=True, ge=2, le=256)] = 128


class ApiScope(Contract):
    principal: Principal
    claim_ids: Annotated[tuple[ClaimId, ...], Field(max_length=16)]
    can_intake: bool = False
    can_process: bool = False

    @model_validator(mode="after")
    def host_permissions(self) -> Self:
        if len(set(self.claim_ids)) != len(self.claim_ids):
            raise ValueError("case scope must be unique")
        if (self.can_intake or self.can_process) and self.principal.kind != PrincipalKind.HOST:
            raise ValueError("only a synthetic intake host can submit or process bundles")
        return self


class IntakeRequest(Contract):
    bundle_id: Version
    claim: Claim


class ProcessRequest(Contract):
    expected_case_revision: PositiveInt
    expected_case_sha256: Sha256


class ProcessingPhase(StrEnum):
    INTAKEN = "intaken"
    PROCESSING = "processing"
    PROCESSED = "processed"
    ATTENTION = "needs_human_attention"
    FAILED = "application_processing_failed"


class ClaimStatus(Contract):
    claim_id: ClaimId
    case_revision: PositiveInt
    case_sha256: Sha256
    case_state: CaseState
    application_revision: PositiveInt
    processing_phase: ProcessingPhase
    workflow_state: State | None = None
    workflow_correlation_id: UUID
    review_entry_id: Sha256 | None = None
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False


class AdvisoryResponse(Contract):
    claim_id: ClaimId
    task: ReviewTask | None
    draft: AgentDraft | None
    rules: RuleEvaluation | None
    review_binding: ReviewBinding | None
    recommendation_available: bool
    content_trust: Literal["untrusted_advisory_and_source_data"] = (
        "untrusted_advisory_and_source_data"
    )
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False


class QueueItem(Contract):
    entry_id: Sha256
    claim_id: ClaimId
    case_revision: PositiveInt
    review_revision: PositiveInt
    state: ReviewState
    required_reviewer: ReviewerRole
    recommendation_available: bool
    correlation_id: UUID

    @classmethod
    def from_entry(cls, entry: QueueEntry) -> "QueueItem":
        return cls(
            entry_id=entry.entry_id,
            claim_id=entry.binding.claim_id,
            case_revision=entry.binding.case_revision,
            review_revision=entry.review_revision,
            state=entry.state,
            required_reviewer=entry.required_reviewer,
            recommendation_available=entry.recommendation_available,
            correlation_id=entry.correlation_id,
        )


class ReviewQueueResponse(Contract):
    items: Annotated[tuple[QueueItem, ...], Field(max_length=16)]
    next_offset: Annotated[int, Field(strict=True, ge=0, le=64)] | None = None


class LivenessResponse(Contract):
    status: Literal["alive"] = "alive"
    execution_mode: Literal["OFFLINE_SYNTHETIC_APPLICATION"] = "OFFLINE_SYNTHETIC_APPLICATION"


class ReadinessResponse(Contract):
    local_application_ready: bool
    started: bool
    services_configured: bool
    workflow_available: bool
    synthetic_authenticator_configured: bool
    authentication_mode: Literal["SYNTHETIC_HOST_CAPABILITY_NOT_ENTRA"] = (
        "SYNTHETIC_HOST_CAPABILITY_NOT_ENTRA"
    )
    external_azure_ready: Literal[False] = False
    azure_dependencies: Literal["NOT_CONFIGURED_NOT_PROBED"] = "NOT_CONFIGURED_NOT_PROBED"
    storage: Literal["BOUNDED_MEMORY_NOT_DURABLE"] = "BOUNDED_MEMORY_NOT_DURABLE"


class ApiCode(StrEnum):
    AUTH = "synthetic_credential_required"
    DENIED = "operation_not_authorized"
    MISSING = "case_or_review_not_found"
    INVALID = "request_validation_failed"
    PRECONDITION = "revision_precondition_failed"
    REQUIRED = "idempotency_and_revision_required"
    CONFLICT = "idempotency_or_state_conflict"
    UNAVAILABLE = "workflow_or_review_unavailable"
    BODY = "request_body_rejected"
    SIZE = "request_too_large"
    MEDIA = "uncompressed_json_required"
    ORIGIN = "local_authority_rejected"
    BUSY = "local_request_capacity_exceeded"
    RESPONSE = "response_capacity_exceeded"
    INTERNAL = "application_failure"


class ErrorResponse(Contract):
    status: Literal["error"] = "error"
    code: ApiCode
    request_correlation_id: UUID


class ApiError(Exception):
    def __init__(self, status: int, code: ApiCode) -> None:
        self.status, self.code = status, code
        super().__init__(code.value)
