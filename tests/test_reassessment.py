"""M25 P2 pure dependency, lifecycle-route and request-reconciliation tests (synthetic)."""

import ast
import inspect
import itertools
import json
from collections.abc import Callable
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from pydantic import ValidationError

from claims_ai import lifecycle
from claims_ai.amendments import (
    AmendmentError,
    AmendmentPlan,
    AmendmentRequest,
    Invalidation,
    ProposedDocument,
    Requirement,
    plan_amendment,
    source_binding,
)
from claims_ai.models import (
    Case,
    CaseState,
    DocumentMetadata,
    Evidence,
    ReviewerDecision,
    ReviewerRole,
)
from claims_ai.outcomes import reducer
from claims_ai.reassessment import (
    MAX_REQUESTS,
    Basis,
    Dependency,
    ImpactItem,
    LifecycleCode,
    PlanStep,
    ReassessmentPlan,
    RequestCode,
    RequestSetDecision,
    RequestStatus,
    RouteStatus,
    Step,
    canonical_reassessment,
    lifecycle_route,
    plan_reassessment,
    reconcile_requests,
)

ROOT = Path(__file__).resolve().parents[1]
DOC2 = "NS-DOC-00000010"  # Not a policy artifact ID in the shared fixtures.
EVD2 = "NS-EVD-00000002"


def proposal(document: DocumentMetadata, **changes: object) -> ProposedDocument:
    return ProposedDocument.model_validate(
        {**document.model_dump(), "scan_status": "quarantined", **changes}
    )


def request_for(case: Case, *documents: ProposedDocument) -> AmendmentRequest:
    return AmendmentRequest(expected=source_binding(case), proposed_documents=documents)


def new_document(case: Case, number: int, kind: str = "repair_estimate") -> ProposedDocument:
    doc_id = f"NS-DOC-{number:08X}"
    return proposal(
        case.documents[0],
        document_id=doc_id,
        artifact_ref=f"synthetic/{case.claim.claim_id}/{doc_id}.pdf",
        kind=kind,
        sha256=sha256(f"p2-development-{number}".encode()).hexdigest(),
    )


@pytest.fixture
def rich_case(awaiting_case: Case) -> Case:
    """Two accepted documents, traced rules, an empty trace and a duplicated rule ID."""
    first = awaiting_case.documents[0]
    second = DocumentMetadata.model_validate(
        {
            **first.model_dump(),
            "document_id": DOC2,
            "kind": "repair_estimate",
            "artifact_ref": f"synthetic/{first.claim_id}/{DOC2}.pdf",
            "sha256": "e" * 64,
        }
    )
    evidence2 = Evidence.model_validate(
        {
            **awaiting_case.evidence[0].model_dump(),
            "evidence_id": EVD2,
            "document_id": DOC2,
            "artifact_sha256": "e" * 64,
        }
    )
    evd1 = awaiting_case.evidence[0].evidence_id
    assert awaiting_case.assessment is not None
    assessment = {
        **awaiting_case.assessment.model_dump(),
        "evidence_ids": (evd1, EVD2),
        "rule_results": (
            {"rule_id": "rule-a", "outcome": "eligible", "evidence_ids": (evd1,)},
            {"rule_id": "rule-b", "outcome": "eligible", "evidence_ids": (EVD2,)},
            {"rule_id": "rule-c", "outcome": "eligible", "evidence_ids": ()},
            {"rule_id": "rule-d", "outcome": "eligible", "evidence_ids": (EVD2,)},
            {"rule_id": "rule-d", "outcome": "ineligible", "evidence_ids": (EVD2,)},
        ),
    }
    return Case.model_validate(
        {
            **awaiting_case.model_dump(),
            "claim": {
                **awaiting_case.claim.model_dump(),
                "document_ids": (first.document_id, DOC2),
            },
            "documents": (first, second),
            "evidence": (awaiting_case.evidence[0], evidence2),
            "assessment": assessment,
        }
    )


