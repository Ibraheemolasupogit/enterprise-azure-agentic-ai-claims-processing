"""Real subprocess faults and minimized offline evidence; no external deliveries."""

import asyncio
import signal
import sqlite3
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from pathlib import Path

from claims_ai.models import AssessmentOutcome, Case, CaseState, DecisionAction
from claims_ai.outcomes.contracts import Action, ApprovedInput, Command, OutcomeError
from claims_ai.outcomes.demo import NOW, approved_fixture, command, demo_host, prepared_store
from claims_ai.outcomes.store import OutcomeStore, encoded
from claims_ai.rules.specification import digest
from claims_ai.workflow.__main__ import injected_document


def worker_args(
    approval_file: Path,
    database: Path,
    command_file: Path,
    actor: str,
    fault: str = "none",
    *,
    dispatch: bool = False,
) -> list[str]:
    package = str(Path(__file__).resolve().parents[2])
    return [
        sys.executable,
        "-I",
        "-B",
        "-c",
        "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.outcomes.worker',run_name='__main__')",
        package,
        "--approval",
        str(approval_file),
        "--approval-sha256",
        sha256(approval_file.read_bytes()).hexdigest(),
        "--database",
        str(database),
        "--command",
        str(command_file),
        "--actor",
        actor,
        "--fault",
        fault,
        *(["--dispatch"] if dispatch else []),
    ]


def crash_probe(
    directory: Path, approval: ApprovedInput, point: str, *, delivery: bool = False
) -> dict[str, object]:
    directory.mkdir(mode=0o700)
    approval_file = directory / "host-approved.json"
    approval_file.write_text(encoded(approval))
    approval_file.chmod(0o600)
    database = directory / "case.sqlite3"
    store, host, state = prepared_store(database, approval)
    request = command(Action.DECIDE, "crash-decision", approval, state)
    if delivery:
        request = command(Action.REGISTER, "register", approval)
    path = directory / "request.json"
    path.write_text(encoded(request))
    actor = "host" if delivery else "reviewer"
    before = store.read(host.tokens["host"], request.claim_id)
    killed = subprocess.run(
        worker_args(approval_file, database, path, actor, point, dispatch=delivery),
        capture_output=True,
        timeout=60,
    )
    if killed.returncode != -signal.SIGKILL:
        raise OutcomeError("crash_not_exercised")
    fresh = demo_host((approval,))
    recovered = OutcomeStore(database, fresh.authority, clock=lambda: NOW)
    after = recovered.read(fresh.tokens["host"], request.claim_id)
    committed = point in {"after_commit", "after_delivery_commit"}
    if not delivery and ((after == before) == committed):
        raise OutcomeError("unexpected_crash_boundary")
    replay = subprocess.run(
        worker_args(approval_file, database, path, actor, dispatch=delivery),
        capture_output=True,
        text=True,
        timeout=60,
    )
    duplicate = subprocess.run(
        worker_args(approval_file, database, path, actor, dispatch=delivery),
        capture_output=True,
        text=True,
        timeout=60,
    )
    if replay.returncode or duplicate.returncode or replay.stdout != duplicate.stdout:
        raise OutcomeError("restart_replay_failed")
    with recovered.transaction() as connection:
        states, events = recovered.verify(connection)
        sink_count = connection.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0]
        decisions = connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
    if delivery and sink_count != 1 or not delivery and decisions != 1:
        raise OutcomeError("duplicate_effect")
    return {
        "point": point,
        "subprocess_sigkill_observed": True,
        "committed_before_lost_ack": committed,
        "fresh_process_replay_succeeded": True,
        "duplicate_receipt_equal": True,
        "decisions": decisions,
        "local_sink_receipts": sink_count,
        "audit_events": len(events[request.claim_id]),
        "state": states[request.claim_id].case.state.value,
    }


