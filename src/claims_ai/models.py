"""Versioned synthetic contracts. Supplied assessments are data, not computed coverage."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    StrictInt,
    StringConstraints,
    field_validator,
    model_validator,
)

ClaimId = Annotated[str, StringConstraints(strict=True, pattern=r"^NS-CLM-[A-Z0-9]{8}$")]
PolicyId = Annotated[str, StringConstraints(strict=True, pattern=r"^NS-POL-[A-Z0-9]{8}$")]
DocumentId = Annotated[str, StringConstraints(strict=True, pattern=r"^NS-DOC-[A-Z0-9]{8}$")]
EvidenceId = Annotated[str, StringConstraints(strict=True, pattern=r"^NS-EVD-[A-Z0-9]{8}$")]
AssessmentId = Annotated[str, StringConstraints(strict=True, pattern=r"^NS-ASM-[A-Z0-9]{8}$")]
Sha256 = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-f0-9]{64}$")]
Version = Annotated[
    str, StringConstraints(strict=True, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
]
Text = Annotated[
    str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=4000)
]
PositiveInt = Annotated[StrictInt, Field(gt=0)]
Coordinate = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class Contract(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_default=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )
    schema_version: Literal["1.0"] = "1.0"
    synthetic: Literal[True] = True

    @field_validator("synthetic", mode="before")
    @classmethod
    def synthetic_only(cls, value: object) -> object:
        if value is not True:
            raise ValueError("only explicitly synthetic records are supported")
        return value


class CaseState(StrEnum):
    RECEIVED = "received"
    VALIDATING = "validating"
    EXTRACTING = "extracting"
    ASSESSING = "assessing"
    AWAITING_REVIEW = "awaiting_review"
    AWAITING_EVIDENCE = "awaiting_evidence"
    QUARANTINED = "quarantined"
    PROCESSING_FAILED = "processing_failed"
    CLOSED = "closed"


class DocumentKind(StrEnum):
    CLAIM_FORM = "claim_form"
    POLICY_SCHEDULE = "policy_schedule"
    POLICY_WORDING = "policy_wording"
    ENDORSEMENT = "endorsement"
    REPAIR_ESTIMATE = "repair_estimate"
    DAMAGE_PHOTO = "damage_photo"


class ScanStatus(StrEnum):
    QUARANTINED = "quarantined"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class AssessmentOutcome(StrEnum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNDETERMINED = "undetermined"


class RiskFlag(StrEnum):
    AMBIGUOUS = "ambiguous"
    HIGH_RISK = "high_risk"
    CONFLICTING = "conflicting"
    INJECTION_FLAGGED = "injection_flagged"
    UNSUPPORTED = "unsupported"


class ReviewerRole(StrEnum):
    REVIEWER = "reviewer"
    SUPERVISOR = "supervisor"


class DecisionAction(StrEnum):
    APPROVE = "approve"
    OVERRIDE = "override"
    REQUEST_EVIDENCE = "request_evidence"


class Claim(Contract):
    claim_id: ClaimId
    policy_id: PolicyId
    loss_at: AwareDatetime
    vehicle_reference: Version
    narrative: Text = Field(repr=False)
    claimed_amount: Annotated[Decimal, Field(ge=0, decimal_places=2, allow_inf_nan=False)]
    currency: Literal["GBP"] = "GBP"
    document_ids: tuple[DocumentId, ...] = ()

    @field_validator("claimed_amount", mode="before")
    @classmethod
    def exact_money_input(cls, value: object) -> object:
        if isinstance(value, (float, bool)):
            raise ValueError("use a decimal string or Decimal, not floating-point money")
        return value

    @field_validator("document_ids")
    @classmethod
    def unique_documents(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(value) != len(set(value)):
            raise ValueError("document references must be unique")
        return value


class DocumentMetadata(Contract):
    document_id: DocumentId
    claim_id: ClaimId
    kind: DocumentKind
    media_type: Literal["application/pdf", "image/jpeg", "image/png"]
    artifact_ref: Text
    sha256: Sha256
    byte_size: PositiveInt
    page_count: PositiveInt
    uploaded_at: AwareDatetime
    scan_status: ScanStatus = ScanStatus.QUARANTINED

    @model_validator(mode="after")
    def valid_reference(self) -> Self:
        suffixes = {
            "application/pdf": ("pdf",),
            "image/jpeg": ("jpg", "jpeg"),
            "image/png": ("png",),
        }[self.media_type]
        refs = {f"synthetic/{self.claim_id}/{self.document_id}.{suffix}" for suffix in suffixes}
        if self.artifact_ref not in refs:
            raise ValueError("artifact reference must be a scoped synthetic object, not a URL/path")
        if self.media_type != "application/pdf" and self.page_count != 1:
            raise ValueError("image documents have exactly one page")
        if self.kind == DocumentKind.DAMAGE_PHOTO and self.media_type == "application/pdf":
            raise ValueError("damage photos must use an image media type")
        return self


class Evidence(Contract):
    evidence_id: EvidenceId
    claim_id: ClaimId
    document_id: DocumentId
    artifact_sha256: Sha256
    page: PositiveInt
    bounding_region: tuple[Coordinate, Coordinate, Coordinate, Coordinate] | None = None
    field_name: Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    observed_value: Text = Field(repr=False)
    normalized_value: Text | None = Field(default=None, repr=False)
    extraction_method: Version
    extraction_version: Version
    confidence: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None
    validation_flags: tuple[Version, ...] = ()

    @model_validator(mode="after")
    def valid_region(self) -> Self:
        if self.bounding_region is not None:
            left, top, right, bottom = self.bounding_region
            if left >= right or top >= bottom:
                raise ValueError("bounding region must be an ordered normalized rectangle")
        return self


class PolicyArtifact(Contract):
    document_id: DocumentId
    sha256: Sha256


class Policy(Contract):
    policy_id: PolicyId
    version: Version
    product: Literal["motor_damage"] = "motor_damage"
    jurisdiction: Literal["GB"] = "GB"
    effective_from: date
    effective_to: date
    schedule: PolicyArtifact
    wording: PolicyArtifact
    endorsements: tuple[PolicyArtifact, ...] = ()
    index_version: Version
    rule_pack_version: Version

    @property
    def artifacts(self) -> tuple[PolicyArtifact, ...]:
        return (self.schedule, self.wording, *self.endorsements)

    @model_validator(mode="after")
    def valid_metadata(self) -> Self:
        if self.effective_from >= self.effective_to:
            raise ValueError("policy effective interval must be nonempty and increasing")
        ids = [item.document_id for item in self.artifacts]
        if len(ids) != len(set(ids)):
            raise ValueError("policy artifact references must be unique")
        return self


class PolicyCitation(Contract):
    policy_id: PolicyId
    policy_version: Version
    document_id: DocumentId
    artifact_sha256: Sha256
    clause_id: Version
    page: PositiveInt


class PolicyClause(Contract):
    citation: PolicyCitation
    text: Text = Field(repr=False)


class RuleResult(Contract):
    """A supplied rule trace; this model neither approves nor evaluates rules."""

    rule_id: Version
    outcome: AssessmentOutcome
    evidence_ids: tuple[EvidenceId, ...]


class Assessment(Contract):
    assessment_id: AssessmentId
    claim_id: ClaimId
    case_revision: PositiveInt
    policy: Policy
    input_sha256: Sha256
    producer_version: Version
    model_version: Version | None = None
    prompt_version: Version | None = None
    tool_version: Version | None = None
    evidence_ids: Annotated[tuple[EvidenceId, ...], Field(min_length=1)]
    citations: tuple[PolicyCitation, ...] = ()
    rule_results: tuple[RuleResult, ...] = ()
    outcome: AssessmentOutcome
    risk_flags: tuple[RiskFlag, ...] = ()
    rationale: Text = Field(repr=False)

    @property
    def requires_supervisor(self) -> bool:
        return self.outcome != AssessmentOutcome.ELIGIBLE or bool(self.risk_flags)

    @model_validator(mode="after")
    def valid_provenance(self) -> Self:
        if len(self.evidence_ids) != len(set(self.evidence_ids)):
            raise ValueError("assessment evidence references must be unique")
        artifacts = {item.document_id: item.sha256 for item in self.policy.artifacts}
        for citation in self.citations:
            if (
                citation.policy_id != self.policy.policy_id
                or citation.policy_version != self.policy.version
                or artifacts.get(citation.document_id) != citation.artifact_sha256
            ):
                raise ValueError("citation must match the exact policy bundle")
        if any(not set(item.evidence_ids) <= set(self.evidence_ids) for item in self.rule_results):
            raise ValueError("rule trace references unknown assessment evidence")
        return self


class ReviewerDecision(Contract):
    claim_id: ClaimId
    assessment_id: AssessmentId
    expected_case_revision: PositiveInt
    reviewer_id: UUID
    role: ReviewerRole
    action: DecisionAction
    outcome: AssessmentOutcome | None = None
    reason: Text = Field(repr=False)
    evidence_ids: tuple[EvidenceId, ...] = ()
    decided_at: AwareDatetime

    @model_validator(mode="after")
    def valid_action(self) -> Self:
        if self.action == DecisionAction.REQUEST_EVIDENCE:
            if self.outcome is not None:
                raise ValueError("requesting evidence cannot finalize an outcome")
        elif self.outcome not in (AssessmentOutcome.ELIGIBLE, AssessmentOutcome.INELIGIBLE):
            raise ValueError("closure needs an explicit eligible/ineligible human outcome")
        elif not self.evidence_ids:
            raise ValueError("closure requires explicit reviewer evidence references")
        if self.action == DecisionAction.OVERRIDE:
            if self.role != ReviewerRole.SUPERVISOR or not self.evidence_ids:
                raise ValueError("override requires a supervisor, reason and evidence")
        return self


def validate_decision(assessment: Assessment, decision: ReviewerDecision, revision: int) -> None:
    if (
        decision.claim_id != assessment.claim_id
        or decision.assessment_id != assessment.assessment_id
        or decision.expected_case_revision != revision
    ):
        raise ValueError("decision must reference the current claim, assessment and case revision")
    needs_supervisor = (
        assessment.requires_supervisor or decision.outcome == AssessmentOutcome.INELIGIBLE
    )
    if needs_supervisor and decision.role != ReviewerRole.SUPERVISOR:
        raise ValueError("assessment or adverse outcome requires supervisor review")
    if decision.action == DecisionAction.APPROVE and decision.outcome != assessment.outcome:
        raise ValueError("a changed outcome requires an explicit supervisor override")
    if not set(decision.evidence_ids) <= set(assessment.evidence_ids):
        raise ValueError("decision references unknown assessment evidence")


class Case(Contract):
    claim: Claim
    revision: PositiveInt = 1
    state: CaseState = CaseState.RECEIVED
    policy: Policy | None = None
    documents: tuple[DocumentMetadata, ...] = ()
    evidence: tuple[Evidence, ...] = ()
    assessment: Assessment | None = None
    decision: ReviewerDecision | None = None

    @model_validator(mode="after")
    def consistent_case(self) -> Self:
        docs = {item.document_id: item for item in self.documents}
        if len(docs) != len(self.documents) or set(docs) != set(self.claim.document_ids):
            raise ValueError("case documents must exactly match unique claim document references")
        if any(item.claim_id != self.claim.claim_id for item in self.documents):
            raise ValueError("cross-case document references are forbidden")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("case evidence IDs must be unique")
        for item in self.evidence:
            doc = docs.get(item.document_id)
            if (
                item.claim_id != self.claim.claim_id
                or doc is None
                or item.artifact_sha256 != doc.sha256
                or item.page > doc.page_count
                or doc.scan_status != ScanStatus.ACCEPTED
            ):
                raise ValueError("evidence requires accepted, matching, case-scoped provenance")
        if self.policy is not None and self.policy.policy_id != self.claim.policy_id:
            raise ValueError("case policy metadata must match the claim policy ID")
        if self.state in (CaseState.AWAITING_REVIEW, CaseState.CLOSED):
            assessment = self.assessment
            if assessment is None or self.policy is None:
                raise ValueError("review/closure requires an assessment and exact policy metadata")
            offset = 2 if self.state == CaseState.CLOSED else 1
            if (
                assessment.claim_id != self.claim.claim_id
                or assessment.case_revision != self.revision - offset
                or assessment.policy != self.policy
                or not set(assessment.evidence_ids) <= {item.evidence_id for item in self.evidence}
            ):
                raise ValueError("assessment snapshot or evidence is stale/mismatched")
        elif self.assessment is not None:
            raise ValueError("assessment must be invalidated outside review/closed states")
        if self.state == CaseState.CLOSED:
            if self.decision is None or self.assessment is None:
                raise ValueError("closure requires a human reviewer decision")
            validate_decision(self.assessment, self.decision, self.revision - 1)
            if self.decision.action == DecisionAction.REQUEST_EVIDENCE:
                raise ValueError("requesting evidence cannot close a case")
        elif self.decision is not None:
            raise ValueError("only closed cases hold a final reviewer decision")
        return self


def validate_required_evidence(case: Case, required: frozenset[DocumentKind]) -> None:
    """Check a caller-supplied document checklist, not an unapproved coverage rule."""
    case = Case.model_validate(case)
    referenced = {item.document_id for item in case.evidence}
    available = {
        doc.kind
        for doc in case.documents
        if doc.scan_status == ScanStatus.ACCEPTED and doc.document_id in referenced
    }
    if not required <= available:
        raise ValueError("required evidence is missing or has not passed validation/extraction")