def keep_all(case: Case) -> list[ProposedDocument]:
    return [proposal(d) for d in case.documents]


def by_key(plan: ReassessmentPlan) -> dict[tuple[Invalidation, str], ImpactItem]:
    return {(i.category, i.item_id): i for i in plan.impact}


def in_state(case: Case, state: CaseState, decision: ReviewerDecision | None = None) -> Case:
    data: dict[str, Any] = {**case.model_dump(), "state": state}
    if state == CaseState.CLOSED:
        data.update(revision=6, decision=decision)
    elif state != CaseState.AWAITING_REVIEW:
        data.update(assessment=None)  # Domain contract: assessment only in review/closed.
    return Case.model_validate(data)


# --- Dependency impact --------------------------------------------------------------


def test_replaced_document_traces_direct_dependencies(rich_case: Case) -> None:
    docs = keep_all(rich_case)
    docs[1] = proposal(rich_case.documents[1], sha256="f" * 64)
    plan = plan_reassessment(rich_case, request_for(rich_case, *docs))
    items = by_key(plan)
    claim = rich_case.claim.claim_id
    assert items[(Invalidation.EVIDENCE, EVD2)].dependency == Dependency.DIRECT
    assert items[(Invalidation.EVIDENCE, "NS-EVD-00000001")].dependency == Dependency.NOT_TRACED
    assert items[(Invalidation.RULES, "rule-a")].dependency == Dependency.NOT_TRACED
    assert items[(Invalidation.RULES, "rule-b")].dependency == Dependency.DIRECT
    assert items[(Invalidation.RULES, "rule-c")].bases == (Basis.EMPTY_TRACE, Basis.M20_CLEARS)
    assert items[(Invalidation.RULES, "rule-d")].bases == (
        Basis.TRACED_EVIDENCE,
        Basis.DUPLICATE_TRACE,
        Basis.M20_CLEARS,
    )
    assert items[(Invalidation.ADVICE, "NS-ASM-00000001")].dependency == Dependency.DIRECT
    assert items[(Invalidation.POLICY, rich_case.claim.policy_id)].dependency == (
        Dependency.NOT_TRACED
    )
    for category in (Invalidation.REVIEW, Invalidation.ASSIGNMENTS):
        assert items[(category, claim)].bases == (Basis.WHOLE_CASE, Basis.M20_CLEARS)
        assert items[(category, claim)].dependency == Dependency.UNTRACEABLE
    rules = next(s for s in plan.steps if s.step == Step.RULES)
    assert rules.focus == ("rule-b", "rule-d")


def test_every_item_stays_invalidated_and_never_reusable(rich_case: Case) -> None:
    for docs in (
        [proposal(rich_case.documents[0])],
        [*keep_all(rich_case), new_document(rich_case, 0x20)],
        [],
    ):
        plan = plan_reassessment(rich_case, request_for(rich_case, *docs))
        assert plan.impact and all(i.invalidated and not i.reuse_authorized for i in plan.impact)
        assert all(Basis.M20_CLEARS in i.bases for i in plan.impact)
        assert plan.amendment.invalidations == tuple(Invalidation)


def test_removal_of_untraced_document_is_not_traced_but_still_invalidated(
    rich_case: Case,
) -> None:
    # Removing DOC2 is direct for its evidence; keep DOC2, remove nothing traced instead:
    # replace DOC1 metadata only, leaving rule-b/rule-d evidence untouched.
    docs = keep_all(rich_case)
    docs[0] = proposal(rich_case.documents[0], uploaded_at=datetime(2026, 1, 3, tzinfo=UTC))
    items = by_key(plan_reassessment(rich_case, request_for(rich_case, *docs)))
    assert items[(Invalidation.RULES, "rule-b")].dependency == Dependency.NOT_TRACED
    assert items[(Invalidation.RULES, "rule-b")].invalidated is True
    assert items[(Invalidation.RULES, "rule-a")].dependency == Dependency.DIRECT


