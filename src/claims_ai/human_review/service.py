"""Bounded single-process storage with atomic review CAS and host-owned identity bindings."""

import threading
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid5

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.human_review.contracts import (
    AssignmentRequest,
    EventKind,
    InvalidationRequest,
    Principal,
    PrincipalKind,
    QueueEntry,
    ReviewBinding,
    ReviewCode,
    ReviewDecision,
    ReviewDetail,
    ReviewError,
    ReviewEvent,
    ReviewLimits,
    ReviewSession,
    ReviewState,
)
from claims_ai.human_review.validation import (
    VerifiedAdvisory,
    assigned,
    bounded_size,
    decision_effect,
    effective_binding,
    replay_event,
    verify_advisory,
    verify_history,
)
from claims_ai.lifecycle import CaseTransition
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import Checkpoint, WorkflowLimits, WorkflowRequest


def utc_now() -> datetime:
    return datetime.now(UTC)


class ReviewQueue:
    """Trusted host owns sessions, ingestion, assignment and invalidation.

    Sessions are opaque objects registered at construction. Nothing here authenticates a real
    person; the host must deliver a human session only to its synthetic human caller. No MCP,
    agent, model, API or UI operation exposes these capabilities. Private memory/OS host is trusted.
    """

    def __init__(
        self,
        sessions: tuple[ReviewSession, ...],
        *,
        limits: ReviewLimits | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if len(sessions) > 64:
            raise ReviewError(ReviewCode.CAPACITY)
        self._principals: dict[UUID, Principal] = {}
        self._sessions: dict[UUID, ReviewSession] = {}
        for session in sessions:
            principal = Principal.model_validate(session.principal)
            if principal.principal_id in self._principals:
                raise ReviewError(ReviewCode.INVALID)
            self._principals[principal.principal_id] = principal
            self._sessions[principal.principal_id] = session
        self.limits = ReviewLimits.model_validate(limits or ReviewLimits())
        self._clock = clock
        self._lock = threading.RLock()
        self._entries: dict[str, QueueEntry] = {}
        self._sources: dict[str, VerifiedAdvisory] = {}
        self._current: dict[str, ReviewBinding] = {}
        self._heads: dict[str, tuple[int, str]] = {}
        self.details = ReviewDetails(self)

    def _actor(self, session: ReviewSession, *, host: bool = False) -> Principal:
        if not isinstance(session, ReviewSession):
            raise ReviewError(ReviewCode.DENIED)
        actor = self._principals.get(session.principal.principal_id)
        if (
            actor is None
            or self._sessions.get(actor.principal_id) is not session
            or actor != session.principal
            or actor.kind != (PrincipalKind.HOST if host else PrincipalKind.HUMAN)
        ):
            raise ReviewError(ReviewCode.DENIED)
        return actor

    def _time(self, occurred_at: datetime) -> None:
        now = self._clock()
        if now.utcoffset() is None or occurred_at.utcoffset() is None or occurred_at > now:
            raise ReviewError(ReviewCode.INVALID)

    def _entry(self, entry_id: str) -> QueueEntry:
        entry = self._entries.get(entry_id)
        if entry is None:
            raise ReviewError(ReviewCode.DENIED)
        try:
            verify_history(self._sources[entry_id], entry, self._principals)
            if self._heads.get(entry_id) != (entry.review_revision, entry.events[-1].event_sha256):
                raise ReviewError(ReviewCode.AUDIT)
        except (ValueError, KeyError, AssertionError) as error:
            raise ReviewError(ReviewCode.AUDIT) from error
        return entry

    def _fresh(self, entry: QueueEntry) -> None:
        if entry.state == ReviewState.STALE or self._current.get(
            entry.binding.claim_id
        ) != effective_binding(entry):
            raise ReviewError(ReviewCode.STALE)

    def _duplicate(
        self,
        event_id: UUID,
        actor: Principal,
        request: AssignmentRequest | ReviewDecision | InvalidationRequest,
    ) -> ReviewEvent | None:
        for entry in self._entries.values():
            for event in entry.events:
                if event.event_id == event_id:
                    original = event.assignment or event.decision or event.invalidation
                    if event.actor == actor and original == request:
                        return event
                    raise ReviewError(ReviewCode.CONFLICT)
        return None

    def _event(
        self,
        entry: QueueEntry,
        actor: Principal,
        event_id: UUID,
        occurred_at: datetime,
        rationale: str,
        kind: EventKind,
        after: ReviewState,
        *,
        assignment: AssignmentRequest | None = None,
        decision: ReviewDecision | None = None,
        invalidation: InvalidationRequest | None = None,
        transition: CaseTransition | None = None,
    ) -> ReviewEvent:
        self._time(occurred_at)
        draft = ReviewEvent.model_construct(
            event_id=event_id,
            entry_id=entry.entry_id,
            claim_id=entry.binding.claim_id,
            correlation_id=entry.correlation_id,
            sequence=entry.review_revision + 1,
            kind=kind,
            actor=actor,
            occurred_at=occurred_at,
            rationale=rationale,
            before=entry.state if entry.events else None,
            after=after,
            assignment=assignment,
            decision=decision,
            invalidation=invalidation,
            case_transition=transition,
            previous_sha256=entry.events[-1].event_sha256 if entry.events else entry.entry_id,
            event_sha256="0" * 64,
        )
        return ReviewEvent.model_validate(
            {
                **draft.model_dump(mode="json"),
                "event_sha256": digest(draft.model_dump(mode="json", exclude={"event_sha256"})),
            }
        )

    def _commit(
        self, source: VerifiedAdvisory, entry: QueueEntry, event: ReviewEvent
    ) -> QueueEntry:
        if len(entry.events) >= self.limits.max_events_per_entry:
            raise ReviewError(ReviewCode.CAPACITY)
        updated = replay_event(source, entry, event, self._principals)
        bounded_size(updated, self.limits.max_entry_bytes)
        self._entries[entry.entry_id] = updated
        self._current[entry.binding.claim_id] = effective_binding(updated)
        self._heads[entry.entry_id] = (updated.review_revision, event.event_sha256)
        return updated

    async def enqueue(
        self,
        host: ReviewSession,
        request: WorkflowRequest,
        grant: ToolGrant,
        checkpoint: Checkpoint,
        *,
        occurred_at: datetime,
        workflow_limits: WorkflowLimits | None = None,
    ) -> QueueEntry:
        actor = self._actor(host, host=True)
        try:
            source = await verify_advisory(
                request, grant, checkpoint, workflow_limits or WorkflowLimits()
            )
            bounded_size(source.snapshot, self.limits.max_entry_bytes)
        except ReviewError:
            raise
        except (ValueError, OSError, StopIteration) as error:
            raise ReviewError(ReviewCode.INVALID) from error
        with self._lock:
            initial = source.initial
            self._time(occurred_at)
            known = self._entries.get(initial.entry_id)
            if known is not None:
                self._fresh(self._entry(initial.entry_id))
                return known
            if len(self._entries) >= self.limits.max_entries:
                raise ReviewError(ReviewCode.CAPACITY)
            current = self._current.get(initial.binding.claim_id)
            if current is not None and current != initial.binding:
                raise ReviewError(ReviewCode.STALE)
            event = self._event(
                initial,
                actor,
                uuid5(UUID(hex=initial.entry_id[:32]), "queued"),
                occurred_at,
                "Verified M12 advisory admitted for recommendation review only.",
                EventKind.QUEUED,
                initial.state,
            )
            updated = self._commit(source, initial, event)
            self._sources[initial.entry_id] = source
            return updated

    def assign(self, host: ReviewSession, request: AssignmentRequest) -> ReviewEvent:
        with self._lock:
            actor = self._actor(host, host=True)
            request = AssignmentRequest.model_validate(request)
            entry = self._entry(request.entry_id)
            self._fresh(entry)
            duplicate = self._duplicate(request.request_id, actor, request)
            if duplicate is not None:
                return duplicate
            if request.claim_id != entry.binding.claim_id:
                raise ReviewError(ReviewCode.DENIED)
            if request.expected_review_revision != entry.review_revision:
                raise ReviewError(ReviewCode.CONFLICT)
            event = self._event(
                entry,
                actor,
                request.request_id,
                request.occurred_at,
                request.rationale,
                EventKind.ASSIGNED,
                entry.state,
                assignment=request,
            )
            self._commit(self._sources[entry.entry_id], entry, event)
            return event

    def decide(self, session: ReviewSession, decision: ReviewDecision) -> ReviewEvent:
        with self._lock:
            actor = self._actor(session)
            decision = ReviewDecision.model_validate(decision)
            bounded_size(decision, self.limits.max_action_bytes)
            entry = self._entry(decision.entry_id)
            if not assigned(entry, actor):
                raise ReviewError(ReviewCode.DENIED)
            self._fresh(entry)
            if decision.expected != entry.binding:
                raise ReviewError(ReviewCode.STALE)
            duplicate = self._duplicate(decision.action_id, actor, decision)
            if duplicate is not None:
                return duplicate
            state, transition = decision_effect(
                self._sources[entry.entry_id], entry, decision, actor
            )
            event = self._event(
                entry,
                actor,
                decision.action_id,
                decision.occurred_at,
                decision.rationale,
                EventKind.DECIDED,
                state,
                decision=decision,
                transition=transition,
            )
            self._commit(self._sources[entry.entry_id], entry, event)
            return event

    def invalidate(self, host: ReviewSession, request: InvalidationRequest) -> ReviewEvent:
        """Trusted host notification of changed inputs; replacement metadata is not reprocessing."""
        with self._lock:
            actor = self._actor(host, host=True)
            request = InvalidationRequest.model_validate(request)
            entry = self._entry(request.entry_id)
            duplicate = self._duplicate(request.request_id, actor, request)
            if duplicate is not None:
                return duplicate
            self._fresh(entry)
            event = self._event(
                entry,
                actor,
                request.request_id,
                request.occurred_at,
                request.rationale,
                EventKind.INVALIDATED,
                ReviewState.STALE,
                invalidation=request,
            )
            self._commit(self._sources[entry.entry_id], entry, event)
            return event


class ReviewDetails:
    """Read-only assigned-case view; deliberately has no action/assignment methods."""

    def __init__(self, queue: ReviewQueue) -> None:
        self._queue = queue

    def list(self, session: ReviewSession) -> tuple[QueueEntry, ...]:
        queue = self._queue
        with queue._lock:
            actor = queue._actor(session)
            return tuple(
                queue._entry(key)
                for key, entry in sorted(queue._entries.items())
                if assigned(entry, actor)
            )

    def get(self, session: ReviewSession, entry_id: str) -> ReviewDetail:
        queue = self._queue
        with queue._lock:
            actor = queue._actor(session)
            entry = queue._entry(entry_id)
            if not assigned(entry, actor):
                raise ReviewError(ReviewCode.DENIED)
            source = queue._sources[entry_id]
            transitions = [e.case_transition for e in entry.events if e.case_transition is not None]
            return ReviewDetail(
                entry=entry,
                advisory_snapshot=source.snapshot,
                current_case=transitions[-1].current if transitions else source.snapshot.case,
            )
