"""Pure snapshot verification and audit replay; no model execution or outcome publication."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.contracts import (
    OPEN_STATES,
    EventKind,
    EvidenceReference,
    Principal,
    PrincipalKind,
    QueueEntry,
    ReviewAction,
    ReviewAssignment,
    ReviewBinding,
    ReviewCode,
    ReviewDecision,
    ReviewError,
    ReviewEvent,
    ReviewState,
)
from claims_ai.lifecycle import CaseTransition, TransitionActor, TransitionRequest, transition_case
from claims_ai.models import CaseState, ReviewerRole
from claims_ai.rules.contracts import FindingStatus
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import (
    Checkpoint,
    Code,
    Snapshot,
    Stage,
    State,
    WorkflowLimits,
    WorkflowRequest,
)
from claims_ai.workflow.engine import execution_key, restore
from claims_ai.workflow.stages import Context


@dataclass(frozen=True)
class VerifiedAdvisory:
    initial: QueueEntry
    snapshot: Snapshot
    requested_at: datetime


async def verify_advisory(
    request: WorkflowRequest,
    grant: ToolGrant,
    checkpoint: Checkpoint,
    limits: WorkflowLimits,
) -> VerifiedAdvisory:
    request = WorkflowRequest.model_validate(request)
    grant = ToolGrant.model_validate(grant)
    limits = WorkflowLimits.model_validate(limits)
    checkpoint = await restore(
        request, Context(request, grant, execution_key(request, grant, limits), limits), checkpoint
    )
    snapshot = checkpoint.snapshot
    task, rules, result, query = (
        snapshot.review_task,
        snapshot.rule_evaluation,
        snapshot.agent_result,
        snapshot.retrieval_request,
    )
    if (
        not checkpoint.records
        or snapshot.case.state != CaseState.ASSESSING
        or task is None
        or rules is None
        or query is None
        or query.policy_version is None
        or snapshot.index is None
    ):
        raise ReviewError(ReviewCode.INVALID)
    recommendation_available = result is not None and result.draft is not None
    if recommendation_available:
        if (
            checkpoint.state not in {State.REVIEW, State.SUPERVISOR}
            or checkpoint.records[-1].stage != Stage.ROUTING
            or task.reason != "advisory_ready"
        ):
            raise ReviewError(ReviewCode.INVALID)
    elif (
        checkpoint.state != State.ABSTAINED
        or task.required_reviewer != ReviewerRole.SUPERVISOR
        or task.reason not in {Code.RULES, Code.AGENT}
    ):
        raise ReviewError(ReviewCode.INVALID)
    policy = next(
        entry.policy
        for entry in snapshot.index.entries
        if entry.policy.policy_id == query.policy_id
        and entry.policy.version == query.policy_version
    )
    binding = ReviewBinding(
        claim_id=snapshot.case.claim.claim_id,
        case_revision=snapshot.case.revision,
        case_sha256=digest(snapshot.case.model_dump(mode="json")),
        evidence_sha256=digest(
            {
                "documents": [d.model_dump(mode="json") for d in snapshot.case.documents],
                "evidence": [e.model_dump(mode="json") for e in snapshot.case.evidence],
                "history": snapshot.history.model_dump(mode="json") if snapshot.history else None,
            }
        ),
        policy_id=policy.policy_id,
        policy_version=policy.version,
        policy_sha256=digest(policy.model_dump(mode="json")),
        index_sha256=query.index_sha256,
        rule_version=request.specification.version,
        rule_sha256=rules.specification_sha256,
        rule_execution_key=rules.execution_key,
        workflow_execution_key=checkpoint.execution_key,
        checkpoint_sha256=digest(checkpoint.model_dump(mode="json")),
        advisory_task_sha256=digest(task.model_dump(mode="json")),
        advisory_sha256=digest(
            result.model_dump(mode="json") if result else {"advisory_unavailable": task.reason}
        ),
    )
    required = (
        ReviewerRole.SUPERVISOR
        if rules.risk_flags
        or any(
            f.status in {FindingStatus.FAIL, FindingStatus.INDETERMINATE} for f in rules.findings
        )
        or ReviewerRole.SUPERVISOR in {rules.required_reviewer, task.required_reviewer}
        else ReviewerRole.REVIEWER
    )
    initial = QueueEntry(
        entry_id=digest(binding.model_dump(mode="json")),
        binding=binding,
        correlation_id=checkpoint.correlation_id,
        required_reviewer=required,
        recommendation_available=recommendation_available,
        producer_ids=tuple(
            sorted({grant.principal_id, *(f.reviewer_id for f in request.reviewed_facts)}, key=str)
        ),
        evidence=tuple(
            EvidenceReference(
                evidence_id=p.evidence_id,
                document_id=p.artifact.document_id,
                artifact_sha256=p.artifact.sha256,
                processing_key=p.processing_key,
                record_sha256=p.record_sha256,
            )
            for p in sorted(rules.evidence_provenance, key=lambda p: p.evidence_id)
        ),
        state=ReviewState.SUPERVISOR if required == ReviewerRole.SUPERVISOR else ReviewState.REVIEW,
    )
    return VerifiedAdvisory(initial, snapshot, request.requested_at)


def effective_binding(entry: QueueEntry) -> ReviewBinding:
    for event in reversed(entry.events):
        if event.invalidation is not None:
            return event.invalidation.replacement
        if event.case_transition is not None:
            case = event.case_transition.current
            return ReviewBinding.model_validate(
                {
                    **entry.binding.model_dump(),
                    "case_revision": case.revision,
                    "case_sha256": digest(case.model_dump(mode="json")),
                }
            )
    return entry.binding


def assigned(entry: QueueEntry, actor: Principal) -> bool:
    return (
        actor.kind == PrincipalKind.HUMAN
        and actor.principal_id not in entry.producer_ids
        and any(
            a.assignee_id == actor.principal_id
            and a.role == actor.role
            and a.binding == entry.binding
            for a in entry.assignments
        )
    )


def decision_effect(
    source: VerifiedAdvisory, entry: QueueEntry, decision: ReviewDecision, actor: Principal
) -> tuple[ReviewState, CaseTransition | None]:
    if not assigned(entry, actor):
        raise ReviewError(ReviewCode.DENIED)
    if decision.expected != entry.binding or decision.entry_id != entry.entry_id:
        raise ReviewError(ReviewCode.STALE)
    if decision.expected_review_revision != entry.review_revision:
        raise ReviewError(ReviewCode.CONFLICT)
    if entry.state not in OPEN_STATES:
        raise ReviewError(ReviewCode.TRANSITION)
    if any(ref not in entry.evidence for ref in decision.evidence):
        raise ReviewError(ReviewCode.INVALID)
    if decision.action == ReviewAction.ESCALATE:
        if entry.state != ReviewState.REVIEW:
            raise ReviewError(ReviewCode.TRANSITION)
        return ReviewState.SUPERVISOR, None
    if (
        entry.required_reviewer == ReviewerRole.SUPERVISOR or entry.state == ReviewState.SUPERVISOR
    ) and actor.role != ReviewerRole.SUPERVISOR:
        raise ReviewError(ReviewCode.DENIED)
    if not entry.recommendation_available and decision.action != ReviewAction.REQUEST_EVIDENCE:
        raise ReviewError(ReviewCode.TRANSITION)
    if decision.action == ReviewAction.REQUEST_EVIDENCE:
        transition = transition_case(
            source.snapshot.case,
            TransitionRequest(
                target=CaseState.AWAITING_EVIDENCE,
                expected_revision=entry.binding.case_revision,
                actor=TransitionActor(principal_id=actor.principal_id, role=actor.role),
                audit_event_id=decision.action_id,
                occurred_at=decision.occurred_at,
                reason=decision.rationale,
            ),
        )
        return ReviewState.EVIDENCE, transition
    return (
        ReviewState.APPROVED if decision.action == ReviewAction.APPROVE else ReviewState.REJECTED,
        None,
    )


def replay_event(
    source: VerifiedAdvisory,
    entry: QueueEntry,
    event: ReviewEvent,
    principals: dict[UUID, Principal],
) -> QueueEntry:
    event = ReviewEvent.model_validate(event)
    previous = entry.events[-1] if entry.events else None
    if (
        event.entry_id != entry.entry_id
        or event.claim_id != entry.binding.claim_id
        or event.correlation_id != entry.correlation_id
        or event.sequence != entry.review_revision + 1
        or event.previous_sha256 != (previous.event_sha256 if previous else entry.entry_id)
        or event.before != (entry.state if previous else None)
        or event.occurred_at < (previous.occurred_at if previous else source.requested_at)
        or principals.get(event.actor.principal_id) != event.actor
    ):
        raise ReviewError(ReviewCode.AUDIT)
    assignments = entry.assignments
    expected_transition = None
    if event.kind == EventKind.QUEUED:
        if previous or event.actor.kind != PrincipalKind.HOST:
            raise ReviewError(ReviewCode.AUDIT)
        after = source.initial.state
    elif event.kind == EventKind.ASSIGNED:
        request = event.assignment
        assert request is not None
        actor = principals.get(request.assignee_id)
        if (
            event.actor.kind != PrincipalKind.HOST
            or entry.state not in OPEN_STATES
            or request.entry_id != entry.entry_id
            or request.claim_id != entry.binding.claim_id
            or request.expected_review_revision != entry.review_revision
            or actor is None
            or actor.kind != PrincipalKind.HUMAN
            or actor.role is None
            or actor.principal_id in entry.producer_ids
            or event.occurred_at != request.occurred_at
            or event.rationale != request.rationale
            or event.event_id != request.request_id
        ):
            raise ReviewError(ReviewCode.DENIED)
        assignment = ReviewAssignment(
            assignee_id=actor.principal_id,
            role=actor.role,
            binding=entry.binding,
            assigned_by=event.actor.principal_id,
            assigned_at=event.occurred_at,
        )
        assignments = tuple(
            sorted(
                (*[a for a in assignments if a.role != actor.role], assignment),
                key=lambda a: a.role.value,
            )
        )
        after = entry.state
    elif event.kind == EventKind.DECIDED:
        decision = event.decision
        assert decision is not None
        if (
            event.event_id != decision.action_id
            or event.occurred_at != decision.occurred_at
            or event.rationale != decision.rationale
        ):
            raise ReviewError(ReviewCode.AUDIT)
        after, expected_transition = decision_effect(source, entry, decision, event.actor)
    else:
        invalidation = event.invalidation
        assert invalidation is not None
        if (
            event.actor.kind != PrincipalKind.HOST
            or invalidation.entry_id != entry.entry_id
            or invalidation.expected_review_revision != entry.review_revision
            or entry.state == ReviewState.STALE
            or invalidation.replacement.claim_id != entry.binding.claim_id
            or invalidation.replacement == effective_binding(entry)
            or invalidation.replacement.case_revision < effective_binding(entry).case_revision
            or event.event_id != invalidation.request_id
            or event.occurred_at != invalidation.occurred_at
            or event.rationale != invalidation.rationale
        ):
            raise ReviewError(ReviewCode.INVALID)
        after = ReviewState.STALE
    if event.after != after or event.case_transition != expected_transition:
        raise ReviewError(ReviewCode.AUDIT)
    return QueueEntry.model_validate(
        {
            **entry.model_dump(),
            "state": after,
            "review_revision": event.sequence,
            "assignments": assignments,
            "events": (*entry.events, event),
        }
    )


def verify_history(
    source: VerifiedAdvisory, entry: QueueEntry, principals: dict[UUID, Principal]
) -> None:
    projected = source.initial
    event_ids: set[UUID] = set()
    for event in entry.events:
        if event.event_id in event_ids:
            raise ReviewError(ReviewCode.AUDIT)
        event_ids.add(event.event_id)
        projected = replay_event(source, projected, event, principals)
    if not entry.events or projected != entry:
        raise ReviewError(ReviewCode.AUDIT)


def bounded_size(value: QueueEntry | ReviewDecision | Snapshot, limit: int) -> None:
    if len(json_bytes(value.model_dump(mode="json"))) > limit:
        raise ReviewError(ReviewCode.CAPACITY)