def test_added_document_makes_rules_and_advice_untraceable(rich_case: Case) -> None:
    added = new_document(rich_case, 0x20)
    plan = plan_reassessment(rich_case, request_for(rich_case, *keep_all(rich_case), added))
    items = by_key(plan)
    assert items[(Invalidation.RULES, "rule-a")].dependency == Dependency.UNTRACEABLE
    assert Basis.ADDED_DOCUMENT in items[(Invalidation.ADVICE, "NS-ASM-00000001")].bases
    assert all(
        i.dependency == Dependency.NOT_TRACED
        for i in plan.impact
        if i.category == Invalidation.EVIDENCE
    )
    evidence_step = next(s for s in plan.steps if s.step == Step.EVIDENCE)
    assert evidence_step.focus == (added.document_id,)


@pytest.mark.parametrize("via", ["policy_artifact_id", "policy_document_kind"])
def test_policy_material_change_is_direct_for_policy_rules_and_advice(
    rich_case: Case, via: str
) -> None:
    if via == "policy_artifact_id":
        added = new_document(rich_case, 0x2)  # NS-DOC-00000002 is the policy schedule ID.
    else:
        added = new_document(rich_case, 0x20, kind="endorsement")
    plan = plan_reassessment(rich_case, request_for(rich_case, *keep_all(rich_case), added))
    items = by_key(plan)
    policy = items[(Invalidation.POLICY, rich_case.claim.policy_id)]
    assert policy.dependency == Dependency.DIRECT
    derived = {Invalidation.RULES, Invalidation.ADVICE}
    assert all(i.dependency == Dependency.DIRECT for i in plan.impact if i.category in derived)
    policy_step = next(s for s in plan.steps if s.step == Step.POLICY)
    assert policy_step.focus == (rich_case.claim.policy_id,)


def test_advisory_is_never_reported_as_untraced(rich_case: Case) -> None:
    docs = keep_all(rich_case)
    docs[0] = proposal(rich_case.documents[0], uploaded_at=datetime(2026, 1, 3, tzinfo=UTC))
    docs[1] = proposal(rich_case.documents[1], uploaded_at=datetime(2026, 1, 3, tzinfo=UTC))
    plan = plan_reassessment(rich_case, request_for(rich_case, *docs))
    advice = by_key(plan)[(Invalidation.ADVICE, "NS-ASM-00000001")]
    assert Basis.HOLISTIC in advice.bases and advice.dependency != Dependency.NOT_TRACED


def test_reviewer_decision_facts_are_bound_to_stale_advice(
    awaiting_case: Case, decision: ReviewerDecision
) -> None:
    closed = in_state(awaiting_case, CaseState.CLOSED, decision)
    plan = plan_reassessment(closed, request_for(closed, new_document(closed, 0x20)))
    facts = by_key(plan)[(Invalidation.FACTS, "NS-ASM-00000001")]
    assert facts.bases == (Basis.TRACED_EVIDENCE, Basis.BOUND_ADVISORY, Basis.M20_CLEARS)
    assert facts.dependency == Dependency.DIRECT
    review = next(s for s in plan.steps if s.step == Step.REVIEW)
    assert review.focus == ("NS-ASM-00000001",)
    assert closed.decision == decision  # Prior outcome history is not altered.


def test_case_without_derived_material_lists_only_external_bindings(case: Case) -> None:
    bare = Case.model_validate({**case.model_dump(), "evidence": (), "policy": None})
    plan = plan_reassessment(bare, request_for(bare, new_document(bare, 0x20)))
    assert {i.category for i in plan.impact} == {Invalidation.REVIEW, Invalidation.ASSIGNMENTS}


def test_unchanged_inventory_has_no_impact_or_steps(rich_case: Case) -> None:
    request = request_for(rich_case, *keep_all(rich_case))
    plan = plan_reassessment(rich_case, request)
    assert plan.impact == () and plan.steps == ()
    assert plan.amendment == plan_amendment(rich_case, request)


