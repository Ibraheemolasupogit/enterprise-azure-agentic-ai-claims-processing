"""Synthetic human authority, exact advisory binding, audit replay and atomic review actions."""

import asyncio
import json
import socket
import subprocess
import sys
import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import cast
from uuid import uuid4

import pytest
from pydantic import ValidationError

from claims_ai.agent_tools.contracts import ALLOWLIST, ToolGrant
from claims_ai.human_review.__main__ import (
    NOW,
    demo_decision,
    demo_queue,
    demo_sessions,
)
from claims_ai.human_review.contracts import (
    AssignmentRequest,
    InvalidationRequest,
    Principal,
    PrincipalKind,
    QueueEntry,
    ReviewAction,
    ReviewBinding,
    ReviewCode,
    ReviewDecision,
    ReviewError,
    ReviewEvent,
    ReviewLimits,
    ReviewSession,
    ReviewState,
)
from claims_ai.human_review.service import ReviewQueue
from claims_ai.models import CaseState, ReviewerRole
from claims_ai.rules.specification import digest
from claims_ai.workflow.__main__ import demo_grant, demo_request
from claims_ai.workflow.contracts import Checkpoint, Stage, WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "data/rules/motor/v1"
type Advisory = tuple[WorkflowRequest, ToolGrant, Checkpoint]
type Store = tuple[ReviewQueue, QueueEntry, dict[str, ReviewSession]]


@pytest.fixture(scope="module")
def sources() -> Callable[[str], Advisory]:
    cache: dict[str, Advisory] = {}

    def load(name: str) -> Advisory:
        if name not in cache:
            request = demo_request(SPEC_ROOT, name, "m15-test-" + name)
            grant = demo_grant(request)
            checkpoint = asyncio.run(WorkflowRunner().run(request, grant))
            cache[name] = (request, grant, checkpoint)
        return cache[name]

    return load


@pytest.fixture
def store(sources: Callable[[str], Advisory]) -> Store:
    sessions = demo_sessions()
    queue, entry = asyncio.run(demo_queue(*sources("valid-v1"), sessions))
    return queue, entry, sessions


def revise(decision: ReviewDecision, **changes: object) -> ReviewDecision:
    return ReviewDecision.model_validate({**decision.model_dump(), **changes})


def detail_entry(store: Store) -> QueueEntry:
    queue, entry, sessions = store
    return queue.details.get(sessions["reviewer"], entry.entry_id).entry


@pytest.mark.parametrize(
    "action,state",
    [
        (ReviewAction.APPROVE, ReviewState.APPROVED),
        (ReviewAction.REJECT, ReviewState.REJECTED),
        (ReviewAction.REQUEST_EVIDENCE, ReviewState.EVIDENCE),
        (ReviewAction.ESCALATE, ReviewState.SUPERVISOR),
    ],
)
def test_explicit_human_actions_are_advisory_only_and_duplicates_are_receipts(
    store: Store, action: ReviewAction, state: ReviewState
) -> None:
    queue, entry, sessions = store
    before = queue.details.get(sessions["reviewer"], entry.entry_id)
    decision = demo_decision(entry, action, "human-action")
    event = queue.decide(sessions["reviewer"], decision)
    assert queue.decide(sessions["reviewer"], decision) == event
    detail = queue.details.get(sessions["reviewer"], entry.entry_id)
    assert detail.entry.state == state and len(detail.entry.events) == 4
    assert detail.entry.events[:-1] == entry.events
    assert event.actor == sessions["reviewer"].principal
    assert event.occurred_at == decision.occurred_at and event.rationale == decision.rationale
    assert event.correlation_id == entry.correlation_id
    assert detail.current_case.decision is None and detail.current_case.assessment is None
    assert detail.entry.human_approval_required and detail.entry.final_outcome is None
    assert not detail.entry.settlement_authorized
    if action == ReviewAction.REQUEST_EVIDENCE:
        assert event.case_transition is not None
        assert detail.current_case.state == CaseState.AWAITING_EVIDENCE
        assert detail.current_case.revision == before.current_case.revision + 1
        assert detail.current_case.evidence == before.current_case.evidence
        assert detail.advisory_snapshot == before.advisory_snapshot
    else:
        assert event.case_transition is None and detail.current_case == before.current_case


