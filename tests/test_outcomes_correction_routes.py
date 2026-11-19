"""M25 P3: M20 correction from a stored VALIDATING case (approved Option E1).

E1 routes VALIDATING through the existing AWAITING_EVIDENCE transitions, as M20 already
does for ASSESSING. These tests use temporary SQLite stores created here; no historical
store, checkpoint or recorded evidence is opened, replayed or migrated.
"""

import asyncio
import sqlite3
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from claims_ai.api.auth import ApiAccess, SyntheticAuthenticator
from claims_ai.api.contracts import ApiScope
from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.__main__ import demo_sessions
from claims_ai.human_review.contracts import Principal, PrincipalKind, ReviewSession
from claims_ai.lifecycle import ALLOWED_TRANSITIONS
from claims_ai.models import AssessmentOutcome, Case, CaseState, DecisionAction, ReviewerRole
from claims_ai.outcomes.authority import Authority
from claims_ai.outcomes.contracts import (
    Action,
    ApprovedInput,
    Assignment,
    AuditEvent,
    Command,
    OutcomeError,
    StoredCase,
    input_hash,
)
from claims_ai.outcomes.demo import (
    NOW,
    DemoHost,
    approved_fixture,
    command,
    demo_host,
    prepared_store,
)
from claims_ai.outcomes.reducer import reduce
from claims_ai.outcomes.store import OutcomeStore
from claims_ai.rules.specification import digest
from claims_ai.workflow.__main__ import injected_document

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data/rules/motor/v1"
LATER = NOW + timedelta(days=1)  # Same host clock prepared_store uses.


@pytest.fixture(scope="module")
def approval() -> ApprovedInput:
    return asyncio.run(
        approved_fixture(SPEC, name="m25-p3-tests", approved_outcome=AssessmentOutcome.ELIGIBLE)
    )


def correction(name: str, approval: ApprovedInput, state: StoredCase, replacement: Case) -> Command:
    return Command.model_validate(
        {
            **command(Action.REOPEN, name, approval, state).model_dump(),
            "action": Action.CORRECT,
            "replacement": replacement,
        }
    )


def replacement(state: StoredCase, offset: int, source: Case | None = None) -> Case:
    base = source or state.case
    return Case(
        claim=base.claim,
        documents=base.documents,
        state=CaseState.VALIDATING,
        revision=state.case.revision + offset,
    )


def changed_case(approval: ApprovedInput) -> tuple[Any, Case]:
    request = injected_document(approval.bundle.request)
    case = Case(claim=request.intake.claim, documents=request.intake.documents)
    assert case.documents != approval.case.documents  # Genuinely changed bytes/narrative.
    return request, case


def assign(
    store: OutcomeStore, host: DemoHost, approval: ApprovedInput, state: StoredCase, *actors: str
) -> StoredCase:
    for actor in actors:
        state = store.execute(
            host.tokens["host"],
            command(
                Action.ASSIGN, f"assign-{actor}-{state.revision}", approval, state, actor=actor
            ),
            permit=host.authority.permit,
        ).after
    return state


def closed_and_reopened(
    path: Path, approval: ApprovedInput, host: DemoHost | None = None, **decide: Any
) -> tuple[OutcomeStore, DemoHost, StoredCase, StoredCase]:
    store, host, state = prepared_store(path, approval, host)
    actor = decide.pop("actor", "reviewer")
    closed = store.execute(
        host.tokens[actor], command(Action.DECIDE, "close", approval, state, actor=actor, **decide)
    ).after
    assert closed.case.state == CaseState.CLOSED
    reopened = store.execute(
        host.tokens["supervisor"], command(Action.REOPEN, "reopen", approval, closed)
    ).after
    assert reopened.case.state == CaseState.VALIDATING and reopened.assignments == ()
    return store, host, closed, reopened


def route(event: AuditEvent) -> list[tuple[CaseState, CaseState]]:
    return [(t.previous.state, t.current.state) for t in event.transitions]


# --- Positive routes ----------------------------------------------------------------