def test_output_contains_ids_only_not_narrative_or_values(rich_case: Case) -> None:
    payload = canonical_reassessment(plan_reassessment(rich_case, request_for(rich_case)))
    assert rich_case.claim.narrative.encode() not in payload
    assert rich_case.evidence[0].observed_value.encode() not in payload
    assert rich_case.assessment is not None
    assert rich_case.assessment.rationale.encode() not in payload
    assert b"artifact_ref" not in payload and b"uploaded_at" not in payload


# --- Ordered reassessment plan ------------------------------------------------------


def test_step_order_and_requirement_coverage(rich_case: Case) -> None:
    plan = plan_reassessment(
        rich_case, request_for(rich_case, *keep_all(rich_case), new_document(rich_case, 0x20))
    )
    assert [s.step for s in plan.steps] == [
        Step.SOURCE,
        Step.IDENTITY,
        Step.REVIEW_INVALIDATION,
        Step.CORRECTION,
        Step.BYTES,
        Step.SCAN,
        Step.EVIDENCE,
        Step.POLICY,
        Step.RULES,
        Step.ADVISORY,
        Step.REVIEW,
        Step.APPROVAL,
    ]
    assert [s.position for s in plan.steps] == list(range(1, 13))
    assert set(plan.amendment.requirements) <= {s.requirement for s in plan.steps}


def test_empty_inventory_omits_byte_scan_and_admission_steps(rich_case: Case) -> None:
    plan = plan_reassessment(rich_case, request_for(rich_case))
    steps = {s.step for s in plan.steps}
    assert not steps & {Step.BYTES, Step.SCAN, Step.EVIDENCE}
    assert Requirement.BYTES not in plan.amendment.requirements


def test_repeat_and_reverse_order_produce_identical_bytes(
    rich_case: Case, record_property: Callable[[str, object], None]
) -> None:
    docs = (
        new_document(rich_case, 0x21),
        proposal(rich_case.documents[0], sha256="f" * 64),
        new_document(rich_case, 0x20),
    )
    first = canonical_reassessment(plan_reassessment(rich_case, request_for(rich_case, *docs)))
    for _ in range(10):
        again = plan_reassessment(rich_case, request_for(rich_case, *reversed(docs)))
        assert canonical_reassessment(again) == first
    decoded = ReassessmentPlan.model_validate_json(first)
    assert canonical_reassessment(decoded) == first
    record_property("canonical_reassessment_sha256", sha256(first).hexdigest())
    record_property("canonical_reassessment_bytes", len(first))
    record_property("amendment_sha256", decoded.amendment_sha256)
    record_property("repetitions_with_reversed_inventory", 10)


# --- Lifecycle preconditions --------------------------------------------------------

EXPECTED_ROUTES = {
    CaseState.RECEIVED: (RouteStatus.SUPPORTED, (CaseState.VALIDATING,), False),
    CaseState.VALIDATING: (RouteStatus.BLOCKED, (), False),
    CaseState.EXTRACTING: (RouteStatus.BLOCKED, (), False),
    CaseState.ASSESSING: (
        RouteStatus.SUPPORTED,
        (CaseState.AWAITING_EVIDENCE, CaseState.VALIDATING),
        False,
    ),
    CaseState.AWAITING_REVIEW: (RouteStatus.SUPPORTED, (CaseState.VALIDATING,), False),
    CaseState.AWAITING_EVIDENCE: (RouteStatus.SUPPORTED, (CaseState.VALIDATING,), False),
    CaseState.QUARANTINED: (RouteStatus.SUPPORTED, (CaseState.VALIDATING,), True),
    CaseState.PROCESSING_FAILED: (RouteStatus.SUPPORTED, (CaseState.VALIDATING,), False),
    CaseState.CLOSED: (RouteStatus.BLOCKED, (), True),
}


@pytest.mark.parametrize("state", list(CaseState))
def test_route_table_is_total_and_matches_expectation(state: CaseState) -> None:
    route = lifecycle_route(state)
    assert (route.status, route.transitions, route.lifecycle_supervisor_required) == (
        EXPECTED_ROUTES[state]
    )


