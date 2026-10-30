from datetime import datetime, timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from claims_ai.lifecycle import CaseTransition, TransitionActor, TransitionRequest, transition_case
from claims_ai.models import (
    Assessment,
    AssessmentOutcome,
    Case,
    CaseState,
    DecisionAction,
    ReviewerDecision,
    ReviewerRole,
    RiskFlag,
)


@pytest.fixture
def request_data(now: datetime, reviewer_id: UUID) -> TransitionRequest:
    return TransitionRequest(
        target=CaseState.CLOSED,
        expected_revision=5,
        actor=TransitionActor(principal_id=reviewer_id, role=ReviewerRole.REVIEWER),
        audit_event_id=UUID("20000000-0000-0000-0000-000000000001"),
        occurred_at=now,
        reason="Synthetic state transition",
    )


def test_normal_lifecycle_requires_human_decision(
    case: Case,
    assessment: Assessment,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
) -> None:
    original = case
    for state in (
        CaseState.VALIDATING,
        CaseState.EXTRACTING,
        CaseState.ASSESSING,
        CaseState.AWAITING_REVIEW,
    ):
        request = TransitionRequest.model_validate(
            {
                **request_data.model_dump(),
                "target": state,
                "expected_revision": case.revision,
                "assessment": assessment if state == CaseState.AWAITING_REVIEW else None,
                "audit_event_id": UUID(int=case.revision),
                "actor": {"principal_id": request_data.actor.principal_id},
            }
        )
        result = transition_case(case, request)
        assert result.previous == case
        assert result.current.revision == case.revision + 1
        case = result.current
    with pytest.raises(ValueError, match="human decision"):
        transition_case(case, request_data)
    approved = transition_case(
        case, TransitionRequest.model_validate({**request_data.model_dump(), "decision": decision})
    )
    assert approved.current.state == CaseState.CLOSED
    assert approved.current.decision == decision
    assert approved.audit_event_id == request_data.audit_event_id
    assert original.state == CaseState.RECEIVED and original.revision == 1


@pytest.mark.parametrize(
    "target",
    [
        CaseState.RECEIVED,
        CaseState.EXTRACTING,
        CaseState.ASSESSING,
        CaseState.AWAITING_REVIEW,
        CaseState.AWAITING_EVIDENCE,
        CaseState.QUARANTINED,
        CaseState.PROCESSING_FAILED,
        CaseState.CLOSED,
    ],
)
def test_cannot_skip_initial_validation(
    case: Case,
    request_data: TransitionRequest,
    target: CaseState,
) -> None:
    with pytest.raises(ValueError, match="not allowed"):
        transition_case(
            case,
            TransitionRequest.model_validate(
                {**request_data.model_dump(), "expected_revision": 1, "target": target}
            ),
        )


@pytest.mark.parametrize("state", [CaseState.AWAITING_EVIDENCE, CaseState.PROCESSING_FAILED])
def test_recovery_restarts_validation(
    case: Case,
    request_data: TransitionRequest,
    state: CaseState,
) -> None:
    failed = Case.model_validate({**case.model_dump(), "state": state})
    request = TransitionRequest.model_validate(
        {**request_data.model_dump(), "expected_revision": 1, "target": "validating"}
    )
    assert transition_case(failed, request).current.state == CaseState.VALIDATING
    with pytest.raises(ValueError, match="not allowed"):
        transition_case(
            failed,
            TransitionRequest.model_validate({**request.model_dump(), "target": "assessing"}),
        )