@pytest.mark.parametrize("name", ["agent", "mcp", "model", "host"])
def test_nonhuman_principals_never_read_or_decide(store: Store, name: str) -> None:
    queue, entry, sessions = store
    for call in (
        lambda: queue.details.list(sessions[name]),
        lambda: queue.details.get(sessions[name], entry.entry_id),
        lambda: queue.decide(sessions[name], demo_decision(entry, ReviewAction.APPROVE, "forged")),
    ):
        with pytest.raises(ReviewError) as error:
            call()
        assert error.value.code == ReviewCode.DENIED
    assert detail_entry(store) == entry


def test_unassigned_case_access_and_unknown_entry_are_indistinguishable(store: Store) -> None:
    queue, entry, sessions = store
    assert queue.details.list(sessions["outsider"]) == ()
    for entry_id in (entry.entry_id, "0" * 64):
        with pytest.raises(ReviewError, match=ReviewCode.DENIED):
            queue.details.get(sessions["outsider"], entry_id)
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.decide(sessions["outsider"], demo_decision(entry, ReviewAction.APPROVE, "outsider"))
    assert not hasattr(queue.details, "decide") and not hasattr(queue.details, "assign")


def test_copied_or_unregistered_session_cannot_claim_human_identity(store: Store) -> None:
    queue, entry, sessions = store
    forged = ReviewSession(sessions["reviewer"].principal)
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.decide(forged, demo_decision(entry, ReviewAction.APPROVE, "forged-session"))
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.details.get(forged, entry.entry_id)
    serialized = cast(ReviewSession, {"principal": sessions["reviewer"].principal.model_dump()})
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.decide(serialized, demo_decision(entry, ReviewAction.APPROVE, "serialized-session"))


@pytest.mark.parametrize("producer", ["workflow", "reviewed_facts"])
def test_producers_and_fact_reviewers_cannot_review_their_own_advisory(
    sources: Callable[[str], Advisory], producer: str
) -> None:
    request, grant, checkpoint = sources("valid-v1")
    principal_id = (
        grant.principal_id if producer == "workflow" else request.reviewed_facts[0].reviewer_id
    )
    sessions = demo_sessions()
    sessions["producer"] = ReviewSession(
        Principal(principal_id=principal_id, kind=PrincipalKind.HUMAN, role=ReviewerRole.SUPERVISOR)
    )
    queue, entry = asyncio.run(demo_queue(request, grant, checkpoint, sessions))
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.assign(
            sessions["host"],
            AssignmentRequest(
                request_id=uuid4(),
                entry_id=entry.entry_id,
                claim_id=entry.binding.claim_id,
                expected_review_revision=entry.review_revision,
                assignee_id=principal_id,
                occurred_at=NOW + timedelta(seconds=3),
                rationale="Synthetic self-review attempt.",
            ),
        )
    assert queue.details.list(sessions["producer"]) == ()


