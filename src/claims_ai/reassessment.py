"""M25 P2: pure dependency impact, lifecycle routing and request reconciliation.

Plans only. Nothing here admits evidence, transitions a case, invalidates a review,
authorizes reuse of prior conclusions or executes an M20 command. Every derived item
remains invalidated: dependency labels order and focus later reassessment work, they
never narrow M20's correction semantics, which clear all derived material.
"""

from collections.abc import Sequence
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from claims_ai.amendments import (
    AmendmentError,
    AmendmentPlan,
    AmendmentRequest,
    Invalidation,
    ReasonCode,
    Requirement,
    _canonical,
    _checked_case,
    _hash,
    plan_amendment,
)
from claims_ai.models import Case, CaseState, Contract, DocumentKind, Sha256

MAX_REQUESTS = 16
POLICY_KINDS = frozenset(
    {DocumentKind.POLICY_SCHEDULE, DocumentKind.POLICY_WORDING, DocumentKind.ENDORSEMENT}
)
ItemId = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=128)]


class Dependency(StrEnum):
    DIRECT = "traced_to_changed_document"
    UNTRACEABLE = "dependency_not_reliably_traceable"
    NOT_TRACED = "no_traced_dependency_on_changed_document"


class Basis(StrEnum):
    """Fixed-order reasons. Supplied traces are unverified, so none permits reuse."""

    TRACED_EVIDENCE = "references_evidence_from_changed_document"
    POLICY_DOCUMENT = "changed_document_is_policy_material"
    ADDED_DOCUMENT = "added_document_may_supply_untraced_facts"
    EMPTY_TRACE = "rule_trace_cites_no_evidence"
    DUPLICATE_TRACE = "rule_identifier_traced_more_than_once"
    HOLISTIC = "holistic_advisory_outcome_rationale_and_flags"
    BOUND_ADVISORY = "bound_to_stale_advisory_assessment"
    WHOLE_CASE = "bound_to_whole_case_hash"
    M20_CLEARS = "m20_correction_clears_all_derived_material"


class ImpactItem(Contract):
    category: Invalidation
    item_id: ItemId
    dependency: Dependency
    bases: Annotated[tuple[Basis, ...], Field(min_length=1)]
    invalidated: Literal[True] = True
    reuse_authorized: Literal[False] = False

    @model_validator(mode="after")
    def conservative(self) -> Self:
        order = tuple(Basis)
        if list(self.bases) != sorted(set(self.bases), key=order.index):
            raise ValueError("bases must be unique and in fixed order")
        if Basis.M20_CLEARS not in self.bases:
            raise ValueError("every item must record the M20 invalidation basis")
        traced = {Basis.TRACED_EVIDENCE, Basis.POLICY_DOCUMENT} & set(self.bases)
        if (self.dependency == Dependency.DIRECT) != bool(traced):
            raise ValueError("direct dependency requires a traced basis")
        if self.dependency == Dependency.NOT_TRACED and set(self.bases) != {Basis.M20_CLEARS}:
            raise ValueError("untraceable bases cannot be labelled not traced")
        return self


class RouteStatus(StrEnum):
    SUPPORTED = "m20_correction_route_in_lifecycle_table"
    BLOCKED = "no_supported_m20_correction_route"


class LifecycleCode(StrEnum):
    DIRECT = "correct_directly_to_validating"
    VIA_AWAITING_EVIDENCE = "assessing_corrects_via_awaiting_evidence"
    QUARANTINE_RELEASE = "quarantine_release_correction_requires_supervisor"
    PROCESSING_FAILED = "processing_failed_requires_full_revalidation"
    REOPEN = "closed_requires_m20_supervisor_reopening"
    REOPENED_UNSUPPORTED = "reopened_validating_case_has_no_m20_correction_route"
    IN_FLIGHT = "in_flight_processing_state_has_no_m20_correction_route"


