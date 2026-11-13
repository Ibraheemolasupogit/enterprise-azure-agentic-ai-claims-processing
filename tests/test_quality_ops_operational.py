"""Actual offline ASGI/SDK, bounded faults, current grants and fresh-process audit recovery."""

import asyncio
import json
import socket
import sqlite3
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest

from claims_ai.quality_ops import __main__ as cli
from claims_ai.quality_ops.evaluation import ScoringNotAuthorised
from claims_ai.quality_ops.runner import evaluate, operational_input_manifest
from claims_ai.quality_ops.telemetry import Telemetry

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/evaluation/m22/v1"
SPEC = ROOT / "data/rules/motor/v1"
OPS = ROOT / "data/operations/m22/v1"


@pytest.fixture(scope="module")
def evidence() -> tuple[dict[str, Any], dict[str, Any]]:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline operation attempted external socket connect")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(socket.socket, "connect", forbidden)
        report, raw = evaluate(CANDIDATES, SPEC, OPS)
    return report, raw


def test_real_operational_controls_and_unapproved_quality_are_distinct(
    evidence: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    report, _ = evidence
    assert report["engineering_status"] == "PASS" and report["harness_complete"]
    assert report["operational_controls"]["counts"] == {"PASS": 17, "FAIL": 0}
    assert report["benchmark_status"] == "PENDING_REVIEW"
    assert report["independent_review_approved"] is report["actual_insurance_authority"] is False
    assert all(r["verdict"] == "NOT_TESTED" for r in report["candidate"]["cases"])
    assert all(
        m["value"] is None and m["status"] == "NOT_TESTED"
        for m in report["independent_quality"].values()
    )
    assert report["azure_operations"] == report["external_model_calls"] == 0
    manifest = report["manifest"]
    assert manifest["review_record_sha256"] is manifest["model_version"] is None
    assert len(manifest["sdk_environment"]) == 39
    assert (
        manifest["operational_inputs"]["files"]["specification.json"]
        == sha256((SPEC / "specification.json").read_bytes()).hexdigest()
    )


def test_operational_input_manifest_binds_actual_fixture_bytes(tmp_path: Path) -> None:
    for name in ("manifest.json", "specification.json", "scenarios.json"):
        (tmp_path / name).write_bytes((SPEC / name).read_bytes())
    first = operational_input_manifest(tmp_path)
    scenarios = tmp_path / "scenarios.json"
    scenarios.write_bytes(scenarios.read_bytes() + b"\n")
    assert operational_input_manifest(tmp_path) != first


def test_acknowledged_audit_survives_failed_export_and_fresh_process_recovery(
    evidence: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    report, _ = evidence
    rows = {r["scenario"]: r for r in report["operational_controls"]["rows"]}
    for name in ("export_failure", "before_commit", "after_commit"):
        row = rows["outcome_" + name]
        assert row["pass"] and row["decisions"] == 1 and row["audit_events"] == 5
        assert row["duplicate_receipt_equal"] and row["w3c_process_link"]
    assert rows["outcome_export_failure"]["export_failure"]
    assert rows["outcome_before_commit"]["sigkill"] and rows["outcome_after_commit"]["sigkill"]
    assert rows["storage_projection_failure_rollback"]["partial_outcome_committed"] is False
    assert rows["revoked_duplicate_after_process_recovery"]["duplicate_allowed"] is False
    assert rows["outbox_retries_survive_restart"]["attempts"] == 3


def test_timeout_retry_stale_and_anchor_controls_have_real_positive_controls(
    evidence: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    report, _ = evidence
    rows = {r["scenario"]: r for r in report["operational_controls"]["rows"]}
    assert rows["workflow_none"]["policy_attempts"] == 1
    for fault in ("timeout", "outage", "retry_once"):
        assert rows["workflow_" + fault]["policy_attempts"] == 2
    assert rows["workflow_retry_once"]["state"] == "awaiting_human_review"
    assert rows["workflow_timeout"]["state"] == rows["workflow_outage"]["state"] == "failed"
    assert rows["stale_revision"]["pass"]
    assert rows["api_ui_current_authority"]["cross_boundary_link"] is True
    assert rows["current_anchor_rollback"]["signature_valid_after"] is True
    assert rows["current_anchor_rollback"]["allowed_after"] is False


def test_actual_sdk_records_do_not_contain_domain_or_identity_payloads(
    evidence: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    report, raw = evidence
    assert len(raw["spans"]) > 60 and len(raw["child_process_spans"]) == 3
    text = json.dumps(raw)
    for forbidden in (
        "NS-CLM-",
        "Bearer ",
        "private-token",
        "synthetic-secret",
        "NARRATIVE=",
        "Authorization",
        "public_key",
        "integrity_key",
        "cookie",
        "tid=",
    ):
        assert forbidden not in text
    assert report["telemetry"]["dropped"] == report["telemetry"]["instrumentation_failures"] == 0
    assert len(report["telemetry"]["metrics"]) <= 64
    assert raw["canonical_report_sha256"] == report["report_sha256"]


def test_live_signals_trigger_owned_alerts_and_backlog_threshold_stays_clear(
    evidence: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    report, _ = evidence
    alerts = {r["alert_id"]: r for r in report["alerts"]}
    assert alerts["OPS-STORAGE"]["status"] == alerts["OPS-EXPORT"]["status"] == "TRIGGERED"
    assert alerts["OPS-REVIEW"]["status"] == "CLEAR"
    assert all(r["positive"] and r["negative"] for r in report["alert_controls"])
    assert all(r["owner"] and r["runbook"] for r in report["alerts"])


def test_independent_scoring_is_rejected_before_running_any_service() -> None:
    with pytest.raises(ScoringNotAuthorised):
        evaluate(CANDIDATES, SPEC, OPS, score_independent=True, review_record={"approved": True})


def test_protected_cli_outputs_fail_before_any_evaluation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("should reject output before evaluation")

    monkeypatch.setattr(cli, "evaluate", forbidden)
    monkeypatch.setattr(
        "sys.argv",
        [
            "m22",
            "--spec-root",
            str(SPEC),
            "--output",
            str(CANDIDATES / "do-not-write.json"),
            "--telemetry-output",
            str(tmp_path / "safe.json"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 3 and not (CANDIDATES / "do-not-write.json").exists()


def test_omitted_operations_are_not_a_complete_engineering_pass() -> None:
    report, _ = evaluate(CANDIDATES, SPEC, OPS, exercise_operations=False)
    assert report["engineering_status"] == "NOT_TESTED" and report["harness_complete"] is False


def test_custom_candidate_root_is_also_protected_before_evaluation(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom = tmp_path / "holdout"
    custom.mkdir()
    output = custom / "new-report.json"

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("protected output must be rejected before evaluation")

    monkeypatch.setattr(cli, "evaluate", forbidden)
    monkeypatch.setattr(
        "sys.argv",
        [
            "m22",
            "--candidate-root",
            str(custom),
            "--output",
            str(output),
            "--telemetry-output",
            str(tmp_path / "safe.json"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 3 and not output.exists()


@pytest.fixture(scope="module")
def approval() -> Any:
    from claims_ai.models import AssessmentOutcome
    from claims_ai.outcomes.demo import approved_fixture

    return asyncio.run(
        approved_fixture(
            SPEC, name="m22-audit-sampling", approved_outcome=AssessmentOutcome.ELIGIBLE
        )
    )


def test_zero_trace_sampling_cannot_remove_business_audit(approval: Any, tmp_path: Path) -> None:
    from claims_ai.outcomes.contracts import Action
    from claims_ai.outcomes.demo import command, prepared_store

    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)
    request = command(Action.DECIDE, "m22-unsampled-decision", approval, state)
    t = Telemetry(sampled=False)
    with t.boundary("outcome.commit", request.correlation_id):
        accepted = store.execute(host.tokens["reviewer"], request)
    with store.transaction() as connection:
        assert connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 5
    assert not t.sink.records and accepted.after.case.decision is not None
    assert t.metrics()
    t.close()


def test_storage_failure_and_export_failure_cannot_acknowledge_partial_outcome(
    approval: Any,
    tmp_path: Path,
) -> None:
    from claims_ai.outcomes.contracts import Action, OutcomeError
    from claims_ai.outcomes.demo import command, prepared_store

    store, host, state = prepared_store(tmp_path / "case.sqlite3", approval)

    def fault(point: str) -> None:
        if point == "after_audit":
            raise sqlite3.OperationalError("sensitive synthetic failure details")

    store.fault = fault
    t = Telemetry()
    t.sink.fail = True
    request = command(Action.DECIDE, "m22-failed-audit", approval, state)
    with pytest.raises(OutcomeError, match="storage_unavailable_or_corrupt"):
        with t.boundary("outcome.commit", request.correlation_id):
            store.execute(host.tokens["reviewer"], request)
    store.fault = lambda point: None
    assert store.read(host.tokens["host"], request.claim_id) == state
    with store.transaction() as connection:
        assert connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM audit").fetchone()[0] == 4
    assert t.sink.export_failures == 1
    t.close()


def test_missing_span_is_detected_in_an_otherwise_successful_workflow(
    evidence: tuple[dict[str, Any], dict[str, Any]],
) -> None:
    from claims_ai.quality_ops.operations import graph_check
    from claims_ai.workflow.__main__ import demo_grant, demo_request

    _, raw = evidence
    correlation = demo_grant(demo_request(SPEC, "valid-v1", "m22-none")).correlation_id
    assert graph_check(raw["spans"], correlation)
    missing = [
        r
        for r in raw["spans"]
        if not (r["correlation_id"] == str(correlation) and r["boundary"] == "policy")
    ]
    assert graph_check(missing, correlation) is False