@pytest.mark.parametrize(
    "fixture",
    [
        "gradual-wear-exclusion",
        "unknown-cause",
        "high-value-threshold",
        "reported-ambiguity",
        "conflicting-amounts",
    ],
)
def test_adverse_ambiguous_risky_and_conflicting_advisories_require_supervisors(
    sources: Callable[[str], Advisory], fixture: str
) -> None:
    sessions = demo_sessions()
    queue, entry = asyncio.run(demo_queue(*sources(fixture), sessions))
    assert entry.state == ReviewState.SUPERVISOR
    assert entry.required_reviewer == ReviewerRole.SUPERVISOR
    for action in (ReviewAction.APPROVE, ReviewAction.REJECT, ReviewAction.REQUEST_EVIDENCE):
        with pytest.raises(ReviewError, match=ReviewCode.DENIED):
            queue.decide(sessions["reviewer"], demo_decision(entry, action, fixture))
    if not entry.recommendation_available:
        for action in (ReviewAction.APPROVE, ReviewAction.REJECT):
            with pytest.raises(ReviewError, match=ReviewCode.TRANSITION):
                queue.decide(sessions["supervisor"], demo_decision(entry, action, fixture))
    action = (
        ReviewAction.REJECT if entry.recommendation_available else ReviewAction.REQUEST_EVIDENCE
    )
    event = queue.decide(
        sessions["supervisor"], demo_decision(entry, action, fixture + "/supervisor")
    )
    assert event.after == (
        ReviewState.REJECTED if entry.recommendation_available else ReviewState.EVIDENCE
    )
    assert queue.details.get(sessions["supervisor"], entry.entry_id).current_case.decision is None


def test_explicit_escalation_cannot_be_bypassed_by_the_assigned_reviewer(store: Store) -> None:
    queue, entry, sessions = store
    queue.decide(sessions["reviewer"], demo_decision(entry, ReviewAction.ESCALATE, "escalate"))
    entry = detail_entry(store)
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.decide(sessions["reviewer"], demo_decision(entry, ReviewAction.APPROVE, "bypass"))
    event = queue.decide(
        sessions["supervisor"], demo_decision(entry, ReviewAction.APPROVE, "supervised")
    )
    assert event.after == ReviewState.APPROVED


@pytest.mark.parametrize(
    "field,value",
    [
        ("claim_id", "NS-CLM-00000000"),
        ("case_revision", 999),
        ("case_sha256", "0" * 64),
        ("evidence_sha256", "0" * 64),
        ("policy_id", "NS-POL-00000000"),
        ("policy_version", "stale-policy"),
        ("policy_sha256", "0" * 64),
        ("index_sha256", "0" * 64),
        ("rule_version", "stale-rule"),
        ("rule_sha256", "0" * 64),
        ("rule_execution_key", "0" * 64),
        ("workflow_execution_key", "0" * 64),
        ("checkpoint_sha256", "0" * 64),
        ("advisory_task_sha256", "0" * 64),
        ("advisory_sha256", "0" * 64),
    ],
)
def test_every_exact_review_binding_field_is_checked_before_commit(
    store: Store, field: str, value: object
) -> None:
    queue, entry, sessions = store
    decision = demo_decision(entry, ReviewAction.APPROVE, "stale-binding")
    wrong = ReviewBinding.model_validate({**entry.binding.model_dump(), field: value})
    with pytest.raises(ReviewError, match=ReviewCode.STALE):
        queue.decide(sessions["reviewer"], revise(decision, expected=wrong))
    assert detail_entry(store) == entry


@pytest.mark.parametrize(
    "field",
    ["case_revision", "evidence_sha256", "policy_version", "rule_version", "advisory_task_sha256"],
)
def test_host_reported_changes_invalidate_pending_actions_and_prior_duplicate_receipts(
    store: Store, field: str
) -> None:
    queue, entry, sessions = store
    decision = demo_decision(entry, ReviewAction.APPROVE, "approval-before-change")
    event = queue.decide(sessions["reviewer"], decision)
    before = detail_entry(store)
    replacement = ReviewBinding.model_validate(
        {
            **entry.binding.model_dump(),
            field: entry.binding.case_revision + 1
            if field == "case_revision"
            else "new-version"
            if "version" in field
            else "0" * 64,
        }
    )
    invalidation = InvalidationRequest(
        request_id=uuid4(),
        entry_id=entry.entry_id,
        expected_review_revision=before.review_revision,
        replacement=replacement,
        occurred_at=NOW + timedelta(seconds=11),
        rationale="Host reports changed source snapshot.",
    )
    invalidated = queue.invalidate(sessions["host"], invalidation)
    assert queue.invalidate(sessions["host"], invalidation) == invalidated
    with pytest.raises(ReviewError, match=ReviewCode.STALE):
        queue.decide(sessions["reviewer"], decision)
    assert detail_entry(store).events[-2] == event
    assert detail_entry(store).state == ReviewState.STALE