class LifecycleRoute(Contract):
    """Mirrors lifecycle.ALLOWED_TRANSITIONS and the M20 CORRECT branch; executes nothing."""

    source_state: CaseState
    status: RouteStatus
    codes: Annotated[tuple[LifecycleCode, ...], Field(min_length=1)]
    transitions: tuple[CaseState, ...]
    lifecycle_supervisor_required: bool

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if (self.status == RouteStatus.SUPPORTED) != bool(self.transitions):
            raise ValueError("only supported routes list transitions")
        if self.transitions and self.transitions[-1] != CaseState.VALIDATING:
            raise ValueError("M20 correction routes end at validating")
        return self


_D, _S, _B = LifecycleCode, RouteStatus.SUPPORTED, RouteStatus.BLOCKED
_ROUTES: dict[
    CaseState, tuple[RouteStatus, tuple[LifecycleCode, ...], tuple[CaseState, ...], bool]
] = {
    CaseState.RECEIVED: (_S, (_D.DIRECT,), (CaseState.VALIDATING,), False),
    CaseState.VALIDATING: (_B, (_D.IN_FLIGHT,), (), False),
    CaseState.EXTRACTING: (_B, (_D.IN_FLIGHT,), (), False),
    CaseState.ASSESSING: (
        _S,
        (_D.VIA_AWAITING_EVIDENCE,),
        (CaseState.AWAITING_EVIDENCE, CaseState.VALIDATING),
        False,
    ),
    CaseState.AWAITING_REVIEW: (_S, (_D.DIRECT,), (CaseState.VALIDATING,), False),
    CaseState.AWAITING_EVIDENCE: (_S, (_D.DIRECT,), (CaseState.VALIDATING,), False),
    CaseState.QUARANTINED: (_S, (_D.QUARANTINE_RELEASE,), (CaseState.VALIDATING,), True),
    CaseState.PROCESSING_FAILED: (_S, (_D.PROCESSING_FAILED,), (CaseState.VALIDATING,), False),
    CaseState.CLOSED: (_B, (_D.REOPEN, _D.REOPENED_UNSUPPORTED), (), True),
}


def lifecycle_route(state: CaseState) -> LifecycleRoute:
    status, codes, transitions, supervisor = _ROUTES[CaseState(state)]
    return LifecycleRoute(
        source_state=state,
        status=status,
        codes=codes,
        transitions=transitions,
        lifecycle_supervisor_required=supervisor,
    )


class Step(StrEnum):
    """Fixed reassessment order; a plan lists the applicable subset in this order."""

    SOURCE = "recheck_exact_source_binding"
    IDENTITY = "recheck_m21_identity_revocation_scope_and_assignment"
    REOPEN = "obtain_m20_supervisor_reopening"
    ROUTE_BLOCKED = "resolve_unsupported_m20_correction_route_before_execution"
    SUPERVISOR = "require_supervisor_actor_for_quarantine_release_correction"
    REVIEW_INVALIDATION = "invalidate_stale_m15_review_bindings_and_assignments"
    CORRECTION = "submit_m20_correction_with_cleared_replacement"
    BYTES = "verify_actual_bytes_hash_size_and_ownership"
    SCAN = "obtain_host_scan_clearance"
    EVIDENCE = "rerun_m6_provenance_validation_extraction_and_admission"
    POLICY = "reselect_and_verify_exact_policy"
    RULES = "rerun_provisional_rules"
    ADVISORY = "rerun_advisory"
    REVIEW = "obtain_fresh_canonical_human_review"
    APPROVAL = "obtain_independent_m20_revalidation_approval"


_STEP_REQUIREMENT: dict[Step, Requirement] = {
    Step.REOPEN: Requirement.REOPEN,
    Step.CORRECTION: Requirement.CORRECTION,
    Step.BYTES: Requirement.BYTES,
    Step.SCAN: Requirement.SCAN,
    Step.EVIDENCE: Requirement.EVIDENCE,
    Step.POLICY: Requirement.POLICY,
    Step.RULES: Requirement.REASSESS,
    Step.ADVISORY: Requirement.REASSESS,
    Step.REVIEW: Requirement.REVIEW,
}


class PlanStep(Contract):
    position: Annotated[int, Field(strict=True, ge=1)]
    step: Step
    requirement: Requirement | None
    # Directly affected items to examine first. Focus never narrows the step's scope.
    focus: tuple[ItemId, ...]