def offline_report(root: Path) -> dict[str, object]:
    approval = asyncio.run(
        approved_fixture(root, name="m20-evidence", approved_outcome=AssessmentOutcome.ELIGIBLE)
    )
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="m20-outcomes-") as name:
        directory = Path(name)
        store, host, state = prepared_store(directory / "case.sqlite3", approval)
        decision = command(Action.DECIDE, "ordinary-approval", approval, state)
        accepted = store.execute(host.tokens["reviewer"], decision)
        duplicate = store.execute(host.tokens["reviewer"], decision)
        if accepted != duplicate:
            raise OutcomeError("duplicate_receipt_mismatch")
        rows.append(
            {
                "scenario": "explicit_synthetic_human_approval",
                "state": accepted.after.case.state.value,
                "same_duplicate_receipt": True,
                "event_sha256": accepted.event_sha256,
            }
        )
        for actor in ["agent", "mcp", "model", "outsider"]:
            try:
                store.execute(host.tokens[actor], decision)
            except OutcomeError:
                rows.append({"scenario": actor + "_denied", "blocked": True})
            else:
                raise OutcomeError("unauthorized_action_accepted")
        fresh = demo_host((approval,))
        restarted = OutcomeStore(directory / "case.sqlite3", fresh.authority, clock=lambda: NOW)
        try:
            restarted.read(host.tokens["reviewer"], approval.case.claim.claim_id)
        except OutcomeError:
            rows.append({"scenario": "old_credential_after_restart", "blocked": True})
        else:
            raise OutcomeError("old_identity_recovered")
        reopened = restarted.execute(
            fresh.tokens["supervisor"], command(Action.REOPEN, "reopen", approval, accepted.after)
        )
        if reopened.after.case.state != CaseState.VALIDATING:
            raise OutcomeError("revalidation_not_required")
        rows.append({"scenario": "supervisor_reopening", "state": reopened.after.case.state.value})
        for scenario in ["override", "correction"]:
            target = directory / scenario
            target.mkdir(mode=0o700)
            instance, identity, current = prepared_store(target / "case.sqlite3", approval)
            if scenario == "override":
                result = instance.execute(
                    identity.tokens["supervisor"],
                    command(
                        Action.DECIDE,
                        "override",
                        approval,
                        current,
                        actor="supervisor",
                        decision_action=DecisionAction.OVERRIDE,
                        outcome=AssessmentOutcome.INELIGIBLE,
                    ),
                )
            else:
                corrected_request = injected_document(approval.bundle.request)
                replacement = Case(
                    claim=corrected_request.intake.claim,
                    documents=corrected_request.intake.documents,
                    state=CaseState.VALIDATING,
                    revision=current.case.revision + 2,
                )
                correction = Command.model_validate(
                    {
                        **command(Action.REOPEN, "correct", approval, current).model_dump(),
                        "action": Action.CORRECT,
                        "replacement": replacement,
                    }
                )
                result = instance.execute(identity.tokens["reviewer"], correction)
                updated = asyncio.run(
                    approved_fixture(
                        root,
                        name="m20-corrected-explicit-approval",
                        approved_outcome=AssessmentOutcome.UNDETERMINED,
                        parent=result.after.binding,
                        request=corrected_request,
                    )
                )
                rehost = demo_host((approval, updated))
                restored = OutcomeStore(
                    target / "case.sqlite3", rehost.authority, clock=lambda: NOW
                )
                validated = restored.execute(
                    rehost.tokens["host"],
                    command(Action.REVALIDATE, "revalidate-source-bytes", updated, result.after),
                    permit=rehost.authority.permit,
                )
                if validated.after.case.assessment is not None:
                    raise OutcomeError("automatic_assessment_promotion")
                published = restored.execute(
                    rehost.tokens["host"],
                    command(Action.PUBLISH, "separate-publication", updated, validated.after),
                    permit=rehost.authority.permit,
                )
                rows.append(
                    {
                        "scenario": "changed_source_revalidation_then_publication",
                        "states": [
                            result.after.case.state.value,
                            validated.after.case.state.value,
                            published.after.case.state.value,
                        ],
                        "changed_evidence": validated.after.case.evidence != current.case.evidence,
                        "new_assignment_required": published.after.assignments == (),
                    }
                )
            rows.append(
                {
                    "scenario": scenario,
                    "state": result.after.case.state.value,
                    "revision": result.after.case.revision,
                }
            )
        concurrent = directory / "concurrent"
        concurrent.mkdir(mode=0o700)
        race, racers, shared = prepared_store(concurrent / "case.sqlite3", approval)
        requests = [command(Action.DECIDE, "race-" + str(i), approval, shared) for i in range(2)]

        def attempt(request: Command) -> str:
            independent = OutcomeStore(
                concurrent / "case.sqlite3", racers.authority, clock=lambda: NOW
            )
            try:
                independent.execute(racers.tokens["reviewer"], request)
                return "committed"
            except OutcomeError:
                return "conflict"

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = sorted(executor.map(attempt, requests))
        if results != ["committed", "conflict"]:
            raise OutcomeError("concurrency_not_enforced")
        rows.append({"scenario": "independent_connection_stale_race", "results": results})
        with sqlite3.connect(concurrent / "case.sqlite3") as connection:
            connection.execute("DELETE FROM assignments")
        try:
            race.read(racers.tokens["host"], approval.case.claim.claim_id)
        except OutcomeError:
            rows.append({"scenario": "corrupt_projection", "blocked_without_repair": True})
        else:
            raise OutcomeError("tampering_not_rejected")
        crashes = [
            crash_probe(directory / point, approval, point)
            for point in ["after_projection", "after_audit", "before_commit", "after_commit"]
        ]
        crashes.extend(
            crash_probe(directory / point, approval, point, delivery=True)
            for point in ["after_sink", "before_delivery_commit", "after_delivery_commit"]
        )
        pending = directory / "retry"
        pending.mkdir(mode=0o700)
        retry, identity, current = prepared_store(pending / "case.sqlite3", approval)
        event_id = retry.execute(
            identity.tokens["host"],
            command(Action.REGISTER, "register", approval),
            permit=identity.authority.permit,
        ).event_id
        statuses = [
            retry.dispatch(
                identity.tokens["host"], approval.case.claim.claim_id, event_id, unavailable=True
            )
            for _ in range(3)
        ]
        if statuses != ["pending", "pending", "dead"]:
            raise OutcomeError("retry_bound_failed")
        rows.append({"scenario": "bounded_local_sink_failure", "states": statuses})
    values = {
        "report_version": "m20-offline-outcomes-v1",
        "identity": "HOST_VERIFIED_SYNTHETIC_CAPABILITIES_AND_CANONICAL_SESSIONS",
        "assessment_authority": "EXPLICIT_SUPPLIED_SYNTHETIC_TEST_ASSESSMENTS_NOT_M9_PROMOTION",
        "persistence": "LOCAL_SQLITE_FULL_SYNCHRONOUS_DELETE_JOURNAL",
        "cases": rows,
        "crash_probes": crashes,
        "runtime_sha256": approval.bundle.runtime_sha256,
        "real_insurance_authority": False,
        "payments": 0,
        "notifications": 0,
        "azure_operations": 0,
        "live_model_calls": 0,
        "new_agents": 0,
        "external_deliveries": 0,
        "model_context": (
            "Existing M12 simulated advisories are prepared; "
            "replay and commits make no model calls."
        ),
        "limitations": [
            "trusted host/OS and independent approval registry",
            "same-runtime recovery only",
            "not WORM or PostgreSQL/cloud proof",
            "synthetic clocks and identities",
            "M8 failures and M12 timing limitation retained",
            "M19 eight production scopes remain NOT_TESTED",
        ],
    }
    return {**values, "report_sha256": digest(values)}