@pytest.mark.parametrize("state", list(CaseState))
def test_supported_routes_are_allowed_by_lifecycle_table(state: CaseState) -> None:
    route = lifecycle_route(state)
    current = state
    for target in route.transitions:
        assert target in lifecycle.ALLOWED_TRANSITIONS[current]
        current = target
    if route.status == RouteStatus.BLOCKED:
        # M20 CORRECT steps to VALIDATING; that edge is absent from these states,
        # and a supervisor reopening of CLOSED lands in VALIDATING, which has none either.
        start = CaseState.VALIDATING if state == CaseState.CLOSED else state
        assert CaseState.VALIDATING not in lifecycle.ALLOWED_TRANSITIONS[start]


def test_route_mirrors_m20_correct_and_reopen_branches() -> None:
    # Drift guard: if M20's CORRECT/REOPEN semantics change, P2 routes must be re-derived.
    source = inspect.getsource(reducer.reduce)
    assert (
        "if case.state == CaseState.CLOSED:\n"
        '            raise OutcomeError("closed_case_requires_reopening")\n'
        "        if case.state == CaseState.ASSESSING:\n"
        "            step(CaseState.AWAITING_EVIDENCE)\n"
        "        step(CaseState.VALIDATING)"
    ) in source
    assert "elif command.action == Action.REOPEN:" in source
    assert lifecycle.ALLOWED_TRANSITIONS[CaseState.CLOSED] == frozenset({CaseState.VALIDATING})


@pytest.mark.parametrize("state", [CaseState.QUARANTINED, CaseState.CLOSED])
def test_lifecycle_supervisor_requirement_matches_pure_transition(
    awaiting_case: Case, decision: ReviewerDecision, now: datetime, state: CaseState
) -> None:
    source = in_state(awaiting_case, state, decision)

    def attempt(role: ReviewerRole) -> None:
        lifecycle.transition_case(
            source,
            lifecycle.TransitionRequest(
                target=CaseState.VALIDATING,
                expected_revision=source.revision,
                actor=lifecycle.TransitionActor(principal_id=UUID(int=1), role=role),
                audit_event_id=UUID(int=2),
                occurred_at=now,
                reason="synthetic route check",
            ),
        )

    with pytest.raises(ValueError, match="supervisor"):
        attempt(ReviewerRole.REVIEWER)
    attempt(ReviewerRole.SUPERVISOR)  # In-memory record only; nothing is persisted.
    assert lifecycle_route(state).lifecycle_supervisor_required is True


def test_closed_case_plan_requires_reopen_then_reports_blocked_route(
    awaiting_case: Case, decision: ReviewerDecision
) -> None:
    closed = in_state(awaiting_case, CaseState.CLOSED, decision)
    plan = plan_reassessment(closed, request_for(closed))
    assert plan.lifecycle.codes == (LifecycleCode.REOPEN, LifecycleCode.REOPENED_UNSUPPORTED)
    assert [s.step for s in plan.steps[:4]] == [
        Step.SOURCE,
        Step.IDENTITY,
        Step.REOPEN,
        Step.ROUTE_BLOCKED,
    ]
    assert plan.execution_authorized is False and plan.automatic_transition is False


@pytest.mark.parametrize(
    ("state", "code", "extra"),
    [
        (CaseState.QUARANTINED, LifecycleCode.QUARANTINE_RELEASE, Step.SUPERVISOR),
        (CaseState.ASSESSING, LifecycleCode.VIA_AWAITING_EVIDENCE, None),
        (CaseState.PROCESSING_FAILED, LifecycleCode.PROCESSING_FAILED, None),
        (CaseState.VALIDATING, LifecycleCode.IN_FLIGHT, Step.ROUTE_BLOCKED),
        (CaseState.EXTRACTING, LifecycleCode.IN_FLIGHT, Step.ROUTE_BLOCKED),
    ],
)
def test_state_specific_preconditions_are_explicit(
    case: Case, state: CaseState, code: LifecycleCode, extra: Step | None
) -> None:
    source = in_state(case, state)
    plan = plan_reassessment(source, request_for(source))
    assert plan.lifecycle.source_state == state and plan.lifecycle.codes == (code,)
    names = [s.step for s in plan.steps]
    assert names[:2] == [Step.SOURCE, Step.IDENTITY]
    lifecycle_steps = {Step.REOPEN, Step.ROUTE_BLOCKED, Step.SUPERVISOR} & set(names)
    assert lifecycle_steps == ({extra} if extra else set())
    assert source.state == state  # Planning performs no transition.