class ReassessmentPlan(Contract):
    format: Literal["m25-reassessment-plan-v1"] = "m25-reassessment-plan-v1"
    purpose: Literal["synthetic_dependency_planning_only"] = "synthetic_dependency_planning_only"
    amendment: AmendmentPlan
    amendment_sha256: Sha256
    lifecycle: LifecycleRoute
    impact: tuple[ImpactItem, ...]
    steps: tuple[PlanStep, ...]
    execution_authorized: Literal[False] = False
    reuse_authorized: Literal[False] = False
    automatic_transition: Literal[False] = False
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        if _hash(self.amendment.model_dump(mode="json")) != self.amendment_sha256:
            raise ValueError("amendment hash mismatch")
        changed = bool(self.amendment.invalidations)
        if not changed and (self.impact or self.steps):
            raise ValueError("unchanged inventory has no impact or steps")
        if changed and not self.steps:
            raise ValueError("changed inventory requires reassessment steps")
        if [s.position for s in self.steps] != list(range(1, len(self.steps) + 1)):
            raise ValueError("step positions must be contiguous")
        order = tuple(Step)
        names = [s.step for s in self.steps]
        if names != sorted(set(names), key=order.index):
            raise ValueError("steps must be unique and in fixed order")
        if any(s.requirement != _STEP_REQUIREMENT.get(s.step) for s in self.steps):
            raise ValueError("step requirement mapping mismatch")
        if not set(self.amendment.requirements) <= {s.requirement for s in self.steps}:
            raise ValueError("every P1 requirement needs a reassessment step")
        keys = [(tuple(Invalidation).index(i.category), i.item_id) for i in self.impact]
        if keys != sorted(set(keys)):
            raise ValueError("impact items must be unique and sorted")
        if changed and {i.category for i in self.impact} - set(self.amendment.invalidations):
            raise ValueError("impact category outside P1 invalidations")
        state = self.lifecycle.source_state
        if self.lifecycle != lifecycle_route(state):
            raise ValueError("lifecycle route must match the canonical route table")
        if changed and (
            (self.lifecycle.status == RouteStatus.BLOCKED) != (Step.ROUTE_BLOCKED in names)
            or (state == CaseState.CLOSED) != (Step.REOPEN in names)
            or (state == CaseState.CLOSED) != (ReasonCode.CLOSED in self.amendment.reasons)
            or (state == CaseState.QUARANTINED) != (Step.SUPERVISOR in names)
        ):
            raise ValueError("lifecycle preconditions must be explicit and state-consistent")
        return self


def _item(category: Invalidation, item_id: str, bases: set[Basis]) -> ImpactItem:
    bases = bases | {Basis.M20_CLEARS}
    if bases & {Basis.TRACED_EVIDENCE, Basis.POLICY_DOCUMENT}:
        dependency = Dependency.DIRECT
    elif bases != {Basis.M20_CLEARS}:
        dependency = Dependency.UNTRACEABLE
    else:
        dependency = Dependency.NOT_TRACED
    return ImpactItem(
        category=category,
        item_id=item_id,
        dependency=dependency,
        bases=tuple(b for b in Basis if b in bases),
    )