@pytest.mark.parametrize(
    "outcome,flag",
    [
        (AssessmentOutcome.INELIGIBLE, None),
        (AssessmentOutcome.UNDETERMINED, None),
        *[(AssessmentOutcome.ELIGIBLE, flag) for flag in RiskFlag],
    ],
)
def test_escalation_cannot_be_bypassed(
    awaiting_case: Case,
    assessment: Assessment,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
    outcome: AssessmentOutcome,
    flag: RiskFlag | None,
) -> None:
    risky = Assessment.model_validate(
        {**assessment.model_dump(), "outcome": outcome, "risk_flags": [flag] if flag else []}
    )
    case = Case.model_validate({**awaiting_case.model_dump(), "assessment": risky})
    action = (
        DecisionAction.OVERRIDE
        if outcome == AssessmentOutcome.UNDETERMINED
        else DecisionAction.APPROVE
    )
    final = AssessmentOutcome.ELIGIBLE if outcome == AssessmentOutcome.UNDETERMINED else outcome
    # A reviewer cannot even request more evidence without supervisor handling of an escalation.
    request_decision = ReviewerDecision.model_validate(
        {**decision.model_dump(), "action": "request_evidence", "outcome": None}
    )
    with pytest.raises(ValueError, match="supervisor"):
        transition_case(
            case,
            TransitionRequest.model_validate(
                {
                    **request_data.model_dump(),
                    "target": "awaiting_evidence",
                    "decision": request_decision,
                }
            ),
        )
    supervisor_decision = ReviewerDecision.model_validate(
        {**decision.model_dump(), "role": "supervisor", "action": action, "outcome": final}
    )
    supervisor_request = TransitionRequest.model_validate(
        {
            **request_data.model_dump(),
            "actor": {"principal_id": decision.reviewer_id, "role": "supervisor"},
            "decision": supervisor_decision,
        }
    )
    assert transition_case(case, supervisor_request).current.state == CaseState.CLOSED


@pytest.mark.parametrize(
    "changes",
    [
        {"expected_case_revision": 4},
        {"assessment_id": "NS-ASM-00000099"},
        {"claim_id": "NS-CLM-00000099"},
        {"reviewer_id": "30000000-0000-0000-0000-000000000001"},
        {"evidence_ids": ["NS-EVD-00000099"]},
        {"outcome": "ineligible"},
    ],
)
def test_invalid_or_stale_decisions(
    awaiting_case: Case,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
    changes: dict[str, object],
) -> None:
    invalid = ReviewerDecision.model_validate({**decision.model_dump(), **changes})
    with pytest.raises(ValueError):
        transition_case(
            awaiting_case,
            TransitionRequest.model_validate({**request_data.model_dump(), "decision": invalid}),
        )


def test_service_actor_cannot_approve(
    awaiting_case: Case,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
) -> None:
    with pytest.raises(ValueError, match="trusted human"):
        transition_case(
            awaiting_case,
            TransitionRequest.model_validate(
                {
                    **request_data.model_dump(),
                    "decision": decision,
                    "actor": {"principal_id": decision.reviewer_id},
                }
            ),
        )