# --- Conflicting and repeated requests ----------------------------------------------


def test_single_request_matches_direct_plan(rich_case: Case) -> None:
    request = request_for(rich_case)
    decision = reconcile_requests(rich_case, [request])
    assert decision.status == RequestStatus.SINGLE and decision.codes == ()
    assert decision.plan == plan_reassessment(rich_case, request)
    assert decision.durable_receipt is False


def test_identical_repeats_deduplicate_to_identical_plan(rich_case: Case) -> None:
    request = request_for(rich_case, new_document(rich_case, 0x20))
    decision = reconcile_requests(rich_case, [request] * 3)
    assert decision.status == RequestStatus.REPEATED
    assert decision.codes == (RequestCode.REPEAT,) and decision.request_count == 3
    assert decision.plan is not None
    assert canonical_reassessment(decision.plan) == canonical_reassessment(
        plan_reassessment(rich_case, request)
    )


def test_conflicting_inventories_fail_closed_regardless_of_order(rich_case: Case) -> None:
    a = request_for(rich_case, new_document(rich_case, 0x20))
    b = request_for(rich_case, new_document(rich_case, 0x21))
    c = request_for(rich_case)
    results = {
        reconcile_requests(rich_case, list(order)).model_dump_json()
        for order in itertools.permutations([a, b, c, a])
    }
    assert len(results) == 1
    decision = RequestSetDecision.model_validate_json(results.pop())
    assert decision.status == RequestStatus.CONFLICTING and decision.plan is None
    assert decision.codes == (RequestCode.CONFLICT,) and decision.distinct_valid_proposals == 3


def test_invalid_requests_reject_the_set_with_sorted_codes(rich_case: Case) -> None:
    valid = request_for(rich_case)
    binding = valid.expected
    stale = valid.model_copy(
        update={"expected": binding.model_copy(update={"case_revision": binding.case_revision + 1})}
    )
    mismatched = valid.model_copy(
        update={"expected": binding.model_copy(update={"case_sha256": "0" * 64})}
    )
    other = request_for(rich_case, new_document(rich_case, 0x20))
    for order in itertools.permutations([mismatched, valid, stale, other]):
        decision = reconcile_requests(rich_case, list(order))
        assert decision.status == RequestStatus.REJECTED and decision.plan is None
        assert decision.codes == (RequestCode.STALE, RequestCode.HASH)


def test_conflicting_artifact_metadata_code(rich_case: Case) -> None:
    clash = new_document(rich_case, 0x20).model_copy(update={"sha256": "a" * 64, "byte_size": 7})
    decision = reconcile_requests(rich_case, [request_for(rich_case, *keep_all(rich_case), clash)])
    assert decision.codes == (RequestCode.ARTIFACT,)


def test_wrong_claim_and_policy_codes(rich_case: Case, case: Case) -> None:
    other_claim = case.claim.model_copy(update={"claim_id": "NS-CLM-00000009"})
    binding = source_binding(rich_case)
    wrong_claim = AmendmentRequest(
        expected=binding.model_copy(update={"claim_id": other_claim.claim_id}),
        proposed_documents=(),
    )
    wrong_policy = AmendmentRequest(
        expected=binding.model_copy(update={"policy_id": "NS-POL-00000009"}),
        proposed_documents=(),
    )
    decision = reconcile_requests(rich_case, [wrong_policy, wrong_claim])
    assert decision.codes == (RequestCode.WRONG_CLAIM, RequestCode.WRONG_POLICY)