def _impact(case: Case, request: AmendmentRequest, plan: AmendmentPlan) -> list[ImpactItem]:
    changed = {r.document_id for r in plan.removed} | {
        r.previous.document_id for r in plan.replaced
    }
    added = {r.document_id for r in plan.added}
    previous = {d.document_id: d for d in case.documents}
    proposed = {d.document_id: d for d in request.proposed_documents}
    policy_ids = {a.document_id for a in case.policy.artifacts} if case.policy else set()
    policy_touched = any(
        key in policy_ids
        or (key in previous and previous[key].kind in POLICY_KINDS)
        or (key in proposed and proposed[key].kind in POLICY_KINDS)
        for key in changed | added
    )
    direct = {e.evidence_id for e in case.evidence if e.document_id in changed}
    context: set[Basis] = set()
    if added:
        context.add(Basis.ADDED_DOCUMENT)
    if policy_touched:
        context.add(Basis.POLICY_DOCUMENT)

    def traced(ids: Sequence[str]) -> set[Basis]:
        return {Basis.TRACED_EVIDENCE} if direct.intersection(ids) else set()

    items = [
        _item(Invalidation.EVIDENCE, e.evidence_id, traced((e.evidence_id,))) for e in case.evidence
    ]
    if case.decision is not None:
        items.append(
            _item(
                Invalidation.FACTS,
                case.decision.assessment_id,
                traced(case.decision.evidence_ids) | {Basis.BOUND_ADVISORY},
            )
        )
    if case.policy is not None:
        items.append(
            _item(Invalidation.POLICY, case.policy.policy_id, context & {Basis.POLICY_DOCUMENT})
        )
    assessment = case.assessment
    if assessment is not None:
        groups: dict[str, list[tuple[str, ...]]] = {}
        for result in assessment.rule_results:
            groups.setdefault(result.rule_id, []).append(result.evidence_ids)
        for rule_id, traces in groups.items():
            bases = context | traced([i for t in traces for i in t])
            if len(traces) > 1:
                bases.add(Basis.DUPLICATE_TRACE)
            if any(not t for t in traces):
                bases.add(Basis.EMPTY_TRACE)
            items.append(_item(Invalidation.RULES, rule_id, bases))
        items.append(
            _item(
                Invalidation.ADVICE,
                assessment.assessment_id,
                context | traced(assessment.evidence_ids) | {Basis.HOLISTIC},
            )
        )
    for category in (Invalidation.REVIEW, Invalidation.ASSIGNMENTS):
        items.append(_item(category, case.claim.claim_id, {Basis.WHOLE_CASE}))
    order = tuple(Invalidation)
    return sorted(items, key=lambda i: (order.index(i.category), i.item_id))


def _steps(
    case: Case, plan: AmendmentPlan, route: LifecycleRoute, impact: list[ImpactItem]
) -> tuple[PlanStep, ...]:
    if not plan.invalidations:
        return ()

    def focus(category: Invalidation) -> tuple[str, ...]:
        return tuple(
            i.item_id
            for i in impact
            if i.category == category and i.dependency == Dependency.DIRECT
        )

    changed_docs = tuple(
        sorted(
            {r.document_id for r in plan.added} | {r.proposed.document_id for r in plan.replaced}
        )
    )
    selected: list[tuple[Step, tuple[str, ...]]] = [(Step.SOURCE, ()), (Step.IDENTITY, ())]
    if case.state == CaseState.CLOSED:
        selected.append((Step.REOPEN, ()))
    if route.status == RouteStatus.BLOCKED:
        selected.append((Step.ROUTE_BLOCKED, ()))
    if case.state == CaseState.QUARANTINED:
        selected.append((Step.SUPERVISOR, ()))
    selected += [(Step.REVIEW_INVALIDATION, ()), (Step.CORRECTION, ())]
    if plan.verification_documents:
        selected += [(s, changed_docs) for s in (Step.BYTES, Step.SCAN, Step.EVIDENCE)]
    selected += [
        (Step.POLICY, focus(Invalidation.POLICY)),
        (Step.RULES, focus(Invalidation.RULES)),
        (Step.ADVISORY, focus(Invalidation.ADVICE)),
        (Step.REVIEW, focus(Invalidation.FACTS)),
        (Step.APPROVAL, ()),
    ]
    return tuple(
        PlanStep(position=n, step=s, requirement=_STEP_REQUIREMENT.get(s), focus=f)
        for n, (s, f) in enumerate(selected, start=1)
    )


def plan_reassessment(case: Case, request: AmendmentRequest) -> ReassessmentPlan:
    """Recompute P1 against the supplied source; never trust a serialized plan."""
    case = _checked_case(case)
    request = AmendmentRequest.model_validate(request)
    amendment = plan_amendment(case, request)
    route = lifecycle_route(case.state)
    impact = _impact(case, request, amendment) if amendment.invalidations else []
    return ReassessmentPlan(
        amendment=amendment,
        amendment_sha256=_hash(amendment.model_dump(mode="json")),
        lifecycle=route,
        impact=tuple(impact),
        steps=_steps(case, amendment, route, impact),
    )


