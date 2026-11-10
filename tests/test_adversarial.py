"""Runtime evaluation integrity; remediation preserves honest outcomes and historical evidence."""

import json
import socket
import subprocess
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from claims_ai.adversarial import runner
from claims_ai.adversarial.application import observed
from claims_ai.adversarial.contracts import (
    AttackCase,
    CaseResult,
    Criterion,
    Observation,
    Target,
    Verdict,
    score,
)
from claims_ai.adversarial.fixtures import load_catalog
from claims_ai.adversarial.identity import identity_probe
from claims_ai.adversarial.runtime import RuntimeHarness
from claims_ai.rules.specification import digest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data/security/adversarial/v1"
SPEC = ROOT / "data/rules/motor/v1"
CATALOG = load_catalog(FIXTURES)
KNOWN_UNTESTED = {f"ADV-PRODUCTION-{index:02d}" for index in range(1, 9)}


@pytest.fixture(scope="module")
def report() -> dict[str, Any]:
    return runner.evaluate(FIXTURES, SPEC)


@pytest.mark.parametrize("case_id", [case.case_id for case in CATALOG.cases])
def test_authored_attack_runs_real_boundary_with_explicit_expected_verdict(
    report: dict[str, Any], case_id: str
) -> None:
    row = next(row for row in report["cases"] if row["case"]["case_id"] == case_id)
    result = CaseResult.model_validate_json(json.dumps(row))
    expected = Verdict.NOT_TESTED if case_id in KNOWN_UNTESTED else Verdict.PASS
    assert result.verdict == expected
    assert not result.observed.harness_error
    assert result.case.control and result.case.trust_boundary and result.case.expected_behavior
    if expected == Verdict.NOT_TESTED:
        assert result.observed.execution == "NOT_EXECUTED" and result.observed.unavailable_reason
    else:
        assert result.observed.execution != "NOT_EXECUTED" and result.observed.facts


def test_complete_evaluation_counts_are_not_a_security_readiness_claim(
    report: dict[str, Any],
) -> None:
    assert report["counts"] == {"PASS": 80, "FAIL": 0, "NOT_TESTED": 8}
    assert report["case_count"] == 88 and report["harness_complete"] is True
    assert (
        report["network_attempts"] == report["azure_operations"] == report["live_model_calls"] == 0
    )
    assert report["operational_outcomes_observed"] is False
    assert report["semantic_live_model_resistance"] == "NOT_TESTED"
    assert report["report_sha256"] == digest(
        {key: value for key, value in report.items() if key != "report_sha256"}
    )
    assert report["m8_historical_failures_preserved"] == ["Q-007", "Q-012", "Q-015", "Q-029"]


def test_consistent_mcp_payload_tampering_is_reported_not_hidden(report: dict[str, Any]) -> None:
    row = next(row for row in report["cases"] if row["case"]["case_id"] == "ADV-MCP-09")
    assert row["verdict"] == "PASS"
    assert row["observed"]["execution"] == "HOST_INJECTED_RUNTIME_GUARDS"
    assert row["observed"]["facts"] == {
        "canonical_sdk_response": True,
        "payload_returned": False,
        "tamper_rejected": True,
    }
    assert row["unmet_criteria"] == []
    mismatch = next(row for row in report["cases"] if row["case"]["attack"] == "text_mismatch")
    assert mismatch["verdict"] == "PASS" and mismatch["observed"]["facts"]["tamper_rejected"]


def test_all_input_injection_surfaces_are_real_data_not_live_model_evidence(
    report: dict[str, Any],
) -> None:
    content = [row for row in report["cases"] if row["case"]["target"] == "content"]
    assert {
        "note",
        "document",
        "policy",
        "workflow_document",
        "extract_forge",
        "source_tamper",
    } <= {row["case"]["attack"] for row in content}
    for row in content:
        if row["case"]["attack"] in {"document", "policy"}:
            assert row["observed"]["facts"]["payload_in_packet"] is True
            assert row["observed"]["facts"]["instructions_unchanged"] is True
            assert row["observed"]["execution"] == "SIMULATED_MODEL_RUNTIME_GUARDS"
        assert row["verdict"] == "PASS"
    service = next(row for row in report["cases"] if row["case"]["attack"] == "service_payload")
    assert service["observed"]["facts"]["service_called"] is True
    assert service["observed"]["facts"]["code"] == "invalid_service_result"


