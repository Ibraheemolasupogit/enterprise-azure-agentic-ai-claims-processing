"""Review packets/drafts compose unchanged domain, retrieval and provisional-rule contracts."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from claims_ai.knowledge.contracts import PolicyChunk, RetrievalRequest, RetrievalResponse
from claims_ai.models import (
    ClaimId,
    Contract,
    Evidence,
    EvidenceId,
    PolicyCitation,
    ReviewerRole,
    Sha256,
    Text,
)
from claims_ai.rules.contracts import (
    EvaluationRequest,
    FindingStatus,
    RuleEvaluation,
    RuleFinding,
    RuleId,
    RuleSpecification,
)


class Reason(StrEnum):
    UNSUPPORTED = "unsupported_request"
    INPUT = "invalid_or_stale_input"
    EVIDENCE = "missing_or_unverified_evidence"
    RETRIEVAL = "retrieval_unavailable"
    CITATIONS = "insufficient_or_invalid_citations"
    TIMEOUT = "execution_timeout"
    BUDGET = "execution_limit"
    SDK = "framework_or_tool_failure"
    OUTPUT = "invalid_or_unsupported_output"
    MODEL_ABSTENTION = "model_abstention"


class Limits(Contract):
    timeout_seconds: Annotated[float, Field(strict=True, gt=0, le=30, allow_inf_nan=False)] = 3.0
    max_model_calls: Literal[2] = 2
    max_tool_calls: Literal[1] = 1
    max_packet_bytes: Annotated[int, Field(strict=True, ge=512, le=131072)] = 65536
    max_output_bytes: Annotated[int, Field(strict=True, ge=512, le=32768)] = 16384
    max_tokens: Annotated[int, Field(strict=True, ge=1, le=4096)] = 2048


class AssessmentInput(Contract):
    rule_request: EvaluationRequest
    specification: RuleSpecification
    rule_evaluation: RuleEvaluation
    retrieval_request: RetrievalRequest | None = None
    retrieval_response: RetrievalResponse | None = None
    task: Literal["explain_findings", "coverage_decision", "unsupported_policy_conclusion"] = (
        "explain_findings"
    )
    untrusted_note: Text = Field(default="Prepare a source-linked human review packet.", repr=False)


class ReviewPacket(Contract):
    claim_id: ClaimId
    case_sha256: Sha256
    rule_execution_key: Sha256
    packet_sha256: Sha256
    policy_status: Literal["provisional_unapproved"] = "provisional_unapproved"
    content_trust: Literal["untrusted_document_and_retrieved_data"] = (
        "untrusted_document_and_retrieved_data"
    )
    required_reviewer: ReviewerRole
    findings: tuple[RuleFinding, ...]
    evidence: tuple[Evidence, ...] = Field(repr=False)
    clauses: Annotated[tuple[PolicyChunk, ...], Field(max_length=10)] = Field(repr=False)


class FindingSummary(Contract):
    rule_id: RuleId
    status: FindingStatus
    evidence_ids: tuple[EvidenceId, ...]
    citations: tuple[PolicyCitation, ...]
    explanation: Text


class AgentDraft(Contract):
    claim_id: ClaimId
    packet_sha256: Sha256
    disposition: Literal["review", "escalate", "abstain"]
    required_reviewer: ReviewerRole
    findings: Annotated[tuple[FindingSummary, ...], Field(max_length=6)]
    human_review_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def advisory_only(self) -> Self:
        if self.disposition == "abstain":
            if self.findings or self.required_reviewer != ReviewerRole.SUPERVISOR:
                raise ValueError("abstention must contain no conclusions and require a supervisor")
        elif len(self.findings) != 6 or {f.rule_id for f in self.findings} != set(RuleId):
            raise ValueError("a review draft must account for all six deterministic findings")
        return self


class AgentResult(Contract):
    status: Literal["drafted", "escalated", "abstained"]
    reason: Reason | None = None
    draft: AgentDraft | None = None
    framework_executed: bool
    model_execution: Literal["SIMULATED"] = "SIMULATED"
    framework_version: Literal["1.23.0"] = "1.23.0"
    model_calls: Annotated[int, Field(ge=0, le=2)] = 0
    tool_executions: Annotated[int, Field(ge=0, le=1)] = 0
    required_reviewer: ReviewerRole
    human_review_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def safe_result(self) -> Self:
        if self.status == "abstained":
            if (
                self.draft is not None
                or self.reason is None
                or self.required_reviewer != ReviewerRole.SUPERVISOR
            ):
                raise ValueError("abstention is an explicit supervisor exception without a draft")
        elif (
            self.draft is None
            or self.reason is not None
            or self.draft.required_reviewer != self.required_reviewer
        ):
            raise ValueError("successful result must carry a matching advisory draft")
        return self
