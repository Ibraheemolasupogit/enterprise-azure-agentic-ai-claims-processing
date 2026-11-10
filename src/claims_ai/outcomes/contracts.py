"Versioned synthetic outcome commands; approval is independent from advisory review."

from base64 import b64decode
from copy import deepcopy
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.human_review.contracts import Principal
from claims_ai.lifecycle import CaseTransition
from claims_ai.models import Assessment, Case, ClaimId, Contract, ReviewerDecision, Sha256, Text
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import Checkpoint, WorkflowLimits, WorkflowRequest


class OutcomeError(ValueError):
    """Only fixed codes cross this local service boundary."""


class RecoveryBundle(Contract):
    format: Literal["m20-recovery-v1"] = "m20-recovery-v1"
    request: WorkflowRequest = Field(repr=False)
    contents: Annotated[tuple[str, ...], Field(max_length=64)] = Field(repr=False)
    grant: ToolGrant
    checkpoint: Checkpoint = Field(repr=False)
    limits: WorkflowLimits = WorkflowLimits()
    runtime_sha256: Sha256

    @model_validator(mode="before")
    @classmethod
    def explicit_bytes(cls, value: object) -> object:
        if isinstance(value, dict) and isinstance(value.get("request"), dict):
            value = deepcopy(value)
            contents = value.get("contents", [])
            inputs = value["request"].get("evidence_inputs", [])
            if not isinstance(contents, (list, tuple)) or len(contents) != len(inputs):
                raise ValueError("missing recovery bytes")
            if sum(len(c) for c in contents if isinstance(c, str)) > 12000000:
                raise ValueError("recovery byte capacity")
            for item, content in zip(inputs, contents, strict=True):
                item["request"]["content"] = b64decode(content, validate=True)
        return value


class Binding(Contract):
    claim_id: ClaimId
    revision: Annotated[int, Field(strict=True, ge=1, le=128)]
    case_revision: Annotated[int, Field(strict=True, ge=1)]
    case_sha256: Sha256
    policy_sha256: Sha256
    assessment_sha256: Sha256


class ApprovedInput(Contract):
    format: Literal["m20-approved-synthetic-v1"] = "m20-approved-synthetic-v1"
    approval_id: UUID
    approved_by: UUID
    rationale: Text
    case: Case = Field(repr=False)
    assessment: Assessment = Field(repr=False)
    bundle: RecoveryBundle = Field(repr=False)
    parent: Binding | None = None
    purpose: Literal["explicitly_approved_synthetic_test_assessment"] = (
        "explicitly_approved_synthetic_test_assessment"
    )
    actual_insurance_authority: Literal[False] = False
    settlement_authorized: Literal[False] = False


class Action(StrEnum):
    REGISTER = "register"
    PUBLISH = "publish_assessment"
    ASSIGN = "assign"
    DECIDE = "human_decision"
    CORRECT = "correct_inputs"
    REOPEN = "reopen"
    REVALIDATE = "revalidate"


class Command(Contract):
    format: Literal["m20-command-v1"] = "m20-command-v1"
    request_id: UUID
    correlation_id: UUID
    claim_id: ClaimId
    action: Action
    occurred_at: AwareDatetime
    rationale: Text
    expected: Binding | None = None
    approval_id: UUID | None = None
    assignee_id: UUID | None = None
    decision: ReviewerDecision | None = None
    replacement: Case | None = Field(default=None, repr=False)

    @model_validator(mode="after")
    def payload(self) -> Self:
        actual = (
            self.approval_id is not None,
            self.assignee_id is not None,
            self.decision is not None,
            self.replacement is not None,
        )
        expected = {
            Action.REGISTER: (True, False, False, False),
            Action.PUBLISH: (True, False, False, False),
            Action.REVALIDATE: (True, False, False, False),
            Action.ASSIGN: (False, True, False, False),
            Action.DECIDE: (False, False, True, False),
            Action.CORRECT: (False, False, False, True),
            Action.REOPEN: (False, False, False, False),
        }[self.action]
        if actual != expected or (self.expected is None) != (self.action == Action.REGISTER):
            raise ValueError("command payload/precondition mismatch")
        if self.expected is not None and self.expected.claim_id != self.claim_id:
            raise ValueError("cross-case precondition")
        if self.decision is not None and (
            self.decision.claim_id != self.claim_id
            or self.decision.reason != self.rationale
            or len(set(self.decision.evidence_ids)) != len(self.decision.evidence_ids)
        ):
            raise ValueError("decision rationale/reference mismatch")
        return self


class Assignment(Contract):
    principal: Principal
    input_sha256: Sha256
    assessment_sha256: Sha256


def input_hash(case: Case) -> str:
    return digest(
        case.model_dump(mode="json", exclude={"revision", "state", "assessment", "decision"})
    )


class StoredCase(Contract):
    format: Literal["m20-state-v1"] = "m20-state-v1"
    case: Case = Field(repr=False)
    revision: Annotated[int, Field(strict=True, ge=1, le=128)]
    approval_id: UUID
    assignments: Annotated[tuple[Assignment, ...], Field(max_length=2)] = ()
    actual_insurance_authority: Literal[False] = False
    settlement_authorized: Literal[False] = False

    @property
    def binding(self) -> Binding:
        return Binding(
            claim_id=self.case.claim.claim_id,
            revision=self.revision,
            case_revision=self.case.revision,
            case_sha256=digest(self.case.model_dump(mode="json")),
            policy_sha256=digest(
                self.case.policy.model_dump(mode="json") if self.case.policy else None
            ),
            assessment_sha256=digest(
                self.case.assessment.model_dump(mode="json") if self.case.assessment else None
            ),
        )


class AuditEvent(Contract):
    format: Literal["m20-audit-v1"] = "m20-audit-v1"
    event_id: UUID
    actor: Principal
    command: Command
    after: StoredCase = Field(repr=False)
    transitions: Annotated[tuple[CaseTransition, ...], Field(max_length=2)] = ()
    previous_sha256: Sha256
    event_sha256: Sha256

    @model_validator(mode="after")
    def fingerprint(self) -> Self:
        if self.event_sha256 != digest(self.model_dump(mode="json", exclude={"event_sha256"})):
            raise ValueError("audit fingerprint mismatch")
        return self
