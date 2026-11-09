"""Immutable review contracts, separate from M2's final insurance-outcome decisions."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from claims_ai.lifecycle import CaseTransition
from claims_ai.models import (
    Case,
    ClaimId,
    Contract,
    DocumentId,
    DocumentKind,
    EvidenceId,
    PolicyId,
    PositiveInt,
    ReviewerRole,
    Sha256,
    Text,
    Version,
)
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import Snapshot


class PrincipalKind(StrEnum):
    HUMAN = "synthetic_human"
    HOST = "synthetic_host"
    AGENT = "agent"
    MCP = "mcp_client"
    MODEL = "simulated_model"


class Principal(Contract):
    principal_id: UUID
    kind: PrincipalKind
    role: ReviewerRole | None = None

    @model_validator(mode="after")
    def human_role(self) -> Self:
        if (self.kind == PrincipalKind.HUMAN) != (self.role is not None):
            raise ValueError("only synthetic humans hold reviewer roles")
        return self


@dataclass(frozen=True, eq=False)
class ReviewSession:
    """Opaque host-registered object identity, never a serialized RPC grant or login token."""

    principal: Principal


class ReviewState(StrEnum):
    REVIEW = "awaiting_reviewer"
    SUPERVISOR = "awaiting_supervisor"
    APPROVED = "recommendation_approved"
    REJECTED = "recommendation_rejected"
    EVIDENCE = "additional_evidence_requested"
    STALE = "snapshot_invalidated"


OPEN_STATES = frozenset({ReviewState.REVIEW, ReviewState.SUPERVISOR})


class ReviewAction(StrEnum):
    APPROVE = "approve_recommendation"
    REJECT = "reject_recommendation"
    REQUEST_EVIDENCE = "request_additional_evidence"
    ESCALATE = "escalate_to_supervisor"


class DecisionReason(StrEnum):
    SUPPORTED = "supported_by_evidence"
    UNSUPPORTED = "recommendation_not_supported"
    EVIDENCE = "additional_evidence_needed"
    SUPERVISOR = "supervisor_required"


class ReviewBinding(Contract):
    claim_id: ClaimId
    case_revision: PositiveInt
    case_sha256: Sha256
    evidence_sha256: Sha256
    policy_id: PolicyId
    policy_version: Version
    policy_sha256: Sha256
    index_sha256: Sha256
    rule_version: Version
    rule_sha256: Sha256
    rule_execution_key: Sha256
    workflow_execution_key: Sha256
    checkpoint_sha256: Sha256
    advisory_task_sha256: Sha256
    advisory_sha256: Sha256


class EvidenceReference(Contract):
    evidence_id: EvidenceId
    document_id: DocumentId
    artifact_sha256: Sha256
    processing_key: Sha256
    record_sha256: Sha256


class AssignmentRequest(Contract):
    request_id: UUID
    entry_id: Sha256
    claim_id: ClaimId
    expected_review_revision: PositiveInt
    assignee_id: UUID
    occurred_at: AwareDatetime
    rationale: Text = Field(repr=False)


class ReviewAssignment(Contract):
    assignee_id: UUID
    role: ReviewerRole
    binding: ReviewBinding
    assigned_by: UUID
    assigned_at: AwareDatetime


class ReviewDecision(Contract):
    action_id: UUID
    entry_id: Sha256
    expected_review_revision: PositiveInt
    expected: ReviewBinding
    action: ReviewAction
    reason: DecisionReason
    rationale: Text = Field(repr=False)
    evidence: Annotated[tuple[EvidenceReference, ...], Field(min_length=1, max_length=256)]
    requested_evidence: Annotated[tuple[DocumentKind, ...], Field(max_length=8)] = ()
    occurred_at: AwareDatetime
    purpose: Literal["advisory_recommendation_only"] = "advisory_recommendation_only"
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def reason_and_references(self) -> Self:
        expected = {
            ReviewAction.APPROVE: DecisionReason.SUPPORTED,
            ReviewAction.REJECT: DecisionReason.UNSUPPORTED,
            ReviewAction.REQUEST_EVIDENCE: DecisionReason.EVIDENCE,
            ReviewAction.ESCALATE: DecisionReason.SUPERVISOR,
        }
        if self.reason != expected[self.action]:
            raise ValueError("action requires its explicit review reason")
        if len({r.evidence_id for r in self.evidence}) != len(self.evidence):
            raise ValueError("duplicate review evidence references")
        if (self.action == ReviewAction.REQUEST_EVIDENCE) != bool(self.requested_evidence):
            raise ValueError("only an evidence request must specify missing document kinds")
        if len(set(self.requested_evidence)) != len(self.requested_evidence):
            raise ValueError("duplicate requested evidence kinds")
        return self


class InvalidationRequest(Contract):
    request_id: UUID
    entry_id: Sha256
    expected_review_revision: PositiveInt
    replacement: ReviewBinding
    occurred_at: AwareDatetime
    rationale: Text = Field(repr=False)


class EventKind(StrEnum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    DECIDED = "decision_recorded"
    INVALIDATED = "invalidated"


class ReviewEvent(Contract):
    event_id: UUID
    entry_id: Sha256
    claim_id: ClaimId
    correlation_id: UUID
    sequence: Annotated[int, Field(strict=True, ge=1, le=128)]
    kind: EventKind
    actor: Principal
    occurred_at: AwareDatetime
    rationale: Text = Field(repr=False)
    before: ReviewState | None
    after: ReviewState
    assignment: AssignmentRequest | None = None
    decision: ReviewDecision | None = None
    invalidation: InvalidationRequest | None = None
    case_transition: CaseTransition | None = None
    previous_sha256: Sha256
    event_sha256: Sha256

    @model_validator(mode="after")
    def valid_event(self) -> Self:
        present = (
            self.assignment is not None,
            self.decision is not None,
            self.invalidation is not None,
        )
        expected = {
            EventKind.QUEUED: (False, False, False),
            EventKind.ASSIGNED: (True, False, False),
            EventKind.DECIDED: (False, True, False),
            EventKind.INVALIDATED: (False, False, True),
        }
        if present != expected[self.kind]:
            raise ValueError("review event payload does not match its kind")
        if self.event_sha256 != digest(self.model_dump(mode="json", exclude={"event_sha256"})):
            raise ValueError("review audit fingerprint mismatch")
        return self


class QueueEntry(Contract):
    entry_id: Sha256
    binding: ReviewBinding
    correlation_id: UUID
    required_reviewer: ReviewerRole
    recommendation_available: bool
    producer_ids: Annotated[tuple[UUID, ...], Field(min_length=1, max_length=65)]
    evidence: Annotated[tuple[EvidenceReference, ...], Field(min_length=1, max_length=256)]
    state: ReviewState
    review_revision: Annotated[int, Field(strict=True, ge=0, le=128)] = 0
    assignments: Annotated[tuple[ReviewAssignment, ...], Field(max_length=2)] = ()
    events: Annotated[tuple[ReviewEvent, ...], Field(max_length=128)] = ()
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def bound_identity(self) -> Self:
        if self.entry_id != digest(self.binding.model_dump(mode="json")):
            raise ValueError("review entry identity must bind its complete advisory snapshot")
        if len(set(self.producer_ids)) != len(self.producer_ids):
            raise ValueError("producer identities must be unique")
        return self


class ReviewDetail(Contract):
    entry: QueueEntry
    advisory_snapshot: Snapshot = Field(repr=False)
    current_case: Case = Field(repr=False)
    content_trust: Literal["untrusted_advisory_and_source_data"] = (
        "untrusted_advisory_and_source_data"
    )


class ReviewLimits(Contract):
    max_entries: Annotated[int, Field(strict=True, ge=1, le=64)] = 16
    max_events_per_entry: Annotated[int, Field(strict=True, ge=3, le=128)] = 64
    max_entry_bytes: Annotated[int, Field(strict=True, ge=65536, le=8388608)] = 4194304
    max_action_bytes: Annotated[int, Field(strict=True, ge=256, le=65536)] = 16384


class ReviewCode(StrEnum):
    DENIED = "review_access_denied"
    STALE = "review_snapshot_stale"
    CONFLICT = "review_revision_or_duplicate_conflict"
    TRANSITION = "review_transition_forbidden"
    INVALID = "review_input_invalid"
    AUDIT = "review_audit_invalid"
    CAPACITY = "review_capacity_exceeded"


class ReviewError(ValueError):
    def __init__(self, code: ReviewCode) -> None:
        self.code = code
        super().__init__(code.value)
