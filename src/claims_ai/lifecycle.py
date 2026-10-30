"""Pure transitions. Caller supplies trusted identity/time/IDs; no audit store exists yet."""

from types import MappingProxyType
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from claims_ai.models import (
    Assessment,
    Case,
    CaseState,
    Contract,
    DecisionAction,
    PositiveInt,
    ReviewerDecision,
    ReviewerRole,
    Text,
    validate_decision,
)

ALLOWED_TRANSITIONS = MappingProxyType(
    {
        CaseState.RECEIVED: frozenset({CaseState.VALIDATING}),
        CaseState.VALIDATING: frozenset(
            {
                CaseState.EXTRACTING,
                CaseState.AWAITING_EVIDENCE,
                CaseState.QUARANTINED,
                CaseState.PROCESSING_FAILED,
            }
        ),
        CaseState.EXTRACTING: frozenset(
            {
                CaseState.ASSESSING,
                CaseState.AWAITING_EVIDENCE,
                CaseState.QUARANTINED,
                CaseState.PROCESSING_FAILED,
            }
        ),
        CaseState.ASSESSING: frozenset(
            {
                CaseState.AWAITING_REVIEW,
                CaseState.AWAITING_EVIDENCE,
                CaseState.QUARANTINED,
                CaseState.PROCESSING_FAILED,
            }
        ),
        CaseState.AWAITING_REVIEW: frozenset(
            {CaseState.CLOSED, CaseState.AWAITING_EVIDENCE, CaseState.VALIDATING}
        ),
        CaseState.AWAITING_EVIDENCE: frozenset({CaseState.VALIDATING}),
        CaseState.QUARANTINED: frozenset({CaseState.VALIDATING}),
        CaseState.PROCESSING_FAILED: frozenset({CaseState.VALIDATING}),
        CaseState.CLOSED: frozenset({CaseState.VALIDATING}),
    }
)


class TransitionActor(Contract):
    """Trusted caller context; role assertions are not authentication or authorization."""

    principal_id: UUID
    role: ReviewerRole | None = None  # None means a nonhuman workflow/service caller.


class CaseTransition(Contract):
    previous: Case
    current: Case
    actor: TransitionActor
    audit_event_id: UUID
    occurred_at: AwareDatetime
    reason: Text = Field(repr=False)
    decision: ReviewerDecision | None = None

    @model_validator(mode="after")
    def consistent_revisions(self) -> "CaseTransition":
        request = TransitionRequest(
            target=self.current.state,
            expected_revision=self.previous.revision,
            actor=self.actor,
            audit_event_id=self.audit_event_id,
            occurred_at=self.occurred_at,
            reason=self.reason,
            assessment=(
                self.current.assessment if self.current.state == CaseState.AWAITING_REVIEW else None
            ),
            decision=self.decision,
        )
        if self.current != _next_case(self.previous, request):
            raise ValueError("transition snapshot must match the validated next case")
        return self


class TransitionRequest(Contract):
    target: CaseState
    expected_revision: PositiveInt
    actor: TransitionActor
    audit_event_id: UUID
    occurred_at: AwareDatetime
    reason: Text = Field(repr=False)
    assessment: Assessment | None = None
    decision: ReviewerDecision | None = None


def _next_case(case: Case, request: TransitionRequest) -> Case:
    target = request.target
    if request.expected_revision != case.revision:
        raise ValueError("case revision conflict")
    if target not in ALLOWED_TRANSITIONS[case.state]:
        raise ValueError("case transition is not allowed")
    if case.state in (CaseState.CLOSED, CaseState.QUARANTINED):
        if request.actor.role != ReviewerRole.SUPERVISOR:
            raise ValueError("reopening or releasing quarantine requires a supervisor")
    if (
        case.state == CaseState.AWAITING_REVIEW
        and case.assessment is not None
        and case.assessment.requires_supervisor
        and request.actor.role != ReviewerRole.SUPERVISOR
    ):
        raise ValueError("escalated review transitions require a supervisor")
    if request.assessment is not None and target != CaseState.AWAITING_REVIEW:
        raise ValueError("assessment can only be submitted for human review")
    if target == CaseState.AWAITING_REVIEW and request.assessment is None:
        raise ValueError("submitting for review requires a current assessment")
    decision = request.decision
    if decision is not None:
        if case.state != CaseState.AWAITING_REVIEW or case.assessment is None:
            raise ValueError("review decisions require a case awaiting review")
        if (
            request.actor.principal_id != decision.reviewer_id
            or request.actor.role != decision.role
        ):
            raise ValueError("review decision does not match trusted human caller context")
        validate_decision(case.assessment, decision, case.revision)
        if decision.decided_at > request.occurred_at:
            raise ValueError("decision cannot occur after its transition")
        required_target = (
            CaseState.AWAITING_EVIDENCE
            if decision.action == DecisionAction.REQUEST_EVIDENCE
            else CaseState.CLOSED
        )
        if target != required_target:
            raise ValueError("decision action does not match transition target")
    if target == CaseState.CLOSED and decision is None:
        raise ValueError("closure requires an explicit human decision")
    if case.state == CaseState.AWAITING_REVIEW and target != CaseState.CLOSED:
        if request.actor.role is None:
            raise ValueError("invalidating reviewed evidence requires a human actor")
    values = case.model_dump()
    values.update(
        state=target,
        revision=case.revision + 1,
        assessment=request.assessment if target == CaseState.AWAITING_REVIEW else None,
        decision=None,
    )
    if target == CaseState.CLOSED:
        values.update(assessment=case.assessment, decision=decision)
    return Case.model_validate(values)


def transition_case(case: Case, request: TransitionRequest) -> CaseTransition:
    """Return an immutable transition record; persistence must atomically store it later."""
    case = Case.model_validate(case)
    request = TransitionRequest.model_validate(request)
    current = _next_case(case, request)
    return CaseTransition(
        previous=case,
        current=current,
        actor=request.actor,
        audit_event_id=request.audit_event_id,
        occurred_at=request.occurred_at,
        reason=request.reason,
        decision=request.decision,
    )