def test_stale_submission_and_future_decision(
    awaiting_case: Case,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
) -> None:
    with pytest.raises(ValueError, match="revision conflict"):
        transition_case(
            awaiting_case,
            TransitionRequest.model_validate(
                {**request_data.model_dump(), "expected_revision": 4, "decision": decision}
            ),
        )
    future = ReviewerDecision.model_validate(
        {**decision.model_dump(), "decided_at": request_data.occurred_at + timedelta(seconds=1)}
    )
    with pytest.raises(ValueError, match="after"):
        transition_case(
            awaiting_case,
            TransitionRequest.model_validate({**request_data.model_dump(), "decision": future}),
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"role": "agent"},
        {"outcome": "undetermined"},
        {"reason": " "},
        {"action": "override"},
        {"action": "request_evidence"},
    ],
)
def test_decision_contract_rejects_invalid_human_actions(
    decision: ReviewerDecision,
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        ReviewerDecision.model_validate({**decision.model_dump(), **changes})


def test_request_evidence_invalidates_snapshot_but_retains_history(
    awaiting_case: Case,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
) -> None:
    followup = ReviewerDecision.model_validate(
        {**decision.model_dump(), "action": "request_evidence", "outcome": None}
    )
    request = TransitionRequest.model_validate(
        {**request_data.model_dump(), "target": "awaiting_evidence", "decision": followup}
    )
    result = transition_case(awaiting_case, request)
    assert result.current.assessment is None and result.current.decision is None
    assert result.previous.assessment is not None and result.decision == followup
    with pytest.raises(ValueError, match="target"):
        transition_case(
            awaiting_case,
            TransitionRequest.model_validate({**request.model_dump(), "target": "closed"}),
        )


def test_reopen_and_quarantine_release_need_supervisor(
    case: Case,
    awaiting_case: Case,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
) -> None:
    closed = transition_case(
        awaiting_case,
        TransitionRequest.model_validate({**request_data.model_dump(), "decision": decision}),
    ).current
    quarantined = Case.model_validate({**case.model_dump(), "state": "quarantined"})
    for source in (closed, quarantined):
        request = TransitionRequest.model_validate(
            {
                **request_data.model_dump(),
                "target": "validating",
                "expected_revision": source.revision,
            }
        )
        with pytest.raises(ValueError, match="supervisor"):
            transition_case(source, request)
        supervisor = TransitionRequest.model_validate(
            {
                **request.model_dump(),
                "actor": {"principal_id": decision.reviewer_id, "role": "supervisor"},
            }
        )
        result = transition_case(source, supervisor)
        assert result.current.assessment is None and result.current.decision is None
        assert result.previous == source


def test_review_and_closed_states_cannot_be_forged(
    case: Case,
    awaiting_case: Case,
    assessment: Assessment,
) -> None:
    with pytest.raises(ValidationError):
        Case.model_validate({**awaiting_case.model_dump(), "state": "closed", "revision": 6})
    with pytest.raises(ValidationError):
        Case.model_validate({**awaiting_case.model_dump(), "revision": 6})
    with pytest.raises(ValidationError):
        Case.model_validate(
            {
                **case.model_dump(),
                "state": "awaiting_review",
                "revision": 5,
                "assessment": assessment,
                "policy": None,
            }
        )


def test_direct_transition_records_use_the_same_guards(
    case: Case,
    awaiting_case: Case,
    request_data: TransitionRequest,
) -> None:
    with pytest.raises(ValidationError, match="not allowed"):
        CaseTransition(
            previous=case,
            current=awaiting_case,
            actor=request_data.actor,
            audit_event_id=request_data.audit_event_id,
            occurred_at=request_data.occurred_at,
            reason="Synthetic invalid direct record",
        )
    next_case = Case.model_validate(
        {
            **case.model_dump(),
            "revision": 2,
            "state": "validating",
            "claim": {**case.claim.model_dump(), "narrative": "Changed without reassessment"},
        }
    )
    with pytest.raises(ValidationError, match="snapshot"):
        CaseTransition(
            previous=case,
            current=next_case,
            actor=request_data.actor,
            audit_event_id=request_data.audit_event_id,
            occurred_at=request_data.occurred_at,
            reason="Synthetic changed input",
        )


def test_high_risk_review_cannot_be_discarded_by_reviewer(
    awaiting_case: Case,
    assessment: Assessment,
    request_data: TransitionRequest,
) -> None:
    risky = Assessment.model_validate({**assessment.model_dump(), "risk_flags": ["high_risk"]})
    case = Case.model_validate({**awaiting_case.model_dump(), "assessment": risky})
    with pytest.raises(ValueError, match="supervisor"):
        transition_case(
            case,
            TransitionRequest.model_validate({**request_data.model_dump(), "target": "validating"}),
        )


def test_override_is_explicit_and_evidence_backed(
    awaiting_case: Case,
    decision: ReviewerDecision,
    request_data: TransitionRequest,
) -> None:
    override = ReviewerDecision.model_validate(
        {
            **decision.model_dump(),
            "role": "supervisor",
            "action": "override",
            "outcome": "ineligible",
        }
    )
    invalid_cases: tuple[dict[str, object], ...] = ({"evidence_ids": []}, {"reason": " "})
    for changes in invalid_cases:
        with pytest.raises(ValidationError):
            ReviewerDecision.model_validate({**override.model_dump(), **changes})
    request = TransitionRequest.model_validate(
        {
            **request_data.model_dump(),
            "decision": override,
            "actor": {"principal_id": decision.reviewer_id, "role": "supervisor"},
        }
    )
    result = transition_case(awaiting_case, request)
    assert result.previous.assessment is not None
    assert result.previous.assessment.outcome == AssessmentOutcome.ELIGIBLE
    assert result.current.decision == override
    assert CaseTransition.model_validate_json(result.model_dump_json()) == result
    with pytest.raises(ValueError, match="explicit supervisor override"):
        transition_case(
            awaiting_case,
            TransitionRequest.model_validate(
                {**request.model_dump(), "decision": {**override.model_dump(), "action": "approve"}}
            ),
        )
