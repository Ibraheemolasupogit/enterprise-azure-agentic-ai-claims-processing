"Pure outcome replay using canonical M2 transitions; no model or policy inference."

from uuid import uuid5

from claims_ai.human_review.contracts import Principal, PrincipalKind
from claims_ai.lifecycle import CaseTransition, TransitionActor, TransitionRequest, transition_case
from claims_ai.models import CaseState, DecisionAction, ReviewerRole
from claims_ai.outcomes.authority import Authority
from claims_ai.outcomes.contracts import (
    Action,
    Assignment,
    Command,
    OutcomeError,
    StoredCase,
    input_hash,
)

HOST_ACTIONS = {Action.REGISTER, Action.PUBLISH, Action.ASSIGN, Action.REVALIDATE}


def reduce(
    authority: Authority, before: StoredCase | None, command: Command, actor: Principal
) -> tuple[StoredCase, tuple[CaseTransition, ...]]:
    authority.known(actor)
    if actor.kind not in {PrincipalKind.HOST, PrincipalKind.HUMAN}:
        raise OutcomeError("operation_not_authorized")
    if (command.action in HOST_ACTIONS) != (actor.kind == PrincipalKind.HOST):
        raise OutcomeError("operation_not_authorized")
    approval = authority.approval(command.approval_id) if command.approval_id else None
    if command.action == Action.REGISTER:
        if before is not None or approval is None or approval.parent is not None:
            raise OutcomeError("already_registered_or_invalid_root")
        if approval.case.claim.claim_id != command.claim_id:
            raise OutcomeError("cross_case_approval")
        return StoredCase(case=approval.case, revision=1, approval_id=approval.approval_id), ()
    if before is None or command.expected != before.binding:
        raise OutcomeError("revision_conflict")
    case, assignments = before.case, before.assignments
    current_approval = before.approval_id
    transitions: list[CaseTransition] = []
    if actor.kind == PrincipalKind.HUMAN:
        authority.assigned(actor, before)
        if actor.principal_id in authority.forbidden(current_approval):
            raise OutcomeError("self_review_forbidden")
        if (
            authority.approval(current_approval).assessment.requires_supervisor
            and actor.role != ReviewerRole.SUPERVISOR
        ):
            raise OutcomeError("supervisor_required")

    def step(target: CaseState) -> None:
        nonlocal case
        event = transition_case(
            case,
            TransitionRequest(
                target=target,
                expected_revision=case.revision,
                actor=TransitionActor(principal_id=actor.principal_id, role=actor.role),
                audit_event_id=uuid5(command.request_id, str(len(transitions))),
                occurred_at=command.occurred_at,
                reason=command.rationale,
                assessment=approval.assessment
                if target == CaseState.AWAITING_REVIEW and approval
                else None,
                decision=command.decision,
            ),
        )
        transitions.append(event)
        case = event.current

    if command.action == Action.ASSIGN:
        if command.assignee_id is None:
            raise OutcomeError("assignee_not_authorized")
        principal = authority.principals.get(command.assignee_id)
        if (
            principal is None
            or principal.kind != PrincipalKind.HUMAN
            or principal.principal_id in authority.forbidden(current_approval)
        ):
            raise OutcomeError("assignee_not_authorized")
        if case.state not in {
            CaseState.ASSESSING,
            CaseState.AWAITING_REVIEW,
            CaseState.VALIDATING,
            CaseState.AWAITING_EVIDENCE,
        }:
            raise OutcomeError("assignment_state_forbidden")
        assignment = Assignment(
            principal=principal,
            input_sha256=input_hash(case),
            assessment_sha256=before.binding.assessment_sha256,
        )
        assignments = tuple(a for a in assignments if a.principal.role != principal.role) + (
            assignment,
        )
        assignments = tuple(sorted(assignments, key=lambda a: str(a.principal.role)))
    elif command.action == Action.PUBLISH:
        if approval is None or approval.approval_id != current_approval or case != approval.case:
            raise OutcomeError("unapproved_publication")
        step(CaseState.AWAITING_REVIEW)
        assignments = ()
    elif command.action == Action.DECIDE:
        decision = command.decision
        if decision is None or decision.decided_at != command.occurred_at:
            raise OutcomeError("decision_time_mismatch")
        step(
            CaseState.AWAITING_EVIDENCE
            if decision.action == DecisionAction.REQUEST_EVIDENCE
            else CaseState.CLOSED
        )
    elif command.action == Action.REOPEN:
        if case.state != CaseState.CLOSED or actor.role != ReviewerRole.SUPERVISOR:
            raise OutcomeError("supervisor_reopening_required")
        step(CaseState.VALIDATING)
        assignments = ()
    elif command.action == Action.CORRECT:
        replacement = command.replacement
        if case.state == CaseState.CLOSED:
            raise OutcomeError("closed_case_requires_reopening")
        if case.state == CaseState.ASSESSING:
            step(CaseState.AWAITING_EVIDENCE)
        step(CaseState.VALIDATING)
        if replacement is None or (
            replacement.state != CaseState.VALIDATING
            or replacement.revision != case.revision + 1
            or replacement.claim.claim_id != case.claim.claim_id
            or replacement.claim.policy_id != case.claim.policy_id
            or replacement.evidence
            or replacement.policy is not None
            or replacement.assessment is not None
            or replacement.decision is not None
        ):
            raise OutcomeError("invalid_correction")
        case, assignments = replacement, ()
    elif command.action == Action.REVALIDATE:
        if (
            approval is None
            or approval.parent != before.binding
            or case.state != CaseState.VALIDATING
        ):
            raise OutcomeError("revalidation_binding_required")
        if (
            approval.bundle.request.intake.claim != case.claim
            or approval.bundle.request.intake.documents != case.documents
        ):
            raise OutcomeError("revalidation_source_mismatch")
        step(CaseState.EXTRACTING)
        step(CaseState.ASSESSING)
        if approval.case.revision != case.revision + 1:
            raise OutcomeError("revalidation_revision_mismatch")
        case, assignments, current_approval = approval.case, (), approval.approval_id
    else:
        raise OutcomeError("forbidden_transition")
    return StoredCase(
        case=case,
        revision=before.revision + 1,
        approval_id=current_approval,
        assignments=assignments,
    ), tuple(transitions)