def test_optimistic_review_revision_and_changed_duplicate_content_fail_closed(store: Store) -> None:
    queue, entry, sessions = store
    decision = demo_decision(entry, ReviewAction.APPROVE, "duplicate")
    with pytest.raises(ReviewError, match=ReviewCode.CONFLICT):
        queue.decide(sessions["reviewer"], revise(decision, expected_review_revision=1))
    original = queue.decide(sessions["reviewer"], decision)
    with pytest.raises(ReviewError, match=ReviewCode.CONFLICT):
        queue.decide(
            sessions["reviewer"], revise(decision, rationale="Changed duplicate rationale.")
        )
    assert detail_entry(store).events[-1] == original
    assert len(detail_entry(store).events) == 4


def test_concurrent_incompatible_actions_have_one_atomic_winner(store: Store) -> None:
    queue, entry, sessions = store
    barrier = threading.Barrier(2)

    def run(action: ReviewAction) -> ReviewEvent | ReviewCode:
        decision = demo_decision(entry, action, action.value)
        barrier.wait(timeout=10)
        try:
            return queue.decide(sessions["reviewer"], decision)
        except ReviewError as error:
            return error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, (ReviewAction.APPROVE, ReviewAction.REJECT)))
    assert sum(isinstance(r, ReviewEvent) for r in results) == 1
    assert ReviewCode.CONFLICT in results
    assert len(detail_entry(store).events) == 4


def test_concurrent_identical_actions_return_one_receipt(store: Store) -> None:
    queue, entry, sessions = store
    decision = demo_decision(entry, ReviewAction.APPROVE, "concurrent-duplicate")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: queue.decide(sessions["reviewer"], decision), range(2)))
    assert results[0] == results[1] and len(detail_entry(store).events) == 4


@pytest.mark.parametrize(
    "terminal", [ReviewAction.APPROVE, ReviewAction.REJECT, ReviewAction.REQUEST_EVIDENCE]
)
@pytest.mark.parametrize("next_action", list(ReviewAction))
def test_completed_review_never_accepts_a_new_action(
    store: Store, terminal: ReviewAction, next_action: ReviewAction
) -> None:
    queue, entry, sessions = store
    queue.decide(sessions["reviewer"], demo_decision(entry, terminal, "terminal"))
    current = detail_entry(store)
    with pytest.raises(ReviewError, match=ReviewCode.TRANSITION):
        queue.decide(sessions["supervisor"], demo_decision(current, next_action, "forbidden"))
    assert detail_entry(store) == current