def canonical_reassessment(plan: ReassessmentPlan) -> bytes:
    """Deterministic serialization, not a signature or a trusted execution receipt."""
    # Same canonical JSON convention as P1; revalidation rejects forged/inconsistent plans.
    return _canonical(ReassessmentPlan.model_validate(plan).model_dump(mode="json"))


class RequestStatus(StrEnum):
    SINGLE = "single_request_planned"
    REPEATED = "identical_repeated_requests_deduplicated"
    CONFLICTING = "conflicting_proposals_rejected"
    REJECTED = "invalid_request_rejected"


class RequestCode(StrEnum):
    WRONG_CLAIM = "wrong_claim_binding"
    WRONG_POLICY = "wrong_policy_binding"
    STALE = "stale_case_revision"
    HASH = "source_hash_mismatch"
    ARTIFACT = "conflicting_artifact_metadata"
    CONFLICT = "conflicting_desired_inventories"
    REPEAT = "repeated_identical_request"


class RequestSetDecision(Contract):
    format: Literal["m25-request-set-decision-v1"] = "m25-request-set-decision-v1"
    request_count: Annotated[int, Field(strict=True, ge=1, le=MAX_REQUESTS)]
    request_set_sha256: Sha256
    distinct_valid_proposals: Annotated[int, Field(strict=True, ge=0, le=MAX_REQUESTS)]
    status: RequestStatus
    codes: tuple[RequestCode, ...]
    plan: ReassessmentPlan | None
    durable_receipt: Literal[False] = False
    execution_authorized: Literal[False] = False

    @model_validator(mode="after")
    def consistent(self) -> Self:
        order = tuple(RequestCode)
        if list(self.codes) != sorted(set(self.codes), key=order.index):
            raise ValueError("codes must be unique and in fixed order")
        planned = self.status in (RequestStatus.SINGLE, RequestStatus.REPEATED)
        if planned != (self.plan is not None):
            raise ValueError("only single or repeated identical requests carry a plan")
        expected = {
            RequestStatus.SINGLE: not self.codes,
            RequestStatus.REPEATED: self.codes == (RequestCode.REPEAT,),
            RequestStatus.CONFLICTING: self.codes == (RequestCode.CONFLICT,),
            RequestStatus.REJECTED: bool(self.codes)
            and not {RequestCode.CONFLICT, RequestCode.REPEAT} & set(self.codes),
        }[self.status]
        if not expected:
            raise ValueError("status and codes disagree")
        return self


def reconcile_requests(case: Case, requests: Sequence[AmendmentRequest]) -> RequestSetDecision:
    """Order-independent, fail-closed handling of a bounded batch of requests.

    Precedence: any invalid request rejects the set; then differing desired inventories
    conflict and nothing is planned (no merging); identical repeats yield one plan.
    This is a deterministic computation, not a durable idempotency receipt.
    """
    if not requests:
        raise AmendmentError("empty_request_set")
    if len(requests) > MAX_REQUESTS:
        raise AmendmentError("request_capacity_exceeded")
    case = _checked_case(case)
    validated = [AmendmentRequest.model_validate(r) for r in requests]
    request_set_sha256 = _hash(sorted(_hash(r.model_dump(mode="json")) for r in validated))
    failures: set[RequestCode] = set()
    plans: dict[str, ReassessmentPlan] = {}
    for request in validated:
        try:
            plan = plan_reassessment(case, request)
        except AmendmentError as error:
            failures.add(RequestCode(str(error)))
            continue
        plans[plan.amendment.proposal_sha256] = plan
    if failures:
        status, codes, chosen = RequestStatus.REJECTED, failures, None
    elif len(plans) > 1:
        status, codes, chosen = RequestStatus.CONFLICTING, {RequestCode.CONFLICT}, None
    elif len(validated) > 1:
        status, codes, chosen = RequestStatus.REPEATED, {RequestCode.REPEAT}, plans
    else:
        status, codes, chosen = RequestStatus.SINGLE, set(), plans
    return RequestSetDecision(
        request_count=len(validated),
        request_set_sha256=request_set_sha256,
        distinct_valid_proposals=len(plans),
        status=status,
        codes=tuple(c for c in RequestCode if c in codes),
        plan=next(iter(chosen.values())) if chosen else None,
    )
