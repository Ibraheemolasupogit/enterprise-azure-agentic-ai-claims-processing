"""Host grants, narrow tool arguments and immutable advisory results."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from claims_ai.agents.contracts import AgentDraft
from claims_ai.knowledge.contracts import PolicyChunk
from claims_ai.models import (
    ClaimId,
    Contract,
    EvidenceId,
    PolicyId,
    ReviewerRole,
    Sha256,
    Text,
    Version,
)
from claims_ai.rules.contracts import EvidenceProvenance, RuleFinding


class ToolName(StrEnum):
    EVIDENCE = "read_claim_evidence"
    POLICY = "read_policy_clauses"
    RULES = "read_rule_findings"


ALLOWLIST = tuple(ToolName)


class Code(StrEnum):
    DENIED = "access_denied"
    SCOPE = "scope_mismatch"
    INPUT = "input_rejected"
    UNAVAILABLE = "service_unavailable"
    RESULT = "invalid_service_result"
    TIMEOUT = "execution_timeout"
    LIMIT = "execution_limit"
    SDK = "framework_failure"
    OUTPUT = "invalid_agent_output"
    ABSTAIN = "model_abstention"


class ToolLimits(Contract):
    timeout_seconds: Annotated[float, Field(strict=True, gt=0, le=30, allow_inf_nan=False)] = 3.0
    tool_timeout_seconds: Annotated[float, Field(strict=True, gt=0, le=5, allow_inf_nan=False)] = (
        1.0
    )
    max_response_bytes: Annotated[int, Field(strict=True, ge=512, le=131072)] = 65536
    max_output_bytes: Annotated[int, Field(strict=True, ge=512, le=32768)] = 16384
    max_model_calls: Literal[4] = 4
    max_tool_calls: Literal[3] = 3


class ReadScope(Contract):
    claim_id: ClaimId
    policy_id: PolicyId
    policy_version: Version
    incident_date: date
    index_sha256: Sha256
    case_sha256: Sha256
    packet_sha256: Sha256
    rule_execution_key: Sha256


class ToolGrant(Contract):
    """Trusted host assertion, never a model/tool argument or an authentication token."""

    principal_id: UUID = Field(repr=False)
    correlation_id: UUID
    claim_id: ClaimId
    case_sha256: Sha256
    permissions: Annotated[tuple[ToolName, ...], Field(max_length=3)]

    @model_validator(mode="after")
    def unique_permissions(self) -> Self:
        if len(set(self.permissions)) != len(self.permissions):
            raise ValueError("duplicate permissions")
        return self


class Arguments(BaseModel):
    model_config = ConfigDict(
        extra="forbid", frozen=True, hide_input_in_errors=True, revalidate_instances="always"
    )


class EvidenceArguments(Arguments):
    claim_id: ClaimId


class PolicyArguments(EvidenceArguments):
    policy_id: PolicyId
    policy_version: Version
    incident_date: date
    index_sha256: Sha256


class RuleArguments(PolicyArguments):
    execution_key: Sha256


class EvidenceView(Contract):
    evidence_id: EvidenceId
    field_name: Version
    value: Text = Field(repr=False)
    provenance: EvidenceProvenance


class EvidenceData(Contract):
    evidence: Annotated[tuple[EvidenceView, ...], Field(min_length=1, max_length=256)] = Field(
        repr=False
    )


class PolicyData(Contract):
    clauses: Annotated[tuple[PolicyChunk, ...], Field(min_length=1, max_length=10)] = Field(
        repr=False
    )


class RuleData(Contract):
    execution_key: Sha256
    findings: Annotated[tuple[RuleFinding, ...], Field(min_length=6, max_length=6)]
    required_reviewer: ReviewerRole


type ToolData = EvidenceData | PolicyData | RuleData


class ToolReply(Contract):
    tool: ToolName
    correlation_id: UUID
    status: Literal["ok", "error"]
    content_trust: Literal["untrusted_data"] = "untrusted_data"
    policy_status: Literal["provisional_unapproved"] = "provisional_unapproved"
    packet_sha256: Sha256 | None = None
    code: Code | None = None
    data: ToolData | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def consistent_reply(self) -> Self:
        expected = {
            ToolName.EVIDENCE: EvidenceData,
            ToolName.POLICY: PolicyData,
            ToolName.RULES: RuleData,
        }
        if self.status == "ok":
            if (
                self.code is not None
                or self.packet_sha256 is None
                or not isinstance(self.data, expected[self.tool])
            ):
                raise ValueError("success requires the matching typed, snapshot-bound payload")
        elif self.data is not None or self.code is None or self.packet_sha256 is not None:
            raise ValueError("safe error must omit data and snapshot identifiers")
        return self


class ToolReceipt(Contract):
    tool: ToolName
    correlation_id: UUID
    status: Literal["ok", "error"]
    code: Code | None = None


class GovernedResult(Contract):
    status: Literal["drafted", "escalated", "abstained"]
    correlation_id: UUID
    reason: Code | None = None
    draft: AgentDraft | None = None
    required_reviewer: ReviewerRole
    framework_executed: bool = False
    model_execution: Literal["SIMULATED"] = "SIMULATED"
    framework_version: Literal["1.23.0"] = "1.23.0"
    model_calls: Annotated[int, Field(strict=True, ge=0, le=4)] = 0
    receipts: Annotated[tuple[ToolReceipt, ...], Field(max_length=3)] = ()
    human_review_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def advisory_only(self) -> Self:
        if any(r.correlation_id != self.correlation_id for r in self.receipts):
            raise ValueError("receipts must retain host correlation")
        if self.status == "abstained":
            if (
                self.draft is not None
                or self.reason is None
                or self.required_reviewer != "supervisor"
            ):
                raise ValueError("abstention requires a supervisor and no draft")
        elif (
            self.reason is not None
            or self.draft is None
            or self.draft.required_reviewer != self.required_reviewer
            or self.draft.disposition != ("review" if self.status == "drafted" else "escalate")
            or self.required_reviewer == "supervisor"
            and self.status != "escalated"
        ):
            raise ValueError("drafts must retain human review disposition")
        return self