@pytest.mark.parametrize(
    "changes",
    [
        {"rationale": " "},
        {"rationale": ""},
        {"evidence": ()},
        {"action": "settle_claim"},
        {"action": "approve"},
        {"final_outcome": "eligible"},
        {"settlement_authorized": True},
        {"human_approval_required": False},
        {"purpose": "insurance_claim_approval"},
        {"reviewer_id": str(uuid4())},
        {"role": "supervisor"},
        {"requested_evidence": ("claim_form",)},
    ],
)
def test_missing_reason_evidence_or_claim_authority_is_not_a_review_action(
    store: Store, changes: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        revise(demo_decision(store[1], ReviewAction.APPROVE, "invalid"), **changes)


def test_missing_rationale_and_mismatched_evidence_provenance_are_rejected(store: Store) -> None:
    queue, entry, sessions = store
    decision = demo_decision(entry, ReviewAction.APPROVE, "evidence")
    data = decision.model_dump()
    del data["rationale"]
    with pytest.raises(ValidationError):
        ReviewDecision.model_validate(data)
    reference = type(entry.evidence[0]).model_validate(
        {**entry.evidence[0].model_dump(), "record_sha256": "0" * 64}
    )
    with pytest.raises(ReviewError, match=ReviewCode.INVALID):
        queue.decide(sessions["reviewer"], revise(decision, evidence=(reference,)))
    with pytest.raises(ValidationError):
        revise(decision, evidence=(entry.evidence[0], entry.evidence[0]))


@pytest.mark.parametrize("offset", [-20, 7200])
def test_backdated_or_future_actions_do_not_append_events(store: Store, offset: int) -> None:
    queue, entry, sessions = store
    decision = revise(
        demo_decision(entry, ReviewAction.APPROVE, "time"),
        occurred_at=NOW + timedelta(seconds=offset),
    )
    with pytest.raises(ReviewError):
        queue.decide(sessions["reviewer"], decision)
    assert detail_entry(store) == entry


@pytest.mark.parametrize("fault", ["unhashed", "rehash_state", "rehash_actor", "rollback"])
def test_audit_replay_and_private_head_detect_tampering(store: Store, fault: str) -> None:
    queue, entry, sessions = store
    queue.decide(sessions["reviewer"], demo_decision(entry, ReviewAction.APPROVE, "audit"))
    complete = detail_entry(store)
    if fault == "rollback":
        queue._entries[entry.entry_id] = entry
    else:
        data = complete.events[-1].model_dump(mode="json")
        if fault == "unhashed":
            forged = complete.events[-1].model_copy(update={"rationale": "Changed audit text."})
        else:
            if fault == "rehash_state":
                data["after"] = ReviewState.REJECTED.value
            else:
                data["actor"] = sessions["outsider"].principal.model_dump(mode="json")
            data["event_sha256"] = digest({k: v for k, v in data.items() if k != "event_sha256"})
            forged = ReviewEvent.model_validate(data)
        queue._entries[entry.entry_id] = complete.model_copy(
            update={"events": (*complete.events[:-1], forged)}
        )
    with pytest.raises(ReviewError, match=ReviewCode.AUDIT):
        queue.details.get(sessions["reviewer"], entry.entry_id)
    with pytest.raises(ValidationError):
        complete.__setattr__("state", ReviewState.REVIEW)


def test_reassignment_revokes_old_review_access_and_invalidates_old_cas(store: Store) -> None:
    queue, entry, sessions = store
    request = AssignmentRequest(
        request_id=uuid4(),
        entry_id=entry.entry_id,
        claim_id=entry.binding.claim_id,
        expected_review_revision=entry.review_revision,
        assignee_id=sessions["outsider"].principal.principal_id,
        occurred_at=NOW + timedelta(seconds=4),
        rationale="Host replaces the assigned reviewer.",
    )
    receipt = queue.assign(sessions["host"], request)
    assert queue.assign(sessions["host"], request) == receipt
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.details.get(sessions["reviewer"], entry.entry_id)
    assert queue.details.list(sessions["reviewer"]) == ()
    with pytest.raises(ReviewError, match=ReviewCode.CONFLICT):
        queue.decide(
            sessions["outsider"], demo_decision(entry, ReviewAction.APPROVE, "old-revision")
        )


def test_only_host_can_assign_or_report_changed_inputs(store: Store) -> None:
    queue, entry, sessions = store
    assignment = AssignmentRequest(
        request_id=uuid4(),
        entry_id=entry.entry_id,
        claim_id=entry.binding.claim_id,
        expected_review_revision=entry.review_revision,
        assignee_id=sessions["outsider"].principal.principal_id,
        occurred_at=NOW,
        rationale="Synthetic forged assignment.",
    )
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.assign(sessions["reviewer"], assignment)
    invalidation = InvalidationRequest(
        request_id=uuid4(),
        entry_id=entry.entry_id,
        expected_review_revision=entry.review_revision,
        replacement=ReviewBinding.model_validate(
            {**entry.binding.model_dump(), "evidence_sha256": "0" * 64}
        ),
        occurred_at=NOW,
        rationale="Untrusted caller claims replacement evidence.",
    )
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.invalidate(sessions["reviewer"], invalidation)
    with pytest.raises(ValidationError):
        Principal(principal_id=uuid4(), kind=PrincipalKind.MODEL, role=ReviewerRole.SUPERVISOR)


def test_queue_entry_and_event_capacity_fail_before_state_changes(store: Store) -> None:
    queue, entry, sessions = store
    for limits in (ReviewLimits(max_events_per_entry=3), ReviewLimits(max_action_bytes=256)):
        queue.limits = limits
        with pytest.raises(ReviewError, match=ReviewCode.CAPACITY):
            queue.decide(
                sessions["reviewer"], demo_decision(entry, ReviewAction.APPROVE, "capacity")
            )
        assert detail_entry(store) == entry


def test_existing_queue_task_replay_does_not_reset_assignment_or_audit(
    store: Store, sources: Callable[[str], Advisory]
) -> None:
    queue, entry, sessions = store
    repeated = asyncio.run(queue.enqueue(sessions["host"], *sources("valid-v1"), occurred_at=NOW))
    assert repeated == entry and repeated.review_revision == 3
    queue.limits = ReviewLimits(max_entries=1)
    with pytest.raises(ReviewError, match=ReviewCode.CAPACITY):
        asyncio.run(queue.enqueue(sessions["host"], *sources("valid-v2"), occurred_at=NOW))


def test_cross_case_review_detail_and_action_are_isolated(
    sources: Callable[[str], Advisory],
) -> None:
    sessions = demo_sessions()
    queue, first = asyncio.run(demo_queue(*sources("valid-v1"), sessions))
    second = asyncio.run(queue.enqueue(sessions["host"], *sources("valid-v2"), occurred_at=NOW))
    assert second.binding.claim_id != first.binding.claim_id
    assert [e.entry_id for e in queue.details.list(sessions["reviewer"])] == [first.entry_id]
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.details.get(sessions["reviewer"], second.entry_id)
    with pytest.raises(ReviewError, match=ReviewCode.DENIED):
        queue.decide(
            sessions["reviewer"], demo_decision(second, ReviewAction.APPROVE, "cross-case")
        )


def test_rehashed_but_forged_m12_advisory_task_is_not_trusted(
    sources: Callable[[str], Advisory],
) -> None:
    request, grant, checkpoint = sources("valid-v1")
    data = checkpoint.model_dump(mode="json")
    record = data["records"][-1]
    record["step"]["snapshot"]["review_task"]["reason"] = "dependency_unavailable"
    record["output_sha256"] = digest(record["step"]["snapshot"])
    record["record_sha256"] = digest({k: v for k, v in record.items() if k != "record_sha256"})
    forged = Checkpoint.model_validate(data)
    sessions = demo_sessions()
    queue = ReviewQueue(tuple(sessions.values()), clock=lambda: NOW)
    with pytest.raises(ReviewError, match=ReviewCode.INVALID):
        asyncio.run(queue.enqueue(sessions["host"], request, grant, forged, occurred_at=NOW))
    assert queue.details.list(sessions["reviewer"]) == ()


def test_partial_or_blocked_workflow_is_not_an_approvable_advisory(
    sources: Callable[[str], Advisory],
) -> None:
    request, grant, _ = sources("valid-v1")
    partial = asyncio.run(WorkflowRunner().run(request, grant, stop_after=Stage.POLICY))
    sessions = demo_sessions()
    queue = ReviewQueue(tuple(sessions.values()), clock=lambda: NOW)
    for req, authorization, checkpoint in ((request, grant, partial), sources("missing-estimate")):
        with pytest.raises(ReviewError, match=ReviewCode.INVALID):
            asyncio.run(
                queue.enqueue(sessions["host"], req, authorization, checkpoint, occurred_at=NOW)
            )


def test_review_processing_never_invokes_models_or_network(
    store: Store, sources: Callable[[str], Advisory], monkeypatch: pytest.MonkeyPatch
) -> None:
    queue, entry, sessions = store

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("review actions cannot invoke model or network services")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr("claims_ai.agent_tools.execution.assess", forbidden)
    monkeypatch.setattr("claims_ai.workflow.stages.assess", forbidden)
    fresh = ReviewQueue(tuple(sessions.values()), clock=lambda: NOW)
    asyncio.run(fresh.enqueue(sessions["host"], *sources("valid-v1"), occurred_at=NOW))
    queue.decide(sessions["reviewer"], demo_decision(entry, ReviewAction.APPROVE, "no-model"))
    assert list(ALLOWLIST) == ["read_claim_evidence", "read_policy_clauses", "read_rule_findings"]


@pytest.mark.parametrize("fault", ["cross_case", "missing_permission", "changed_content"])
def test_untrusted_source_grants_and_changed_workflow_bytes_fail_before_enqueue(
    sources: Callable[[str], Advisory], fault: str
) -> None:
    request, grant, checkpoint = sources("valid-v1")
    if fault == "cross_case":
        grant = ToolGrant.model_validate({**grant.model_dump(), "claim_id": "NS-CLM-00000000"})
    elif fault == "missing_permission":
        grant = ToolGrant.model_validate({**grant.model_dump(), "permissions": ()})
    else:
        first = request.evidence_inputs[0]
        changed = first.model_copy(
            update={
                "request": first.request.model_copy(update={"content": b"not-the-source-document"})
            }
        )
        request = request.model_copy(
            update={"evidence_inputs": (changed, *request.evidence_inputs[1:])}
        )
    sessions = demo_sessions()
    queue = ReviewQueue(tuple(sessions.values()), clock=lambda: NOW)
    with pytest.raises(ReviewError, match=ReviewCode.INVALID):
        asyncio.run(queue.enqueue(sessions["host"], request, grant, checkpoint, occurred_at=NOW))
    assert queue.details.list(sessions["reviewer"]) == ()


def test_offline_cli_reproduces_review_evidence_and_protects_reference_data(tmp_path: Path) -> None:
    import claims_ai

    assert claims_ai.__file__ is not None
    package_root = str(Path(claims_ai.__file__).resolve().parents[1])
    bootstrap = (
        "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.human_review',run_name='__main__')"
    )
    command = [
        sys.executable,
        "-I",
        "-B",
        "-c",
        bootstrap,
        package_root,
        "--spec-root",
        str(SPEC_ROOT),
    ]
    outputs = [tmp_path / "a.json", tmp_path / "b.json"]
    for output in outputs:
        subprocess.run(
            [*command, "--output", str(output)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            timeout=30,
        )
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    report = json.loads(outputs[0].read_bytes())
    assert report["review_model_calls"] == report["live_model_calls"] == 0
    assert report["autonomous_outcomes"] == report["azure_operations"] == 0
    assert not report["insurance_outcome_authority"]
    assert [r["detail"]["entry"]["state"] for r in report["cases"]] == [
        ReviewState.APPROVED,
        ReviewState.REJECTED,
        ReviewState.APPROVED,
        ReviewState.EVIDENCE,
        ReviewState.STALE,
        ReviewState.REVIEW,
    ]
    for output in [outputs[0], SPEC_ROOT / "m15-must-not-write.json"]:
        result = subprocess.run(
            [*command, "--output", str(output)], cwd=tmp_path, capture_output=True, timeout=30
        )
        assert result.returncode == 1 and not result.stdout and b"Traceback" not in result.stderr
    assert not (SPEC_ROOT / "m15-must-not-write.json").exists()
