"""Immutable workflow inputs, stage records and caller-held checkpoints."""

from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from claims_ai.agent_tools.contracts import GovernedResult, ToolLimits
from claims_ai.evidence.contracts import EvidenceAdmission, EvidenceHistory
from claims_ai.knowledge.contracts import KnowledgeIndex, RetrievalRequest, RetrievalResponse
from claims_ai.lifecycle import CaseTransition
from claims_ai.models import (
    Case,
    ClaimId,
    Contract,
    Policy,
    ReviewerRole,
    RiskFlag,
    Sha256,
    Text,
    Version,
)
from claims_ai.rules.contracts import (
    EvidenceInput,
    ReviewedFacts,
    RuleEvaluation,
    RuleSpecification,
)
from claims_ai.rules.specification import digest


class Stage(StrEnum):
    INTAKE = "intake"
    EVIDENCE = "evidence"
    POLICY = "policy"
    RULES = "rules"
    AGENT = "agent"
    ROUTING = "routing"


STAGES = tuple(Stage)


class State(StrEnum):
    READY = "ready"
    PAUSED = "paused"
    REVIEW = "awaiting_human_review"
    SUPERVISOR = "awaiting_supervisor_review"
    EVIDENCE = "awaiting_evidence"
    QUARANTINED = "quarantined"
    ABSTAINED = "abstained"
    FAILED = "failed"
    REJECTED = "rejected"


class Code(StrEnum):
    DENIED = "access_denied"
    INTAKE = "invalid_intake"
    MISSING = "missing_evidence"
    UNTRUSTED = "untrusted_or_conflicting_evidence"
    POLICY = "policy_unavailable_or_unverifiable"
    RULES = "rule_prerequisite_failed"
    AGENT = "agent_abstention"
    DEPENDENCY = "dependency_unavailable"
    TIMEOUT = "cooperative_timeout"
    CANCELLED = "execution_cancelled"
    INVALID = "invalid_stage_output"


class WorkflowLimits(Contract):
    max_attempts: Literal[1, 2] = 2
    run_timeout_seconds: Annotated[float, Field(strict=True, gt=0, le=60, allow_inf_nan=False)] = (
        15.0
    )
    stage_timeout_seconds: Annotated[
        float, Field(strict=True, gt=0, le=10, allow_inf_nan=False)
    ] = 3.0
    max_checkpoint_bytes: Annotated[int, Field(strict=True, ge=65536, le=8388608)] = 4194304
    tools: ToolLimits = ToolLimits()


class WorkflowRequest(Contract):
    request_id: Version
    requested_at: AwareDatetime
    intake: Case
    evidence_inputs: Annotated[tuple[EvidenceInput, ...], Field(max_length=64)] = Field(repr=False)
    policies: Annotated[tuple[Policy, ...], Field(max_length=16)]
    policy_version: Version | None
    specification: RuleSpecification
    reviewed_facts: Annotated[tuple[ReviewedFacts, ...], Field(max_length=16)] = ()
    risk_flags: tuple[RiskFlag, ...] = ()
    allow_simulated_evidence: Annotated[bool, Field(strict=True)] = False
    untrusted_note: Text = Field(default="Prepare a bounded advisory review.", repr=False)


class ReviewTask(Contract):
    claim_id: ClaimId
    case_sha256: Sha256
    correlation_id: UUID
    required_reviewer: ReviewerRole
    reason: Code | Literal["advisory_ready"]
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False


class Snapshot(Contract):
    case: Case
    transitions: Annotated[tuple[CaseTransition, ...], Field(max_length=8)] = ()
    admissions: Annotated[tuple[EvidenceAdmission, ...], Field(max_length=64)] = ()
    history: EvidenceHistory | None = Field(default=None, repr=False)
    index: KnowledgeIndex | None = Field(default=None, repr=False)
    retrieval_request: RetrievalRequest | None = None
    retrieval_response: RetrievalResponse | None = Field(default=None, repr=False)
    rule_evaluation: RuleEvaluation | None = None
    agent_result: GovernedResult | None = None
    review_task: ReviewTask | None = None


