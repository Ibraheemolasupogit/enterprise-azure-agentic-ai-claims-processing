"""M20 actual SQLite, independent connections and SIGKILL/restart acceptance evidence."""

import asyncio
import json
import os
import shutil
import sqlite3
import subprocess
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from claims_ai.api.auth import ApiAccess
from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.contracts import Principal, PrincipalKind, ReviewSession
from claims_ai.models import AssessmentOutcome, Case, CaseState, DecisionAction, ReviewerRole
from claims_ai.outcomes.authority import Authority, PublicationPermit
from claims_ai.outcomes.contracts import (
    Action,
    ApprovedInput,
    Command,
    OutcomeError,
    RecoveryBundle,
)
from claims_ai.outcomes.demo import NOW, approved_fixture, command, demo_host, prepared_store
from claims_ai.outcomes.evidence import crash_probe, worker_args
from claims_ai.outcomes.recovery import verify_approval
from claims_ai.outcomes.store import OutcomeStore, decode, encoded

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data/rules/motor/v1"


@pytest.fixture(scope="module")
def approval() -> ApprovedInput:
    return asyncio.run(
        approved_fixture(SPEC, name="m20-tests", approved_outcome=AssessmentOutcome.ELIGIBLE)
    )


@pytest.mark.parametrize(
    "action,outcome,actor",
    [
        (DecisionAction.APPROVE, AssessmentOutcome.ELIGIBLE, "reviewer"),
        (DecisionAction.APPROVE, AssessmentOutcome.ELIGIBLE, "supervisor"),
        (DecisionAction.OVERRIDE, AssessmentOutcome.INELIGIBLE, "supervisor"),
        (DecisionAction.REQUEST_EVIDENCE, None, "reviewer"),
    ],
)
def test_explicit_human_decisions_preserve_assessment_and_durable_receipts(
    tmp_path: Path,
    approval: ApprovedInput,
    action: DecisionAction,
    outcome: AssessmentOutcome | None,
    actor: str,
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    request = command(
        Action.DECIDE,
        "decide",
        approval,
        state,
        actor=actor,
        decision_action=action,
        outcome=outcome,
    )
    event = store.execute(host.tokens[actor], request)
    if action == DecisionAction.REQUEST_EVIDENCE:
        with pytest.raises(OutcomeError, match="assignment_required"):
            store.execute(host.tokens[actor], request)
        store.execute(
            host.tokens["host"],
            command(Action.ASSIGN, "renew-case-assignment", approval, event.after, actor=actor),
        )
    assert store.execute(host.tokens[actor], request) == event
    fresh = demo_host((approval,))
    recovered = OutcomeStore(tmp_path / "case.sqlite3", fresh.authority, clock=lambda: NOW)
    assert recovered.execute(fresh.tokens[actor], request) == event
    assert event.after.case.state == (
        CaseState.AWAITING_EVIDENCE
        if action == DecisionAction.REQUEST_EVIDENCE
        else CaseState.CLOSED
    )
    if outcome is not None:
        assert event.after.case.assessment == approval.assessment
        assert (
            event.after.case.decision is not None and event.after.case.decision.outcome == outcome
        )
    assert not event.after.actual_insurance_authority and not event.after.settlement_authorized
    with recovered.transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM decisions").fetchone() == (1,)
        assert c.execute("SELECT COUNT(*) FROM outbox").fetchone() == (
            6 if action == DecisionAction.REQUEST_EVIDENCE else 5,
        )
    assert not any(
        token.encode() in (tmp_path / "case.sqlite3").read_bytes() for token in host.tokens.values()
    )


@pytest.mark.parametrize("actor", ["host", "outsider", "agent", "mcp", "model"])
def test_only_canonical_assigned_humans_can_decide(
    tmp_path: Path, approval: ApprovedInput, actor: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    with pytest.raises(OutcomeError):
        store.execute(host.tokens[actor], command(Action.DECIDE, "forbidden", approval, state))
    assert store.read(host.tokens["host"], approval.case.claim.claim_id) == state


@pytest.mark.parametrize(
    "kind", ["forged", "revoked", "expired", "copied_session", "cross_case", "restarted"]
)
def test_fresh_identity_and_case_scope_before_duplicate_lookup(
    tmp_path: Path, approval: ApprovedInput, kind: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    request = command(Action.DECIDE, "original", approval, state)
    store.execute(host.tokens["reviewer"], request)
    token = host.tokens["reviewer"]
    if kind == "forged":
        token = "forged"
    elif kind == "revoked":
        host.authenticator.revoke(token)
    elif kind == "expired":
        # Existing host-issued capability expiry implementation, actual timer advanced.
        deadline = host.authenticator._store._last + 901
        host.authenticator._store._timer = lambda: deadline
    elif kind == "copied_session":
        original = host.authority.sessions[
            next(
                k
                for k, v in host.authority.sessions.items()
                if v.principal.role == ReviewerRole.REVIEWER
            )
        ]
        token = host.authenticator.issue(
            ApiAccess(
                ApiScope(principal=original.principal, claim_ids=(request.claim_id,)),
                ReviewSession(original.principal),
            )
        )
    elif kind == "cross_case":
        original = next(
            s for s in host.authority.sessions.values() if s.principal.role == ReviewerRole.REVIEWER
        )
        token = host.authenticator.issue(
            ApiAccess(
                ApiScope(principal=original.principal, claim_ids=("NS-CLM-00000000",)), original
            )
        )
    else:
        fresh = demo_host((approval,))
        store = OutcomeStore(tmp_path / "case.sqlite3", fresh.authority, clock=lambda: NOW)
    with pytest.raises(OutcomeError):
        store.execute(token, request)


@pytest.mark.parametrize(
    "field", ["revision", "case_revision", "case_sha256", "policy_sha256", "assessment_sha256"]
)
def test_exact_bindings_and_optimistic_preconditions(
    tmp_path: Path, approval: ApprovedInput, field: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    request = command(Action.DECIDE, "stale", approval, state)
    assert request.expected is not None
    replacement = 99 if field in {"revision", "case_revision"} else "f" * 64
    raw = request.model_dump(mode="json")
    raw["expected"][field] = replacement
    with pytest.raises(OutcomeError, match="revision_conflict"):
        store.execute(host.tokens["reviewer"], Command.model_validate(raw))
    assert store.read(host.tokens["host"], request.claim_id) == state


@pytest.mark.parametrize(
    "field",
    [
        "rationale",
        "decision_reason",
        "evidence",
        "role",
        "actor",
        "future",
        "timestamp",
        "assessment_id",
        "extra_authority",
    ],
)
def test_missing_rationale_and_forged_decisions_fail_before_mutation(
    tmp_path: Path, approval: ApprovedInput, field: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    raw = command(Action.DECIDE, "invalid", approval, state).model_dump(mode="json")
    if field == "rationale":
        raw["rationale"] = " "
    elif field == "decision_reason":
        raw["decision"]["reason"] = "different reason"
    elif field == "evidence":
        raw["decision"]["evidence_ids"] = ["NS-EVD-00000000"]
    elif field == "role":
        raw["decision"]["role"] = "supervisor"
    elif field == "actor":
        raw["decision"]["reviewer_id"] = str(uuid4())
    elif field == "future":
        raw["occurred_at"] = (NOW + timedelta(days=2)).isoformat()
    elif field == "timestamp":
        raw["decision"]["decided_at"] = (NOW + timedelta(seconds=1)).isoformat()
    elif field == "assessment_id":
        raw["decision"]["assessment_id"] = "NS-ASM-00000000"
    else:
        raw["settlement_authorized"] = True
    with pytest.raises(ValueError):
        store.execute(host.tokens["reviewer"], Command.model_validate(raw))
    assert store.read(host.tokens["host"], state.case.claim.claim_id) == state


@pytest.mark.parametrize(
    "kind",
    ["missing_permit", "copied_permit", "human_publisher", "unknown_approval", "advisory_payload"],
)
def test_publication_requires_independent_explicit_approval(
    tmp_path: Path, approval: ApprovedInput, kind: str
) -> None:
    host = demo_host((approval,))
    store = OutcomeStore(tmp_path / "case.sqlite3", host.authority, create=True, clock=lambda: NOW)
    request = command(Action.REGISTER, "register", approval)
    token = host.tokens["host"]
    permit = host.authority.permit
    if kind == "missing_permit":
        permit = None  # type: ignore[assignment]
    elif kind == "copied_permit":
        permit = PublicationPermit()
    elif kind == "human_publisher":
        token = host.tokens["reviewer"]
    elif kind == "unknown_approval":
        request = request.model_copy(update={"approval_id": uuid4()})
    else:
        raw = request.model_dump(mode="json")
        raw["advisory_recommendation_approved"] = True
        with pytest.raises(ValueError):
            Command.model_validate(raw)
        return
    with pytest.raises(OutcomeError):
        store.execute(token, request, permit=permit)
    with store.transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM audit").fetchone() == (0,)


@pytest.mark.parametrize(
    "kind",
    [
        "input_hash",
        "case_revision",
        "policy",
        "missing_citations",
        "evidence",
        "source_bytes",
        "runtime",
        "missing_bytes",
        "outcome_authority",
    ],
)
def test_approved_inputs_are_not_unverified_or_provisional_promotions(
    approval: ApprovedInput, kind: str
) -> None:
    raw = json.loads(encoded(approval))
    if kind == "input_hash":
        raw["assessment"]["input_sha256"] = "f" * 64
    elif kind == "case_revision":
        raw["assessment"]["case_revision"] += 1
    elif kind == "policy":
        raw["assessment"]["policy"]["version"] = "forged"
    elif kind == "missing_citations":
        raw["assessment"]["citations"] = []
    elif kind == "evidence":
        raw["assessment"]["evidence_ids"] = ["NS-EVD-00000000"]
    elif kind == "source_bytes":
        raw["bundle"]["contents"][0] = "Q09SUlVQVEVE"
    elif kind == "runtime":
        raw["bundle"]["runtime_sha256"] = "f" * 64
    elif kind == "missing_bytes":
        raw["bundle"]["contents"] = []
    else:
        raw["actual_insurance_authority"] = True
    with pytest.raises(ValueError):
        verify_approval(ApprovedInput.model_validate(raw))


@pytest.mark.parametrize("identity", ["producer", "approver"])
def test_separation_of_duties_including_publication_approver(
    tmp_path: Path, approval: ApprovedInput, identity: str
) -> None:
    host = demo_host((approval,))
    forbidden = (
        next(iter(host.authority.sources[approval.approval_id].initial.producer_ids))
        if identity == "producer"
        else approval.approved_by
    )
    session = ReviewSession(
        Principal(principal_id=forbidden, kind=PrincipalKind.HUMAN, role=ReviewerRole.REVIEWER)
    )
    authority = Authority(
        host.authenticator,
        host.authority.host,
        (*host.authority.sessions.values(), session),
        (approval,),
    )
    host.authority = authority
    store = OutcomeStore(tmp_path / "case.sqlite3", authority, create=True, clock=lambda: NOW)
    state = store.execute(
        host.tokens["host"], command(Action.REGISTER, "root", approval), permit=authority.permit
    ).after
    request = command(Action.ASSIGN, "self", approval, state).model_copy(
        update={"assignee_id": forbidden}
    )
    with pytest.raises(OutcomeError, match="assignee_not_authorized"):
        store.execute(host.tokens["host"], request)


@pytest.mark.parametrize("outcome", [AssessmentOutcome.INELIGIBLE, AssessmentOutcome.UNDETERMINED])
def test_adverse_and_ambiguous_assessments_require_supervisor(
    tmp_path: Path, approval: ApprovedInput, outcome: AssessmentOutcome
) -> None:
    approved = approval.model_copy(
        update={"assessment": approval.assessment.model_copy(update={"outcome": outcome})}
    )
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approved)
    with pytest.raises(OutcomeError):
        store.execute(host.tokens["reviewer"], command(Action.DECIDE, "bypass", approved, state))
    if outcome == AssessmentOutcome.UNDETERMINED:
        with pytest.raises(OutcomeError):
            store.execute(
                host.tokens["supervisor"],
                command(
                    Action.DECIDE,
                    "unknown",
                    approved,
                    state,
                    actor="supervisor",
                    outcome=AssessmentOutcome.ELIGIBLE,
                ),
            )
    result = store.execute(
        host.tokens["supervisor"],
        command(
            Action.DECIDE,
            "supervisor",
            approved,
            state,
            actor="supervisor",
            decision_action=DecisionAction.OVERRIDE,
            outcome=AssessmentOutcome.ELIGIBLE,
        ),
    )
    assert result.after.case.state == CaseState.CLOSED


@pytest.mark.parametrize("point", ["after_projection", "after_audit", "before_commit"])
def test_ordinary_transaction_failure_rolls_back_every_projection(
    tmp_path: Path, approval: ApprovedInput, point: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)

    def fault(stage: str) -> None:
        if stage == point:
            raise RuntimeError("bounded injected transaction failure")

    broken = OutcomeStore(tmp_path / "case.sqlite3", host.authority, clock=lambda: NOW, fault=fault)
    with pytest.raises(RuntimeError):
        broken.execute(host.tokens["reviewer"], command(Action.DECIDE, "rollback", approval, state))
    assert store.read(host.tokens["host"], approval.case.claim.claim_id) == state
    with store.transaction() as c:
        assert c.execute("SELECT COUNT(*) FROM decisions").fetchone() == (0,)
        assert c.execute("SELECT COUNT(*) FROM audit").fetchone() == (4,)
        assert c.execute("SELECT COUNT(*) FROM outbox").fetchone() == (4,)


@pytest.mark.parametrize(
    "point", ["after_projection", "after_audit", "before_commit", "after_commit"]
)
def test_real_sigkill_before_and_after_business_commit(
    tmp_path: Path, approval: ApprovedInput, point: str
) -> None:
    report = crash_probe(tmp_path / point, approval, point)
    assert report["subprocess_sigkill_observed"] is True and report["decisions"] == 1
    assert report["audit_events"] == 5


@pytest.mark.parametrize("point", ["after_sink", "before_delivery_commit", "after_delivery_commit"])
def test_real_sigkill_outbox_replay_has_one_local_effect(
    tmp_path: Path, approval: ApprovedInput, point: str
) -> None:
    report = crash_probe(tmp_path / point, approval, point, delivery=True)
    assert report["local_sink_receipts"] == 1 and report["decisions"] == 0


def test_independent_connections_and_processes_cannot_both_win(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    requests = [command(Action.DECIDE, str(i), approval, state) for i in range(2)]

    def attempt(request: Command) -> str:
        independent = OutcomeStore(tmp_path / "case.sqlite3", host.authority, clock=lambda: NOW)
        try:
            return independent.execute(host.tokens["reviewer"], request).after.case.state.value
        except OutcomeError:
            return "conflict"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, requests))
    assert sorted(results) == ["closed", "conflict"]
    # A fresh database is raced by independently initialized host processes too.
    other = tmp_path / "processes"
    other.mkdir(mode=0o700)
    _, _, state = prepared_store(other / "case.sqlite3", approval)
    source = other / "approval.json"
    source.write_text(encoded(approval))
    source.chmod(0o600)
    processes = []
    for i in range(2):
        path = other / f"{i}.json"
        path.write_text(encoded(command(Action.DECIDE, f"process-{i}", approval, state)))
        processes.append(
            subprocess.Popen(
                worker_args(source, other / "case.sqlite3", path, "reviewer"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        )
    results_codes = []
    for process in processes:
        process.communicate(timeout=60)
        results_codes.append(process.returncode)
    assert sorted(results_codes) == [0, 1]


@pytest.mark.parametrize("table", ["cases", "assignments", "outbox", "meta"])
def test_corrupted_projections_and_runtime_are_rejected_without_repair(
    tmp_path: Path, approval: ApprovedInput, table: str
) -> None:
    store, host, _ = prepared_store(tmp_path / "case.sqlite3", approval)
    with sqlite3.connect(tmp_path / "case.sqlite3") as c:
        if table == "cases":
            c.execute("UPDATE cases SET payload='{}'")
        elif table == "assignments":
            c.execute("DELETE FROM assignments")
        elif table == "outbox":
            c.execute("UPDATE outbox SET status='delivered'")
        else:
            c.execute("UPDATE meta SET value='wrong' WHERE key='runtime'")
    with pytest.raises(OutcomeError):
        store.read(host.tokens["host"], approval.case.claim.claim_id)
    with pytest.raises(OutcomeError):
        OutcomeStore(tmp_path / "case.sqlite3", host.authority, clock=lambda: NOW)


@pytest.mark.parametrize("kind", ["schema", "version", "file", "trigger", "extra_table"])
def test_schema_and_file_compatibility_fail_closed(
    tmp_path: Path, approval: ApprovedInput, kind: str
) -> None:
    store, host, _ = prepared_store(tmp_path / "case.sqlite3", approval)
    if kind == "file":
        (tmp_path / "case.sqlite3").write_bytes(b"not a SQLite file")
    else:
        with sqlite3.connect(tmp_path / "case.sqlite3") as c:
            if kind == "schema":
                c.execute("ALTER TABLE cases ADD COLUMN forged TEXT")
            elif kind == "version":
                c.execute("PRAGMA user_version=99")
            elif kind == "trigger":
                c.execute("DROP TRIGGER audit_delete")
            else:
                c.execute("CREATE TABLE forged (secret TEXT)")
    with pytest.raises(OutcomeError):
        store.read(host.tokens["host"], approval.case.claim.claim_id)


@pytest.mark.parametrize(
    "table",
    ["audit", "artifacts", "assessments", "decisions", "receipts", "delivery_events", "deliveries"],
)
def test_append_only_tables_block_update_and_delete(
    tmp_path: Path, approval: ApprovedInput, table: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    decision = store.execute(
        host.tokens["reviewer"], command(Action.DECIDE, "decide", approval, state)
    )
    store.dispatch(host.tokens["host"], approval.case.claim.claim_id, decision.event_id)
    with sqlite3.connect(tmp_path / "case.sqlite3") as c:
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            c.execute(f"DELETE FROM {table}")
        column = c.execute(f"PRAGMA table_info({table})").fetchone()[1]
        with pytest.raises(sqlite3.IntegrityError, match="append_only"):
            c.execute(f"UPDATE {table} SET {column}={column}")


def test_outbox_retry_dead_letter_and_case_isolation(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    event = store.execute(
        host.tokens["host"],
        command(Action.REGISTER, "register", approval),
        permit=host.authority.permit,
    )
    with pytest.raises(OutcomeError):
        store.dispatch(host.tokens["reviewer"], approval.case.claim.claim_id, event.event_id)
    assert [
        store.dispatch(
            host.tokens["host"], approval.case.claim.claim_id, event.event_id, unavailable=True
        )
        for _ in range(4)
    ] == ["pending", "pending", "dead", "dead"]
    assert store.read(host.tokens["host"], approval.case.claim.claim_id) == state


def test_correction_reopening_and_actual_revalidation_are_separate(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    replacement = Case(
        claim=state.case.claim,
        documents=state.case.documents,
        state=CaseState.VALIDATING,
        revision=state.case.revision + 2,
    )
    request = command(Action.REOPEN, "correction", approval, state).model_copy(
        update={"action": Action.CORRECT, "replacement": replacement}
    )
    corrected = store.execute(host.tokens["reviewer"], request).after
    assert (
        corrected.case.assessment is None
        and corrected.case.evidence == ()
        and corrected.assignments == ()
    )
    with pytest.raises(OutcomeError):
        store.execute(
            host.tokens["host"],
            command(Action.PUBLISH, "stale", approval, corrected),
            permit=host.authority.permit,
        )
    new = asyncio.run(
        approved_fixture(
            SPEC,
            name="revalidated",
            approved_outcome=AssessmentOutcome.ELIGIBLE,
            parent=corrected.binding,
        )
    )
    fresh = demo_host((approval, new))
    recovered = OutcomeStore(tmp_path / "case.sqlite3", fresh.authority, clock=lambda: NOW)
    verified = recovered.execute(
        fresh.tokens["host"],
        command(Action.REVALIDATE, "revalidation", new, corrected),
        permit=fresh.authority.permit,
    ).after
    assert verified.case.state == CaseState.ASSESSING and verified.case.assessment is None
    published = recovered.execute(
        fresh.tokens["host"],
        command(Action.PUBLISH, "new-publication", new, verified),
        permit=fresh.authority.permit,
    ).after
    assert (
        published.case.state == CaseState.AWAITING_REVIEW
        and published.case.assessment == new.assessment
    )
    assert published.assignments == ()  # previous assignment never survives changed snapshot


def test_supervisor_reopening_and_external_rollback_anchor(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    copy = tmp_path / "old.sqlite3"
    shutil.copyfile(tmp_path / "case.sqlite3", copy)
    copy.chmod(0o600)
    event = store.execute(host.tokens["reviewer"], command(Action.DECIDE, "close", approval, state))
    with pytest.raises(OutcomeError):
        store.execute(host.tokens["reviewer"], command(Action.REOPEN, "bad", approval, event.after))
    reopened = store.execute(
        host.tokens["supervisor"], command(Action.REOPEN, "good", approval, event.after)
    ).after
    assert reopened.case.state == CaseState.VALIDATING and reopened.case.decision is None
    with pytest.raises(OutcomeError, match="external_head_mismatch"):
        OutcomeStore(
            copy,
            host.authority,
            clock=lambda: NOW,
            expected_heads={approval.case.claim.claim_id: event.event_sha256},
        )


def test_bundle_roundtrip_preserves_original_bytes_and_never_credentials(
    approval: ApprovedInput,
) -> None:
    recovered = decode(RecoveryBundle, encoded(approval.bundle))
    assert recovered == approval.bundle
    assert [b.request.content for b in recovered.request.evidence_inputs] == [
        b.request.content for b in approval.bundle.request.evidence_inputs
    ]
    assert (
        verify_approval(decode(ApprovedInput, encoded(approval))).initial.binding
        == verify_approval(approval).initial.binding
    )


def test_changed_duplicate_is_denied_without_second_event(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    request = command(Action.DECIDE, "close", approval, state)
    store.execute(host.tokens["reviewer"], request)
    changed = request.model_copy(update={"correlation_id": uuid4()})
    with pytest.raises(OutcomeError, match="changed_duplicate"):
        store.execute(host.tokens["reviewer"], changed)


@pytest.mark.parametrize("kind", ["public", "symlink", "hardlink", "existing_create"])
def test_private_storage_and_no_overwrite(
    tmp_path: Path, approval: ApprovedInput, kind: str
) -> None:
    store, host, _ = prepared_store(tmp_path / "case.sqlite3", approval)
    path = tmp_path / "case.sqlite3"
    if kind == "public":
        path.chmod(0o644)
    elif kind == "symlink":
        link = tmp_path / "alias.sqlite3"
        link.symlink_to(path)
        path = link
    elif kind == "hardlink":
        os.link(path, tmp_path / "alias.sqlite3")
    with pytest.raises((OutcomeError, FileExistsError)):
        OutcomeStore(path, host.authority, create=kind == "existing_create", clock=lambda: NOW)


@pytest.mark.parametrize("kind", ["empty", "oversized", "bad_json", "unknown_field", "bad_base64"])
def test_recovery_envelopes_reject_invalid_serialized_inputs(
    approval: ApprovedInput, kind: str
) -> None:
    raw = json.loads(encoded(approval.bundle))
    if kind == "empty":
        raw["contents"] = []
    elif kind == "oversized":
        raw["contents"][0] = "a" * 12000001
    elif kind == "bad_json":
        with pytest.raises(ValueError):
            decode(RecoveryBundle, "{broken")
        return
    elif kind == "unknown_field":
        raw["bearer_token"] = "must-not-be-accepted"
    else:
        raw["contents"][0] = "!!!"
    with pytest.raises(ValueError):
        RecoveryBundle.model_validate(raw)


def test_real_adverse_provisional_context_cannot_be_downgraded_by_publication() -> None:
    with pytest.raises(ValueError, match="unapproved_assessment_binding"):
        candidate = asyncio.run(
            approved_fixture(
                SPEC,
                name="unsafe-downgrade",
                fixture="gradual-wear-exclusion",
                approved_outcome=AssessmentOutcome.ELIGIBLE,
            )
        )
        verify_approval(candidate)
    candidate = asyncio.run(
        approved_fixture(
            SPEC,
            name="supervisor-only",
            fixture="gradual-wear-exclusion",
            approved_outcome=AssessmentOutcome.UNDETERMINED,
        )
    )
    assert verify_approval(candidate).initial.required_reviewer == ReviewerRole.SUPERVISOR


def test_coherently_rehashed_root_forgery_is_rejected_against_independent_approval(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    from claims_ai.dataset.generator import json_bytes
    from claims_ai.rules.specification import digest

    host = demo_host((approval,))
    store = OutcomeStore(tmp_path / "case.sqlite3", host.authority, create=True, clock=lambda: NOW)
    event = store.execute(
        host.tokens["host"],
        command(Action.REGISTER, "root", approval),
        permit=host.authority.permit,
    )
    raw = event.model_dump(mode="json")
    raw["after"]["case"]["claim"]["narrative"] = "FORGED BUT REHASHED"
    raw["event_sha256"] = digest({k: v for k, v in raw.items() if k != "event_sha256"})
    with sqlite3.connect(tmp_path / "case.sqlite3") as c:
        trigger = c.execute("SELECT sql FROM sqlite_master WHERE name='audit_update'").fetchone()[0]
        c.execute("DROP TRIGGER audit_update")
        c.execute("UPDATE audit SET payload=?", (json_bytes(raw).decode(),))
        c.execute(trigger)
        c.execute("UPDATE cases SET payload=?", (json_bytes(raw["after"]).decode(),))
        payload = json_bytes(
            {
                "claim_id": approval.case.claim.claim_id,
                "event_sha256": raw["event_sha256"],
                "purpose": "local_synthetic_audit_projection_only",
            }
        ).decode()
        c.execute("UPDATE outbox SET payload=?", (payload,))
    with pytest.raises(OutcomeError, match="audit_semantics_mismatch"):
        store.read(host.tokens["host"], approval.case.claim.claim_id)


@pytest.mark.parametrize("change", ["role", "case_scope", "session"])
def test_reissued_identity_does_not_override_durable_assignment(
    tmp_path: Path, approval: ApprovedInput, change: str
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    human = next(
        s for s in host.authority.sessions.values() if s.principal.role == ReviewerRole.REVIEWER
    )
    principal = human.principal
    if change == "role":
        principal = principal.model_copy(update={"role": ReviewerRole.SUPERVISOR})
    access = ApiAccess(
        ApiScope(
            principal=principal,
            claim_ids=() if change == "case_scope" else (approval.case.claim.claim_id,),
        ),
        ReviewSession(principal) if change != "case_scope" else human,
    )
    token = host.authenticator.issue(access)
    with pytest.raises(OutcomeError):
        store.execute(token, command(Action.DECIDE, "forged-current-access", approval, state))


def test_changed_document_bytes_require_fresh_m12_verification_before_publication(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    from claims_ai.workflow.__main__ import injected_document

    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    corrected_request = injected_document(approval.bundle.request)
    assert corrected_request.intake.documents != state.case.documents
    replacement = Case(
        claim=corrected_request.intake.claim,
        documents=corrected_request.intake.documents,
        state=CaseState.VALIDATING,
        revision=state.case.revision + 2,
    )
    request = command(Action.REOPEN, "actual-correction", approval, state).model_copy(
        update={"action": Action.CORRECT, "replacement": replacement}
    )
    corrected = store.execute(host.tokens["reviewer"], request).after
    assert corrected.case.evidence == () and corrected.case.assessment is None
    new = asyncio.run(
        approved_fixture(
            SPEC,
            name="changed-document-approved",
            approved_outcome=AssessmentOutcome.UNDETERMINED,
            parent=corrected.binding,
            request=corrected_request,
        )
    )
    fresh = demo_host((approval, new))
    restored = OutcomeStore(tmp_path / "case.sqlite3", fresh.authority, clock=lambda: NOW)
    verified = restored.execute(
        fresh.tokens["host"],
        command(Action.REVALIDATE, "verify-new-bytes", new, corrected),
        permit=fresh.authority.permit,
    ).after
    assert verified.case.evidence and verified.case.evidence != state.case.evidence
    assert verified.case.state == CaseState.ASSESSING and verified.case.assessment is None
    published = restored.execute(
        fresh.tokens["host"],
        command(Action.PUBLISH, "publish-separate", new, verified),
        permit=fresh.authority.permit,
    ).after
    assert published.case.assessment is not None and published.case.assessment.requires_supervisor
    assert published.case.claim.narrative == corrected_request.intake.claim.narrative
    assert published.case.decision is None and not published.settlement_authorized


def test_two_real_cases_do_not_leak_through_store_reads_or_mutations(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    second = asyncio.run(
        approved_fixture(
            SPEC,
            name="second-case",
            fixture="valid-v2",
            approved_outcome=AssessmentOutcome.ELIGIBLE,
        )
    )
    host = demo_host((approval, second))
    store, _, state = prepared_store(tmp_path / "case.sqlite3", approval, host)
    store.execute(
        host.tokens["host"],
        command(Action.REGISTER, "second-root", second),
        permit=host.authority.permit,
    )
    from claims_ai.human_review.__main__ import demo_sessions

    reviewer = host.authority.sessions[demo_sessions()["reviewer"].principal.principal_id]
    token = host.authenticator.issue(
        ApiAccess(
            ApiScope(principal=reviewer.principal, claim_ids=(approval.case.claim.claim_id,)),
            reviewer,
        )
    )
    with pytest.raises(OutcomeError, match="access_denied"):
        store.read(token, second.case.claim.claim_id)
    with pytest.raises(OutcomeError, match="access_denied"):
        store.execute(
            token,
            command(
                Action.ASSIGN,
                "foreign",
                second,
                store.read(host.tokens["host"], second.case.claim.claim_id),
            ),
        )
    assert store.read(host.tokens["host"], approval.case.claim.claim_id) == state


def test_retry_budget_is_not_reset_by_fresh_host_and_connections(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, _ = prepared_store(tmp_path / "case.sqlite3", approval)
    event = store.execute(
        host.tokens["host"],
        command(Action.REGISTER, "register", approval),
        permit=host.authority.permit,
    )
    assert (
        store.dispatch(
            host.tokens["host"], approval.case.claim.claim_id, event.event_id, unavailable=True
        )
        == "pending"
    )
    fresh = demo_host((approval,))
    restarted = OutcomeStore(tmp_path / "case.sqlite3", fresh.authority, clock=lambda: NOW)
    assert (
        restarted.dispatch(
            fresh.tokens["host"], approval.case.claim.claim_id, event.event_id, unavailable=True
        )
        == "pending"
    )
    assert (
        restarted.dispatch(
            fresh.tokens["host"], approval.case.claim.claim_id, event.event_id, unavailable=True
        )
        == "dead"
    )
    assert (
        restarted.dispatch(fresh.tokens["host"], approval.case.claim.claim_id, event.event_id)
        == "dead"
    )


def test_reassignment_revokes_previous_canonical_human(
    tmp_path: Path, approval: ApprovedInput
) -> None:
    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    replaced = store.execute(
        host.tokens["host"],
        command(Action.ASSIGN, "replace-reviewer", approval, state, actor="outsider"),
    ).after
    with pytest.raises(OutcomeError, match="assignment_required"):
        store.execute(
            host.tokens["reviewer"], command(Action.DECIDE, "old-assignee", approval, replaced)
        )
    accepted = store.execute(
        host.tokens["outsider"],
        command(Action.DECIDE, "new-assignee", approval, replaced, actor="outsider"),
    )
    assert accepted.after.case.state == CaseState.CLOSED


@pytest.mark.parametrize("revocation", ["token", "key"])
def test_existing_m18_signed_verification_is_rechecked_before_durable_duplicate(
    tmp_path: Path, approval: ApprovedInput, revocation: str
) -> None:
    from claims_ai.identity.adapters import VerifiedCapabilities
    from claims_ai.identity.contracts import API_AUDIENCE, IdentityRole, VerificationPolicy
    from claims_ai.identity.keys import LocalKeyRing
    from claims_ai.identity.verification import SyntheticTokenVerifier, issue

    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    from claims_ai.human_review.__main__ import demo_sessions

    session = host.authority.sessions[demo_sessions()["reviewer"].principal.principal_id]
    epoch = 1800000000
    keys = LocalKeyRing(clock=lambda: epoch)
    policy = VerificationPolicy(
        audience=API_AUDIENCE,
        tenant_id=uuid4(),
        application_id=uuid4(),
        subject=session.principal.principal_id,
        role=IdentityRole.REVIEWER,
    )
    verifier = SyntheticTokenVerifier(policy, keys, clock=lambda: epoch)
    token_id = uuid4()
    signed = issue(keys, policy, (approval.case.claim.claim_id,), now=epoch, token_id=token_id)
    capabilities = VerifiedCapabilities()
    opaque = capabilities.issue(
        ApiAccess(
            ApiScope(principal=session.principal, claim_ids=(approval.case.claim.claim_id,)),
            session,
        ),
        signed,
        verifier,
    )
    authority = Authority(
        capabilities, host.authority.host, tuple(host.authority.sessions.values()), (approval,)
    )
    guarded = OutcomeStore(tmp_path / "case.sqlite3", authority, clock=lambda: NOW)
    request = command(Action.DECIDE, "signed-human", approval, state)
    accepted = guarded.execute(opaque, request)
    assert accepted.after.case.state == CaseState.CLOSED
    if revocation == "token":
        verifier.revoke_token(token_id)
    else:
        previous = keys.current
        keys.rotate()
        keys.retire(previous)
    with pytest.raises(OutcomeError, match="access_denied"):
        guarded.execute(opaque, request)
    assert signed.encode() not in (tmp_path / "case.sqlite3").read_bytes()