def test_positive_controls_prevent_blanket_denial_false_passes(report: dict[str, Any]) -> None:
    positives = [row for row in report["cases"] if row["case"]["attack"] == "positive"]
    assert len(positives) == 6
    assert all(row["verdict"] == "PASS" for row in positives)
    assert {row["case"]["target"] for row in positives} == {
        "content",
        "agent",
        "tools",
        "mcp",
        "application",
        "identity",
    }


def test_security_expectations_do_not_drive_identity_runtime_behavior() -> None:
    original = next(
        case
        for case in CATALOG.cases
        if case.target == Target.IDENTITY and case.attack == "positive"
    )
    changed = original.model_copy(
        update={"criteria": (Criterion(fact="verified", expected=False),)}
    )
    actual = identity_probe(changed)
    assert actual.facts["verified"] is True
    assert score(changed, actual).verdict == Verdict.FAIL


@pytest.mark.parametrize(
    "actual,expected", [(1, True), (True, 1), (0, False), (False, 0), (None, False)]
)
def test_oracle_does_not_coerce_boolean_integer_or_missing_evidence(
    actual: Any, expected: Any
) -> None:
    case = CATALOG.cases[0].model_copy(
        update={"criteria": (Criterion(fact="guard", expected=expected),)}
    )
    assert score(case, observed({"guard": actual})).verdict == Verdict.FAIL
    assert score(case, observed({})).verdict == Verdict.FAIL


def test_not_executed_or_harness_error_cannot_be_marked_as_blocked_attack() -> None:
    case = CATALOG.cases[0].model_copy(
        update={"criteria": (Criterion(fact="guard", expected=True),)}
    )
    result = score(case, runner.unavailable("No provider configured."))
    assert result.verdict == Verdict.NOT_TESTED
    for data in [
        dict(execution="NOT_EXECUTED", facts={"guard": True}, evidence_note="Not executed."),
        dict(
            execution="RUNTIME",
            facts={"guard": True},
            evidence_note="Failed setup.",
            harness_error=True,
        ),
    ]:
        with pytest.raises(ValidationError):
            Observation.model_validate(data)


@pytest.mark.parametrize("attack", ["fact", "payload", "classification"])
def test_case_evidence_hashes_bind_attempt_observation_and_correct_classification(
    report: dict[str, Any], attack: str
) -> None:
    row = json.loads(json.dumps(report["cases"][0]))
    if attack == "fact":
        row["observed"]["facts"]["no_outcome"] = False
    elif attack == "payload":
        row["case"]["payload"] = "Changed authored attack"
    else:
        row["verdict"] = "FAIL"
        row["evidence_sha256"] = digest(
            {key: value for key, value in row.items() if key != "evidence_sha256"}
        )
    with pytest.raises(ValidationError):
        CaseResult.model_validate_json(json.dumps(row))


def catalog_at(root: Path, cases: list[dict[str, Any]]) -> Path:
    root.mkdir()
    content = (
        json.dumps({"catalog_version": "claims-adversarial-v1", "cases": cases}) + "\n"
    ).encode()
    (root / "scenarios.json").write_bytes(content)
    (root / "manifest.json").write_text(
        json.dumps({"scenarios_sha256": sha256(content).hexdigest()})
    )
    return root