class Step(Contract):
    snapshot: Snapshot
    outcome: Literal["succeeded", "blocked", "retryable"] = "succeeded"
    code: Code | None = None
    state: State = State.PAUSED
    agent_attempt: GovernedResult | None = None

    @model_validator(mode="after")
    def consistent_outcome(self) -> Self:
        if self.outcome == "succeeded":
            if self.code is not None or self.state not in {
                State.PAUSED,
                State.REVIEW,
                State.SUPERVISOR,
            }:
                raise ValueError("success must be a checkpoint or human-review route")
        elif self.outcome == "retryable":
            if self.code not in {
                Code.DEPENDENCY,
                Code.TIMEOUT,
                Code.CANCELLED,
            } or self.state not in {
                State.PAUSED,
                State.FAILED,
            }:
                raise ValueError("only bounded technical failures can retry")
        elif self.code is None or self.state not in {
            State.EVIDENCE,
            State.QUARANTINED,
            State.ABSTAINED,
            State.REJECTED,
            State.FAILED,
        }:
            raise ValueError("blocked stage must have an explicit safe terminal state")
        return self


class StageRecord(Contract):
    sequence: Annotated[int, Field(strict=True, ge=1, le=12)]
    stage: Stage
    attempt: Annotated[int, Field(strict=True, ge=1, le=2)]
    correlation_id: UUID
    input_sha256: Sha256
    output_sha256: Sha256
    previous_sha256: Sha256
    step: Step
    record_sha256: Sha256

    @model_validator(mode="after")
    def valid_hashes(self) -> Self:
        if self.output_sha256 != digest(
            self.step.snapshot.model_dump(mode="json")
        ) or self.record_sha256 != digest(self.model_dump(mode="json", exclude={"record_sha256"})):
            raise ValueError("stage record fingerprint mismatch")
        return self


class Checkpoint(Contract):
    workflow_version: Literal["offline-claims-v1"] = "offline-claims-v1"
    execution_key: Sha256
    correlation_id: UUID
    max_attempts: Literal[1, 2]
    initial: Snapshot
    records: Annotated[tuple[StageRecord, ...], Field(max_length=12)] = ()
    state: State = State.READY
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @property
    def snapshot(self) -> Snapshot:
        return self.records[-1].step.snapshot if self.records else self.initial

    @property
    def next_stage(self) -> Stage | None:
        if self.state not in {State.READY, State.PAUSED}:
            return None
        if not self.records:
            return Stage.INTAKE
        last = self.records[-1]
        return (
            last.stage if last.step.outcome == "retryable" else STAGES[STAGES.index(last.stage) + 1]
        )

    @model_validator(mode="after")
    def ordered_history(self) -> Self:
        expected, attempt = Stage.INTAKE, 1
        previous = self.execution_key
        snapshot = self.initial
        terminal = False
        for number, record in enumerate(self.records, start=1):
            if (
                terminal
                or record.sequence != number
                or record.stage != expected
                or record.attempt != attempt
                or record.attempt > self.max_attempts
                or record.previous_sha256 != previous
                or record.correlation_id != self.correlation_id
                or record.input_sha256 != digest(snapshot.model_dump(mode="json"))
                or record.step.snapshot.case.claim.claim_id != self.initial.case.claim.claim_id
            ):
                raise ValueError("invalid workflow order, binding, retry or hash chain")
            if record.step.outcome == "retryable":
                exhausted = record.attempt == self.max_attempts
                expected_snapshot = snapshot
                if exhausted:
                    if record.step.code is None:
                        raise ValueError("failed retry needs a reason")
                    task = ReviewTask(
                        claim_id=snapshot.case.claim.claim_id,
                        case_sha256=digest(snapshot.case.model_dump(mode="json")),
                        correlation_id=self.correlation_id,
                        required_reviewer=ReviewerRole.SUPERVISOR,
                        reason=record.step.code,
                    )
                    expected_snapshot = Snapshot.model_validate(
                        {
                            **snapshot.model_dump(),
                            "review_task": task,
                        }
                    )
                if record.step.snapshot != expected_snapshot:
                    raise ValueError(
                        "failed attempts retain processing data and safe terminal routing"
                    )
                if record.step.state != (State.FAILED if exhausted else State.PAUSED):
                    raise ValueError("retry budget cannot be reset")
                attempt += 1
            elif record.step.outcome == "succeeded" and record.stage != Stage.ROUTING:
                if record.step.state != State.PAUSED:
                    raise ValueError("only routing can complete successful processing")
                expected, attempt = STAGES[STAGES.index(record.stage) + 1], 1
            elif record.step.outcome == "succeeded" and record.stage == Stage.ROUTING:
                if record.step.state not in {State.REVIEW, State.SUPERVISOR}:
                    raise ValueError("successful routing must require human review")
            terminal = record.step.state not in {State.PAUSED, State.READY}
            snapshot, previous = record.step.snapshot, record.record_sha256
        if self.state != (self.records[-1].step.state if self.records else State.READY):
            raise ValueError("checkpoint state must follow its validated record history")
        return self
