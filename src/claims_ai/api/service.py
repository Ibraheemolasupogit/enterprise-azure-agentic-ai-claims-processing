"""Thin, bounded application state; M12 owns processing and M15 owns review authority."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Protocol
from uuid import UUID, uuid5

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.api.auth import ApiAccess
from claims_ai.api.contracts import (
    AdvisoryResponse,
    ApiCode,
    ApiError,
    ApiLimits,
    ClaimStatus,
    IntakeRequest,
    ProcessingPhase,
    ProcessRequest,
    QueueItem,
    ReviewQueueResponse,
)
from claims_ai.human_review.contracts import (
    AssignmentRequest,
    PrincipalKind,
    ReviewCode,
    ReviewDecision,
    ReviewDetail,
    ReviewError,
    ReviewEvent,
    ReviewSession,
)
from claims_ai.human_review.service import ReviewQueue, utc_now
from claims_ai.models import Case, CaseState
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import Checkpoint, State, WorkflowLimits, WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner, authorized, execution_key, restore
from claims_ai.workflow.stages import Context


class WorkflowService(Protocol):
    async def run(self, request: WorkflowRequest, grant: ToolGrant) -> Checkpoint: ...


@dataclass(frozen=True)
class HostBundle:
    """Host-owned original fixture bytes/grant/assignments; never an HTTP request model."""

    bundle_id: str
    request: WorkflowRequest
    grant: ToolGrant
    reviewers: tuple[ReviewSession, ...]
    limits: WorkflowLimits = field(default_factory=WorkflowLimits)


@dataclass(frozen=True)
class CaseRecord:
    bundle: HostBundle
    current_case: Case
    revision: int = 1
    phase: ProcessingPhase = ProcessingPhase.INTAKEN
    checkpoint: Checkpoint | None = None
    review_entry_id: str | None = None
    last_review_sequence: int = 0


@dataclass(frozen=True)
class MutationReceipt:
    fingerprint: str
    response: ClaimStatus | None = None
    failed: bool = False


def review_error(error: ReviewError) -> ApiError:
    if error.code == ReviewCode.DENIED:
        return ApiError(404, ApiCode.MISSING)
    if error.code == ReviewCode.STALE:
        return ApiError(412, ApiCode.PRECONDITION)
    if error.code in {ReviewCode.CONFLICT, ReviewCode.TRANSITION}:
        return ApiError(409, ApiCode.CONFLICT)
    if error.code == ReviewCode.INVALID:
        return ApiError(422, ApiCode.INVALID)
    return ApiError(503, ApiCode.UNAVAILABLE)


class ClaimsApplication:
    def __init__(
        self,
        bundles: tuple[HostBundle, ...],
        queue: ReviewQueue,
        host: ReviewSession,
        *,
        runner: WorkflowService | None = None,
        limits: ApiLimits | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        self.limits = ApiLimits.model_validate(limits or ApiLimits())
        if len(bundles) > self.limits.max_cases or host.principal.kind != PrincipalKind.HOST:
            raise ValueError("invalid local application host configuration")
        self._bundles = {b.bundle_id: b for b in bundles}
        if len(self._bundles) != len(bundles) or len(
            {b.request.intake.claim.claim_id for b in bundles}
        ) != len(bundles):
            raise ValueError("host bundle/case identities must be unique")
        for bundle in bundles:
            IntakeRequest(bundle_id=bundle.bundle_id, claim=bundle.request.intake.claim)
            if (
                bundle.request.intake.state != CaseState.RECEIVED
                or bundle.request.intake.revision != 1
            ):
                raise ValueError("intake bundles must start at the M2 received revision")
            if len(bundle.reviewers) > 2 or len(
                {s.principal.role for s in bundle.reviewers}
            ) != len(bundle.reviewers):
                raise ValueError("host assigns at most one human per review role")
            if any(s.principal.kind != PrincipalKind.HUMAN for s in bundle.reviewers):
                raise ValueError("review plans contain synthetic humans only")
        self.queue, self.host = queue, host
        self.runner = runner or WorkflowRunner()
        self._clock = clock
        self.available = True
        self._records: dict[str, CaseRecord] = {}
        self._published_reviews: dict[str, str] = {}
        self._receipts: dict[tuple[UUID, str, UUID], MutationReceipt] = {}
        self._lock = asyncio.Lock()

    @property
    def ready(self) -> bool:
        return (
            self.available
            and bool(self._bundles)
            and all(authorized(bundle.request, bundle.grant) for bundle in self._bundles.values())
        )

    def _authorize(self, access: ApiAccess, claim_id: str, operation: str = "read") -> None:
        scope = access.scope
        if scope.principal.kind not in {PrincipalKind.HOST, PrincipalKind.HUMAN}:
            raise ApiError(403, ApiCode.DENIED)
        if claim_id not in scope.claim_ids:
            raise ApiError(404, ApiCode.MISSING)
        if (
            operation == "intake"
            and not scope.can_intake
            or operation == "process"
            and not scope.can_process
        ):
            raise ApiError(403, ApiCode.DENIED)

    def _record(self, access: ApiAccess, claim_id: str) -> CaseRecord:
        self._authorize(access, claim_id)
        record = self._records.get(claim_id)
        if record is None:
            raise ApiError(404, ApiCode.MISSING)
        return record

    def _status(self, record: CaseRecord) -> ClaimStatus:
        case = record.current_case
        return ClaimStatus(
            claim_id=case.claim.claim_id,
            case_revision=case.revision,
            case_sha256=digest(case.model_dump(mode="json")),
            case_state=case.state,
            application_revision=record.revision,
            processing_phase=record.phase,
            workflow_state=record.checkpoint.state if record.checkpoint else None,
            workflow_correlation_id=record.bundle.grant.correlation_id,
            review_entry_id=record.review_entry_id,
        )

    def _receipt(self, key: tuple[UUID, str, UUID], fingerprint: str) -> ClaimStatus | None:
        receipt = self._receipts.get(key)
        if receipt is None:
            return None
        if receipt.fingerprint != fingerprint:
            raise ApiError(409, ApiCode.CONFLICT)
        if receipt.failed:
            raise ApiError(503, ApiCode.UNAVAILABLE)
        return receipt.response

    def _capacity(self) -> None:
        if len(self._receipts) >= self.limits.max_receipts:
            raise ApiError(503, ApiCode.UNAVAILABLE)

    async def intake(self, access: ApiAccess, request: IntakeRequest, key: UUID) -> ClaimStatus:
        self._authorize(access, request.claim.claim_id, "intake")
        bundle = self._bundles.get(request.bundle_id)
        if bundle is None:
            raise ApiError(404, ApiCode.MISSING)
        if request.claim != bundle.request.intake.claim:
            raise ApiError(422, ApiCode.INVALID)
        async with self._lock:
            receipt_key = (access.scope.principal.principal_id, "intake", key)
            fingerprint = digest(request.model_dump(mode="json"))
            repeated = self._receipt(receipt_key, fingerprint)
            if repeated is not None:
                return repeated
            if request.claim.claim_id in self._records:
                raise ApiError(409, ApiCode.CONFLICT)
            if len(self._records) >= self.limits.max_cases:
                raise ApiError(503, ApiCode.UNAVAILABLE)
            self._capacity()
            record = CaseRecord(bundle, bundle.request.intake)
            response = self._status(record)
            self._records[request.claim.claim_id] = record
            self._receipts[receipt_key] = MutationReceipt(fingerprint, response)
            return response

    async def process(
        self,
        access: ApiAccess,
        claim_id: str,
        request: ProcessRequest,
        key: UUID,
        revision: int,
    ) -> ClaimStatus:
        self._authorize(access, claim_id, "process")
        async with self._lock:
            record = self._record(access, claim_id)
            receipt_key = (access.scope.principal.principal_id, "process/" + claim_id, key)
            fingerprint = digest({"request": request.model_dump(mode="json"), "revision": revision})
            repeated = self._receipt(receipt_key, fingerprint)
            if repeated is not None:
                return repeated
            if (
                revision != record.revision
                or request.expected_case_revision != record.current_case.revision
                or request.expected_case_sha256
                != digest(record.current_case.model_dump(mode="json"))
            ):
                raise ApiError(412, ApiCode.PRECONDITION)
            if record.phase != ProcessingPhase.INTAKEN:
                raise ApiError(409, ApiCode.CONFLICT)
            if not self.available:
                raise ApiError(503, ApiCode.UNAVAILABLE)
            bundle = record.bundle
            if not authorized(bundle.request, bundle.grant):
                raise ApiError(403, ApiCode.DENIED)
            self._capacity()
            processing = replace(
                record, revision=record.revision + 1, phase=ProcessingPhase.PROCESSING
            )
            self._records[claim_id] = processing
            # Reserve a failure tombstone before any workflow call; cancellation never resets it.
            self._receipts[receipt_key] = MutationReceipt(fingerprint, failed=True)
            try:
                checkpoint = await self.runner.run(bundle.request, bundle.grant)
                context = Context(
                    bundle.request,
                    bundle.grant,
                    execution_key(bundle.request, bundle.grant, bundle.limits),
                    bundle.limits,
                )
                checkpoint = await restore(bundle.request, context, checkpoint)
                entry_id = None
                sequence = 0
                try:
                    entry = await self.queue.enqueue(
                        self.host,
                        bundle.request,
                        bundle.grant,
                        checkpoint,
                        occurred_at=self._clock(),
                        workflow_limits=bundle.limits,
                    )
                except ReviewError as error:
                    if error.code != ReviewCode.INVALID:
                        raise
                else:
                    for reviewer in bundle.reviewers:
                        self.queue.assign(
                            self.host,
                            AssignmentRequest(
                                request_id=uuid5(
                                    UUID(hex=entry.entry_id[:32]),
                                    str(reviewer.principal.principal_id),
                                ),
                                entry_id=entry.entry_id,
                                claim_id=claim_id,
                                expected_review_revision=entry.review_revision,
                                assignee_id=reviewer.principal.principal_id,
                                occurred_at=self._clock(),
                                rationale="Host-configured synthetic API case assignment.",
                            ),
                        )
                        entry = self.queue.details.get(reviewer, entry.entry_id).entry
                    entry_id, sequence = entry.entry_id, entry.review_revision
                completed = replace(
                    processing,
                    current_case=checkpoint.snapshot.case,
                    checkpoint=checkpoint,
                    review_entry_id=entry_id,
                    last_review_sequence=sequence,
                    phase=ProcessingPhase.PROCESSED
                    if checkpoint.state in {State.REVIEW, State.SUPERVISOR}
                    else ProcessingPhase.ATTENTION,
                )
                response = self._status(completed)
            except BaseException as error:
                self._records[claim_id] = replace(processing, phase=ProcessingPhase.FAILED)
                if not isinstance(error, Exception):
                    raise
                raise ApiError(503, ApiCode.UNAVAILABLE) from None
            self._records[claim_id] = completed
            if entry_id is not None:
                self._published_reviews[entry_id] = claim_id
            self._receipts[receipt_key] = MutationReceipt(fingerprint, response)
            return response

    def status(self, access: ApiAccess, claim_id: str) -> ClaimStatus:
        return self._status(self._record(access, claim_id))

    def _session(self, access: ApiAccess) -> ReviewSession:
        if access.review_session is None or access.scope.principal.kind != PrincipalKind.HUMAN:
            raise ApiError(403, ApiCode.DENIED)
        return access.review_session

    def review_detail(self, access: ApiAccess, entry_id: str) -> ReviewDetail:
        session = self._session(access)
        claim_id = self._published_reviews.get(entry_id)
        if claim_id is None:
            raise ApiError(404, ApiCode.MISSING)
        self._authorize(access, claim_id)
        try:
            return self.queue.details.get(session, entry_id)
        except ReviewError as error:
            raise review_error(error) from None

    def review_list(self, access: ApiAccess, offset: int, limit: int) -> ReviewQueueResponse:
        session = self._session(access)
        try:
            entries = [
                entry
                for entry in self.queue.details.list(session)
                if entry.entry_id in self._published_reviews
                and entry.binding.claim_id in access.scope.claim_ids
            ]
        except ReviewError as error:
            raise review_error(error) from None
        return ReviewQueueResponse(
            items=tuple(QueueItem.from_entry(e) for e in entries[offset : offset + limit]),
            next_offset=offset + limit if len(entries) > offset + limit else None,
        )

    def advisory(self, access: ApiAccess, claim_id: str) -> AdvisoryResponse:
        record = self._record(access, claim_id)
        if record.checkpoint is None:
            raise ApiError(409, ApiCode.CONFLICT)
        binding = None
        if access.scope.principal.kind == PrincipalKind.HUMAN:
            if record.review_entry_id is None:
                raise ApiError(404, ApiCode.MISSING)
            binding = self.review_detail(access, record.review_entry_id).entry.binding
        elif record.review_entry_id is not None:
            # Hosts see processing advisory data, never acquire a human session or review action.
            binding = None
        snapshot = record.checkpoint.snapshot
        draft = snapshot.agent_result.draft if snapshot.agent_result else None
        return AdvisoryResponse(
            claim_id=claim_id,
            task=snapshot.review_task,
            draft=draft,
            rules=snapshot.rule_evaluation,
            review_binding=binding,
            recommendation_available=draft is not None,
        )

    async def review_action(
        self,
        access: ApiAccess,
        entry_id: str,
        decision: ReviewDecision,
        key: UUID,
        revision: int,
    ) -> ReviewEvent:
        async with self._lock:
            self.review_detail(access, entry_id)
            if decision.entry_id != entry_id or key != decision.action_id:
                raise ApiError(409, ApiCode.CONFLICT)
            if revision != decision.expected_review_revision:
                raise ApiError(412, ApiCode.PRECONDITION)
            try:
                event = self.queue.decide(self._session(access), decision)
            except ReviewError as error:
                if error.code == ReviewCode.DENIED:
                    raise ApiError(403, ApiCode.DENIED) from None
                raise review_error(error) from None
            claim_id = self._published_reviews[entry_id]
            record = self._records[claim_id]
            if event.sequence > record.last_review_sequence:
                self._records[claim_id] = replace(
                    record,
                    revision=record.revision + 1,
                    last_review_sequence=event.sequence,
                    current_case=event.case_transition.current
                    if event.case_transition
                    else record.current_case,
                )
            return event