def test_replay_after_applied_amendment_is_stale(case: Case) -> None:
    request = request_for(case, new_document(case, 0x20))
    assert reconcile_requests(case, [request]).status == RequestStatus.SINGLE
    # Any later execution advances the source revision; the old request cannot replay.
    amended = Case.model_validate({**case.model_dump(), "revision": case.revision + 1})
    decision = reconcile_requests(amended, [request])
    assert decision.status == RequestStatus.REJECTED and decision.codes == (RequestCode.STALE,)


def test_rejection_takes_precedence_over_conflict(rich_case: Case) -> None:
    a = request_for(rich_case, new_document(rich_case, 0x20))
    b = request_for(rich_case)
    stale = b.model_copy(update={"expected": b.expected.model_copy(update={"case_revision": 99})})
    decision = reconcile_requests(rich_case, [a, b, stale])
    assert decision.status == RequestStatus.REJECTED and decision.distinct_valid_proposals == 2


def test_request_set_bounds(rich_case: Case) -> None:
    with pytest.raises(AmendmentError, match="empty_request_set"):
        reconcile_requests(rich_case, [])
    request = request_for(rich_case)
    assert reconcile_requests(rich_case, [request] * MAX_REQUESTS).request_count == MAX_REQUESTS
    with pytest.raises(AmendmentError, match="request_capacity_exceeded"):
        reconcile_requests(rich_case, [request] * (MAX_REQUESTS + 1))


def test_forged_request_inside_set_is_revalidated(rich_case: Case) -> None:
    smuggled = ProposedDocument.model_construct(
        **{**rich_case.documents[0].model_dump(), "scan_status": "accepted"}
    )
    forged = AmendmentRequest.model_construct(
        expected=source_binding(rich_case), proposed_documents=(smuggled,)
    )
    with pytest.raises(ValidationError):
        reconcile_requests(rich_case, [forged])


# --- Authority, immutability and purity ---------------------------------------------


@pytest.mark.parametrize(
    "field",
    [
        "execution_authorized",
        "reuse_authorized",
        "automatic_transition",
        "settlement_authorized",
    ],
)
def test_plan_cannot_claim_authority(rich_case: Case, field: str) -> None:
    data = plan_reassessment(rich_case, request_for(rich_case)).model_dump()
    data[field] = True
    with pytest.raises(ValidationError):
        ReassessmentPlan.model_validate(data)
    with pytest.raises(ValidationError):
        canonical_reassessment(ReassessmentPlan.model_construct(**data))


def test_forged_inconsistent_plans_are_rejected(rich_case: Case) -> None:
    plan = plan_reassessment(rich_case, request_for(rich_case))
    data = json.loads(plan.model_dump_json())
    mutations: list[Callable[[dict[str, Any]], None]] = [
        lambda d: d["impact"][0].update(invalidated=False),
        lambda d: d["impact"][0].update(reuse_authorized=True),
        lambda d: d["impact"][0].update(dependency=Dependency.NOT_TRACED.value),
        lambda d: d["impact"][-1].update(bases=[Basis.WHOLE_CASE.value]),
        lambda d: d.update(steps=d["steps"][:-3]),
        lambda d: d.update(steps=list(reversed(d["steps"]))),
        lambda d: d.update(impact=list(reversed(d["impact"]))),
        lambda d: d.update(amendment_sha256="0" * 64),
        lambda d: d["steps"][2].update(requirement=Requirement.REOPEN.value),
        lambda d: d["lifecycle"].update(status=RouteStatus.BLOCKED.value, transitions=[]),
        lambda d: d.update(approved_by="supervisor"),
        lambda d: d["lifecycle"].update(source_state=CaseState.CLOSED.value),
        lambda d: d["lifecycle"].update(lifecycle_supervisor_required=True),
    ]
    for mutate in mutations:
        forged = json.loads(json.dumps(data))
        mutate(forged)
        with pytest.raises(ValidationError):
            ReassessmentPlan.model_validate(forged)