def test_unexpected_runtime_failure_is_not_tested_with_no_raw_exception(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = next(case for case in CATALOG.cases if case.target == Target.AGENT)
    root = catalog_at(tmp_path / "fixture", [case.model_dump(mode="json")])

    async def fail(*args: object) -> Observation:
        raise RuntimeError("SYNTHETIC-SECRET-not-for-evidence")

    monkeypatch.setattr(RuntimeHarness, "agent", fail)
    report = runner.evaluate(root, SPEC)
    assert report["harness_complete"] is False and report["counts"] == {
        "PASS": 0,
        "FAIL": 0,
        "NOT_TESTED": 1,
    }
    assert "SYNTHETIC-SECRET" not in json.dumps(report)


def test_caught_network_guard_rejection_is_not_counted_as_runtime_protection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case = next(
        case for case in CATALOG.cases if case.target == Target.IDENTITY and case.attack == "forged"
    )
    root = catalog_at(tmp_path / "fixture", [case.model_dump(mode="json")])
    original = socket.socket.connect

    def attempted_network(case: AttackCase) -> Observation:
        with socket.socket() as connection:
            try:
                connection.connect(("127.0.0.1", 9))
            except RuntimeError:
                pass
        return observed({"verified": False})

    monkeypatch.setattr(runner, "identity_probe", attempted_network)
    report = runner.evaluate(root, SPEC)
    assert report["network_attempts"] == 1 and report["harness_complete"] is False
    assert report["counts"] == {"PASS": 0, "FAIL": 0, "NOT_TESTED": 1}
    assert socket.socket.connect is original


@pytest.mark.parametrize(
    "mutation",
    [
        "hash",
        "duplicate_json",
        "duplicate_case",
        "unknown_target",
        "duplicate_criterion",
        "too_many",
        "oversized",
        "manifest_size",
    ],
)
def test_fixture_integrity_and_capacity_fail_before_execution(
    tmp_path: Path, mutation: str
) -> None:
    cases = [CATALOG.cases[0].model_dump(mode="json")]
    if mutation == "duplicate_case":
        cases *= 2
    if mutation == "too_many":
        cases *= 97
    if mutation == "unknown_target":
        cases[0]["target"] = "external_exploit"
    if mutation == "duplicate_criterion":
        cases[0]["criteria"] *= 2
    root = catalog_at(tmp_path / "fixture", cases)
    path = root / "scenarios.json"
    if mutation in {"hash", "duplicate_json", "oversized"}:
        content = path.read_bytes()
        if mutation == "hash":
            content += b" "
        elif mutation == "duplicate_json":
            content = b'{"catalog_version":"invalid",' + content[1:]
        else:
            content = b" " * 131073
        path.write_bytes(content)
        if mutation != "hash":
            (root / "manifest.json").write_text(
                json.dumps({"scenarios_sha256": sha256(content).hexdigest()})
            )
    if mutation == "manifest_size":
        (root / "manifest.json").write_bytes(b" " * 4097)
    with pytest.raises((ValueError, ValidationError)):
        load_catalog(root)


def command() -> list[str]:
    package = Path(runner.__file__).resolve().parents[2]
    return [
        sys.executable,
        "-I",
        "-c",
        "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));"
        'runpy.run_module("claims_ai.adversarial",run_name="__main__")',
        str(package),
        "--fixture-root",
        str(FIXTURES),
        "--spec-root",
        str(SPEC),
    ]


def test_cli_writes_findings_and_returns_nonzero_instead_of_silent_success(tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    completed = subprocess.run(
        [*command(), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    data = json.loads(output.read_text())
    assert data["counts"] == {"PASS": 80, "FAIL": 0, "NOT_TESTED": 8}
    assert (
        data["harness_complete"] is True
        and "NOT_TESTED is not a blocked attack" in completed.stdout
    )
    assert "BEGIN PRIVATE KEY" not in output.read_text() and "Bearer " not in output.read_text()

    # A successful remediation must not weaken the CLI's failure exit. Change an
    # authored expectation while still running the actual independent verifier.
    positive = next(
        case
        for case in CATALOG.cases
        if case.target == Target.IDENTITY and case.attack == "positive"
    )
    failing = positive.model_copy(
        update={"criteria": (Criterion(fact="verified", expected=False),)}
    )
    fixture = catalog_at(tmp_path / "counterfactual", [failing.model_dump(mode="json")])
    failed_output = tmp_path / "failed.json"
    failed = subprocess.run(
        [*command(), "--fixture-root", str(fixture), "--output", str(failed_output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert failed.returncode == 2
    failed_report = json.loads(failed_output.read_text())
    assert failed_report["counts"] == {"PASS": 0, "FAIL": 1, "NOT_TESTED": 0}
    assert failed_report["harness_complete"] is True


@pytest.mark.parametrize("kind", ["existing", "reference"])
def test_cli_preserves_existing_evidence_and_reference_data(tmp_path: Path, kind: str) -> None:
    output = (
        tmp_path / "preserve.json"
        if kind == "existing"
        else ROOT / "data/synthetic/motor/v1/m19-must-not-write.json"
    )
    if kind == "existing":
        output.write_text("PRESERVE")
    else:
        assert not output.exists()
    completed = subprocess.run(
        [*command(), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 3
    if kind == "existing":
        assert output.read_text() == "PRESERVE"
    else:
        assert not output.exists()