def test_reopened_closed_case_can_be_corrected_and_independently_revalidated(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    path = tmp_path / "case.sqlite3"
    store, host, closed, reopened = closed_and_reopened(path, approval)
    ready = assign(store, host, approval, reopened, "reviewer")
    request, changed = changed_case(approval)
    event = store.execute(
        host.tokens["reviewer"],
        correction("correct-reopened", approval, ready, replacement(ready, 3, changed)),
    )
    corrected = event.after
    assert route(event) == [
        (CaseState.VALIDATING, CaseState.AWAITING_EVIDENCE),
        (CaseState.AWAITING_EVIDENCE, CaseState.VALIDATING),
    ]
    assert corrected.case.state == CaseState.VALIDATING
    assert corrected.case.revision == ready.case.revision + 3
    assert corrected.case.documents == changed.documents
    assert corrected.case.evidence == () and corrected.case.policy is None
    assert corrected.case.assessment is None and corrected.case.decision is None
    assert corrected.assignments == () and corrected.approval_id == closed.approval_id
    # Prior closure decision remains in immutable history.
    with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as c:
        assert c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
    new = asyncio.run(
        approved_fixture(
            SPEC,
            name="m25-p3-reopened-corrected",
            approved_outcome=AssessmentOutcome.UNDETERMINED,
            parent=corrected.binding,
            request=request,
        )
    )
    fresh = demo_host((approval, new))
    restored = OutcomeStore(path, fresh.authority, clock=lambda: LATER)
    verified = restored.execute(
        fresh.tokens["host"],
        command(Action.REVALIDATE, "revalidate-corrected", new, corrected),
        permit=fresh.authority.permit,
    ).after
    assert verified.case.state == CaseState.ASSESSING and verified.case.assessment is None
    assert verified.case.evidence and verified.case.claim == changed.claim
    published = restored.execute(
        fresh.tokens["host"],
        command(Action.PUBLISH, "publish-corrected", new, verified),
        permit=fresh.authority.permit,
    ).after
    assert published.case.state == CaseState.AWAITING_REVIEW
    assert published.assignments == () and published.case.decision is None


def test_chained_correction_invalidates_pending_approval(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    path = tmp_path / "case.sqlite3"
    store, host, state = prepared_store(path, approval)
    request, changed = changed_case(approval)
    first = store.execute(
        host.tokens["reviewer"],
        correction("first", approval, state, replacement(state, 2, changed)),
    )
    assert route(first) == [(CaseState.AWAITING_REVIEW, CaseState.VALIDATING)]  # Unchanged.
    pending = asyncio.run(
        approved_fixture(
            SPEC,
            name="m25-p3-pending-first",
            approved_outcome=AssessmentOutcome.UNDETERMINED,
            parent=first.after.binding,
            request=request,
        )
    )
    ready = assign(store, host, approval, first.after, "reviewer")
    second = store.execute(
        host.tokens["reviewer"],
        correction("second", approval, ready, replacement(ready, 3, approval.case)),
    )
    assert second.after.case.state == CaseState.VALIDATING
    assert second.after.case.documents == approval.case.documents
    rehost = demo_host((approval, pending))
    restored = OutcomeStore(path, rehost.authority, clock=lambda: LATER)
    with pytest.raises(OutcomeError, match="revalidation_binding_required"):
        restored.execute(
            rehost.tokens["host"],
            command(Action.REVALIDATE, "stale-approval", pending, second.after),
            permit=rehost.authority.permit,
        )
    assert restored.read(rehost.tokens["host"], approval.case.claim.claim_id) == second.after


def test_existing_assessing_and_review_routes_are_unchanged(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    host = demo_host((approval,))
    store = OutcomeStore(
        tmp_path / "case.sqlite3", host.authority, create=True, clock=lambda: LATER
    )
    registered = store.execute(
        host.tokens["host"],
        command(Action.REGISTER, "register", approval),
        permit=host.authority.permit,
    ).after
    assert registered.case.state == CaseState.ASSESSING
    ready = assign(store, host, approval, registered, "reviewer")
    event = store.execute(
        host.tokens["reviewer"],
        correction("from-assessing", approval, ready, replacement(ready, 3)),
    )
    assert route(event) == [
        (CaseState.ASSESSING, CaseState.AWAITING_EVIDENCE),
        (CaseState.AWAITING_EVIDENCE, CaseState.VALIDATING),
    ]


# --- Controls that must still refuse ------------------------------------------------


def test_existing_controls_still_refuse_around_reopened_correction(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, closed, reopened = closed_and_reopened(tmp_path / "case.sqlite3", approval)
    claim_id = approval.case.claim.claim_id
    good = replacement(reopened, 3)

    def refused(token: str, request: Command, code: str) -> None:
        before = store.read(host.tokens["host"], claim_id)
        with pytest.raises(OutcomeError, match=code):
            store.execute(host.tokens[token], request)
        assert store.read(host.tokens["host"], claim_id) == before  # No partial write.

    # Closed cases still need supervisor reopening; reviewers cannot reopen.
    other_store, other_host, other_state = prepared_store(tmp_path / "other.sqlite3", approval)
    other_closed = other_store.execute(
        other_host.tokens["reviewer"], command(Action.DECIDE, "close", approval, other_state)
    ).after
    with pytest.raises(OutcomeError, match="closed_case_requires_reopening"):
        other_store.execute(
            other_host.tokens["reviewer"],
            correction("closed", approval, other_closed, replacement(other_closed, 1)),
        )
    with pytest.raises(OutcomeError, match="supervisor_reopening_required"):
        other_store.execute(
            other_host.tokens["reviewer"], command(Action.REOPEN, "bad", approval, other_closed)
        )
    assert other_store.read(other_host.tokens["host"], claim_id) == other_closed

    # Reopening cleared assignments: no human may correct before a fresh host assignment.
    for actor in ("reviewer", "supervisor", "outsider"):
        refused(actor, correction(f"unassigned-{actor}", approval, reopened, good), "assignment")
    for actor in ("agent", "mcp", "model"):
        with pytest.raises(OutcomeError, match="access_denied"):
            store.execute(host.tokens[actor], correction(f"bot-{actor}", approval, reopened, good))
    with pytest.raises(OutcomeError, match="operation_not_authorized"):
        store.execute(host.tokens["host"], correction("host", approval, reopened, good))

    ready = assign(store, host, approval, reopened, "reviewer")
    fresh_good = replacement(ready, 3)
    # Assigning the reviewer grants nothing to other humans.
    refused("outsider", correction("outsider", approval, ready, fresh_good), "assignment")
    # Replacement revision must follow both recorded transitions exactly.
    for offset in (1, 2, 4):
        refused(
            "reviewer",
            correction(f"revision-{offset}", approval, ready, replacement(ready, offset)),
            "invalid_correction",
        )
    # Replacements cannot carry admitted evidence, policy or another policy ID.
    carried = Case.model_validate(
        {
            **closed.case.model_dump(),
            "state": "validating",
            "revision": ready.case.revision + 3,
            "assessment": None,
            "decision": None,
        }
    )
    refused("reviewer", correction("carried", approval, ready, carried), "invalid_correction")
    other_policy = Case(
        claim=ready.case.claim.model_copy(update={"policy_id": "NS-POL-99999999"}),
        documents=ready.case.documents,
        state=CaseState.VALIDATING,
        revision=ready.case.revision + 3,
    )
    refused("reviewer", correction("policy", approval, ready, other_policy), "invalid_correction")
    # Stale bindings are rejected.
    refused("reviewer", correction("stale", approval, reopened, fresh_good), "revision_conflict")

    request = correction("accepted", approval, ready, fresh_good)
    accepted = store.execute(host.tokens["reviewer"], request)
    # Documented M20 rule: current assignment is checked before duplicate-receipt lookup,
    # and the correction cleared assignments, so even an identical replay is refused.
    with pytest.raises(OutcomeError, match="assignment_required"):
        store.execute(host.tokens["reviewer"], request)
    assign(store, host, approval, accepted.after, "reviewer")
    assert store.execute(host.tokens["reviewer"], request) == accepted  # Original receipt.
    changed = correction(
        "accepted", approval, ready, replacement(ready, 3, changed_case(approval)[1])
    )
    with pytest.raises(OutcomeError, match="changed_duplicate"):
        store.execute(host.tokens["reviewer"], changed)


def test_supervisor_required_assessment_still_requires_supervisor_correction(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    adverse = approval.model_copy(
        update={
            "assessment": approval.assessment.model_copy(
                update={"outcome": AssessmentOutcome.INELIGIBLE}
            )
        }
    )
    store, host, _, reopened = closed_and_reopened(
        tmp_path / "case.sqlite3",
        adverse,
        actor="supervisor",
        decision_action=DecisionAction.OVERRIDE,
        outcome=AssessmentOutcome.ELIGIBLE,
    )
    ready = assign(store, host, adverse, reopened, "reviewer", "supervisor")
    with pytest.raises(OutcomeError, match="supervisor_required"):
        store.execute(
            host.tokens["reviewer"], correction("reviewer", adverse, ready, replacement(ready, 3))
        )
    done = store.execute(
        host.tokens["supervisor"], correction("supervisor", adverse, ready, replacement(ready, 3))
    )
    assert done.after.case.state == CaseState.VALIDATING


def host_with_forbidden(approval: ApprovedInput) -> tuple[DemoHost, Principal]:
    """Demo host plus a human session for the approval's own approver (self-review)."""
    sessions = dict(demo_sessions())
    forbidden = Principal(
        principal_id=approval.approved_by, kind=PrincipalKind.HUMAN, role=ReviewerRole.REVIEWER
    )
    sessions["approver"] = ReviewSession(forbidden)
    auth = SyntheticAuthenticator()
    claims = (approval.case.claim.claim_id,)
    tokens = {
        name: auth.issue(
            ApiAccess(
                ApiScope(principal=s.principal, claim_ids=claims),
                s if s.principal.kind == PrincipalKind.HUMAN else None,
            )
        )
        for name, s in sessions.items()
    }
    authority = Authority(
        auth,
        sessions["host"].principal,
        tuple(s for s in sessions.values() if s.principal.kind == PrincipalKind.HUMAN),
        (approval,),
    )
    return DemoHost(authority, auth, tokens), forbidden


def test_self_review_principal_cannot_be_assigned_or_correct(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    host, forbidden = host_with_forbidden(approval)
    store, host, _, reopened = closed_and_reopened(tmp_path / "case.sqlite3", approval, host)
    assign_forbidden = Command.model_validate(
        {
            **command(Action.ASSIGN, "assign-approver", approval, reopened).model_dump(),
            "assignee_id": forbidden.principal_id,
        }
    )
    with pytest.raises(OutcomeError, match="assignee_not_authorized"):
        store.execute(host.tokens["host"], assign_forbidden, permit=host.authority.permit)
    # Adversarial: a forged in-memory state injecting the forbidden assignment is still
    # refused by the reducer's self-review guard. Nothing is written.
    forged = StoredCase.model_validate(
        {
            **reopened.model_dump(),
            "assignments": (
                Assignment(
                    principal=forbidden,
                    input_sha256=input_hash(reopened.case),
                    assessment_sha256=reopened.binding.assessment_sha256,
                ),
            ),
        }
    )
    request = correction("approver", approval, forged, replacement(forged, 3))
    with pytest.raises(OutcomeError, match="self_review_forbidden"):
        reduce(host.authority, forged, request, forbidden)


# --- Audit integrity and lifecycle contract -----------------------------------------


def test_correction_audit_replays_and_detects_rehashed_route_forgery(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    path = tmp_path / "case.sqlite3"
    store, host, _, reopened = closed_and_reopened(path, approval)
    ready = assign(store, host, approval, reopened, "reviewer")
    event = store.execute(
        host.tokens["reviewer"], correction("audited", approval, ready, replacement(ready, 3))
    )
    claim_id = approval.case.claim.claim_id
    restarted = OutcomeStore(path, host.authority, clock=lambda: LATER)
    assert restarted.read(host.tokens["host"], claim_id) == event.after  # Full replay.
    raw = event.model_dump(mode="json")
    raw["transitions"] = raw["transitions"][1:]  # Hide the invalidation hop, then rehash.
    raw["event_sha256"] = digest({k: v for k, v in raw.items() if k != "event_sha256"})
    with sqlite3.connect(path) as c:
        trigger = c.execute("SELECT sql FROM sqlite_master WHERE name='audit_update'").fetchone()[0]
        c.execute("DROP TRIGGER audit_update")
        c.execute(
            "UPDATE audit SET payload=? WHERE event_id=?",
            (json_bytes(raw).decode(), str(event.event_id)),
        )
        c.execute(trigger)
    with pytest.raises(OutcomeError, match="audit_semantics_mismatch"):
        restarted.read(host.tokens["host"], claim_id)


def test_lifecycle_transition_table_is_unchanged() -> None:
    s = CaseState
    assert dict(ALLOWED_TRANSITIONS) == {
        s.RECEIVED: {s.VALIDATING},
        s.VALIDATING: {s.EXTRACTING, s.AWAITING_EVIDENCE, s.QUARANTINED, s.PROCESSING_FAILED},
        s.EXTRACTING: {s.ASSESSING, s.AWAITING_EVIDENCE, s.QUARANTINED, s.PROCESSING_FAILED},
        s.ASSESSING: {s.AWAITING_REVIEW, s.AWAITING_EVIDENCE, s.QUARANTINED, s.PROCESSING_FAILED},
        s.AWAITING_REVIEW: {s.CLOSED, s.AWAITING_EVIDENCE, s.VALIDATING},
        s.AWAITING_EVIDENCE: {s.VALIDATING},
        s.QUARANTINED: {s.VALIDATING},
        s.PROCESSING_FAILED: {s.VALIDATING},
        s.CLOSED: {s.VALIDATING},
    }
    assert s.VALIDATING not in ALLOWED_TRANSITIONS[s.VALIDATING]  # E1 adds no self-loop.
    assert AuditEvent.model_fields["transitions"].metadata[0].max_length == 2