def test_forged_closed_plan_cannot_drop_reopen_or_blocker(
    awaiting_case: Case, decision: ReviewerDecision
) -> None:
    closed = in_state(awaiting_case, CaseState.CLOSED, decision)
    data = json.loads(plan_reassessment(closed, request_for(closed)).model_dump_json())
    for drop in (Step.REOPEN.value, Step.ROUTE_BLOCKED.value):
        steps = [s for s in data["steps"] if s["step"] != drop]
        for n, item in enumerate(steps, start=1):
            item["position"] = n
        with pytest.raises(ValidationError):
            ReassessmentPlan.model_validate({**data, "steps": steps})


def test_request_decision_cannot_carry_plan_on_conflict(rich_case: Case) -> None:
    decision = reconcile_requests(rich_case, [request_for(rich_case)])
    data = decision.model_dump()
    for update in (
        {"status": RequestStatus.CONFLICTING, "codes": (RequestCode.CONFLICT,)},
        {"durable_receipt": True},
        {"execution_authorized": True},
        {"codes": (RequestCode.REPEAT,)},
    ):
        with pytest.raises(ValidationError):
            RequestSetDecision.model_validate({**data, **update})


def test_inputs_and_results_are_immutable(rich_case: Case) -> None:
    request = request_for(rich_case, new_document(rich_case, 0x20))
    before = (rich_case.model_dump_json(), request.model_dump_json())
    plan = plan_reassessment(rich_case, request)
    assert (rich_case.model_dump_json(), request.model_dump_json()) == before
    for record, field in (
        (plan, "execution_authorized"),
        (plan.impact[0], "invalidated"),
        (plan.steps[0], "focus"),
        (plan.lifecycle, "transitions"),
    ):
        with pytest.raises(ValidationError):
            setattr(record, field, None)
    assert isinstance(plan.impact, tuple) and isinstance(plan.steps, tuple)


def test_planning_needs_no_files_network_or_database(
    rich_case: Case, monkeypatch: pytest.MonkeyPatch
) -> None:
    request = request_for(rich_case, new_document(rich_case, 0x20))

    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("pure planning attempted external access")

    # In-process regression checks only, not proof of host/process containment.
    with monkeypatch.context() as guard:
        guard.setattr("builtins.open", denied)
        guard.setattr(Path, "open", denied)
        guard.setattr("socket.socket", denied)
        guard.setattr("sqlite3.connect", denied)
        assert canonical_reassessment(plan_reassessment(rich_case, request))
        assert reconcile_requests(rich_case, [request, request]).plan is not None


def test_dependency_surface_is_pure() -> None:
    # Static dependency guard, not an OS sandbox or an M24 containment claim.
    tree = ast.parse((ROOT / "src/claims_ai/reassessment.py").read_text())
    imports = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports == {
        "collections.abc",
        "enum",
        "typing",
        "pydantic",
        "claims_ai.amendments",
        "claims_ai.models",
    }
    for model in (ReassessmentPlan, ImpactItem, PlanStep, RequestSetDecision):
        assert model.model_config["frozen"] is True
        assert model.model_config["extra"] == "forbid"


def test_p1_module_and_evidence_bindings_are_preserved() -> None:
    record = json.loads((ROOT / "docs/milestones/m25-p1/verification.json").read_text())
    for path in (
        "src/claims_ai/amendments.py",
        "tests/test_amendments.py",
        "docs/milestones/m25-p1/README.md",
        "docs/milestones/m25-p1/focused-run-1.xml",
        "docs/milestones/m25-p1/focused-run-2.xml",
        "docs/milestones/m25-p1/regressions.xml",
    ):
        expected = record["artifact_bindings"][path]["sha256"]
        assert sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    assert AmendmentPlan.model_fields["format"].default == "m25-amendment-plan-v1"
