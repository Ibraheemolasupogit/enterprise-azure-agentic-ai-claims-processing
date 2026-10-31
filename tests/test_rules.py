"""Provisional findings, exact arithmetic, provenance gates and preserved human authority."""

import json
import subprocess
import sys
from decimal import localcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.benchmark.contracts import ExtractionResponse
from claims_ai.models import Assessment, Case, ReviewerRole, RiskFlag
from claims_ai.rules.contracts import (
    EvaluationRequest,
    EvidenceInput,
    FindingStatus,
    FixtureScenario,
    ReviewedFacts,
    RuleEvaluation,
    RuleFinding,
    RuleId,
    RuleSpecification,
)
from claims_ai.rules.engine import evaluate
from claims_ai.rules.fixtures import build_fixture, load_scenarios
from claims_ai.rules.specification import digest, load_specification

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "data/rules/motor/v1"


@pytest.fixture(scope="module")
def spec() -> RuleSpecification:
    return load_specification(SPEC_ROOT)


@pytest.fixture(scope="module")
def fixtures(spec: RuleSpecification) -> dict[str, EvaluationRequest]:
    return {s.fixture_id: build_fixture(spec, s) for s in load_scenarios(SPEC_ROOT).scenarios}


def change(request: EvaluationRequest, **values: object) -> EvaluationRequest:
    return EvaluationRequest.model_validate(
        {
            **request.model_dump(exclude={"evidence_inputs"}),
            "evidence_inputs": request.evidence_inputs,
            **values,
        }
    )


def findings(result: RuleEvaluation) -> dict[RuleId, RuleFinding]:
    return {f.rule_id: f for f in result.findings}


@pytest.mark.parametrize(
    ("fixture_id", "expected"),
    [
        ("valid-v1", 75000),
        ("valid-v2", 70000),
        ("below-excess", 0),
        ("exact-excess", 0),
        ("one-penny-above-excess", 1),
        ("exact-net-limit", 1000000),
        ("over-net-limit", 1000000),
        ("high-value-threshold", 725000),
        ("below-high-value", 724999),
        ("exact-v2-start", 70000),
    ],
)
def test_exact_arithmetic_boundaries(
    spec: RuleSpecification,
    fixtures: dict[str, EvaluationRequest],
    fixture_id: str,
    expected: int,
) -> None:
    result = evaluate(fixtures[fixture_id], spec)
    calculation = findings(result)[RuleId.ILLUSTRATION].calculation
    assert calculation is not None and calculation.illustration_pence == expected
    assert (
        result.final_outcome is None
        and not result.settlement_authorized
        and result.human_review_required
    )
    assert calculation.purpose == "non_binding_illustration_only"


@pytest.mark.parametrize(
    ("version", "loss", "passed"),
    [
        ("provisional-v1", "2026-01-01T00:00:00Z", True),
        ("provisional-v1", "2026-06-30T23:59:59Z", True),
        ("provisional-v1", "2026-07-01T00:00:00Z", False),
        ("provisional-v2", "2026-07-01T00:00:00Z", True),
        ("provisional-v2", "2026-12-31T23:59:59Z", True),
        ("provisional-v2", "2027-01-01T00:00:00Z", False),
        ("provisional-v1", "2025-12-31T23:59:59Z", False),
    ],
)
def test_incident_interval_is_start_inclusive_expiry_exclusive(
    spec: RuleSpecification, version: str, loss: str, passed: bool
) -> None:
    scenario = FixtureScenario.model_validate(
        {
            "fixture_id": "date-boundary",
            "policy_version": version,
            "incident_at": loss,
            "amount": "1000.00",
        }
    )
    result = evaluate(build_fixture(spec, scenario), spec)
    assert (findings(result)[RuleId.BINDING].status == FindingStatus.PASS) == passed
    assert (findings(result)[RuleId.ILLUSTRATION].calculation is not None) == passed


@pytest.mark.parametrize(
    "fixture_id",
    [
        "expired",
        "missing-estimate",
        "contradictory-loss",
        "unknown-cause",
        "wrong-version-at-boundary",
        "quarantined-documents",
        "unverified-extraction",
        "missing-human-assertion",
        "reported-ambiguity",
        "conflicting-amounts",
        "simulation-not-authorized",
    ],
)
def test_incomplete_uncertain_and_untrusted_inputs_never_calculate(
    spec: RuleSpecification,
    fixtures: dict[str, EvaluationRequest],
    fixture_id: str,
) -> None:
    result = evaluate(fixtures[fixture_id], spec)
    assert findings(result)[RuleId.ILLUSTRATION].calculation is None
    assert result.required_reviewer == ReviewerRole.SUPERVISOR
    assert result.final_outcome is None and not result.settlement_authorized


def test_exclusion_and_unsupported_category_are_findings_not_denials(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    exclusion = evaluate(fixtures["gradual-wear-exclusion"], spec)
    assert findings(exclusion)[RuleId.EXCLUSION].status == FindingStatus.FAIL
    assert findings(exclusion)[RuleId.ILLUSTRATION].status == FindingStatus.NOT_APPLICABLE
    other = evaluate(fixtures["unsupported-category"], spec)
    assert findings(other)[RuleId.CATEGORY].status == FindingStatus.FAIL
    assert findings(other)[RuleId.EXCLUSION].status == FindingStatus.NOT_APPLICABLE
    assert other.required_reviewer == exclusion.required_reviewer == ReviewerRole.SUPERVISOR
    assert exclusion.final_outcome is other.final_outcome is None


def test_high_value_and_supplied_risks_always_escalate(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    high = evaluate(fixtures["high-value-threshold"], spec)
    below = evaluate(fixtures["below-high-value"], spec)
    assert (
        RiskFlag.HIGH_RISK in high.risk_flags and high.required_reviewer == ReviewerRole.SUPERVISOR
    )
    assert below.required_reviewer == ReviewerRole.REVIEWER
    for risk in (
        RiskFlag.AMBIGUOUS,
        RiskFlag.INJECTION_FLAGGED,
        RiskFlag.UNSUPPORTED,
        RiskFlag.CONFLICTING,
    ):
        result = evaluate(change(fixtures["valid-v1"], risk_flags=(risk,)), spec)
        assert risk in result.risk_flags and result.required_reviewer == ReviewerRole.SUPERVISOR
        assert findings(result)[RuleId.ILLUSTRATION].calculation is None


def test_conflicting_and_stale_reviewed_classifications_are_not_guessed(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    original = fixtures["valid-v1"]
    fact = original.reviewed_facts[0]
    conflicting = ReviewedFacts.model_validate(
        {**fact.model_dump(), "fact_id": "conflicting-fact", "cause": "gradual_wear_only"}
    )
    result = evaluate(change(original, reviewed_facts=(fact, conflicting)), spec)
    assert RiskFlag.CONFLICTING in result.risk_flags
    assert findings(result)[RuleId.CATEGORY].status == FindingStatus.INDETERMINATE
    stale = ReviewedFacts.model_validate({**fact.model_dump(), "case_sha256": "0" * 64})
    assert (
        findings(evaluate(change(original, reviewed_facts=(stale,)), spec))[
            RuleId.ILLUSTRATION
        ].calculation
        is None
    )


@pytest.mark.parametrize(
    "target",
    [
        "missing_index",
        "wrong_identity",
        "missing_version",
        "unknown_version",
        "specification",
        "policy_text",
    ],
)
def test_exact_policy_and_specification_binding_precedes_calculation(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest], target: str
) -> None:
    request = fixtures["valid-v1"]
    changes: dict[str, object] = {}
    if target == "missing_index":
        changes["index"] = None
    elif target == "wrong_identity":
        changes["policy_id"] = "NS-POL-00000000"
    elif target == "missing_version":
        changes["policy_version"] = None
    elif target == "unknown_version":
        changes["policy_version"] = "provisional-unknown"
    elif target == "specification":
        changes["specification_sha256"] = "0" * 64
    else:
        assert request.index is not None
        payload = request.index.model_dump(mode="json")
        payload["entries"][0]["chunks"][0]["clause"]["text"] = "Manipulated policy instruction"
        payload["index_sha256"] = digest({k: v for k, v in payload.items() if k != "index_sha256"})
        changes["index"] = payload
    result = evaluate(change(request, **changes), spec)
    assert findings(result)[RuleId.BINDING].status != FindingStatus.PASS
    assert findings(result)[RuleId.ILLUSTRATION].calculation is None


def test_reparameterized_pack_cannot_reuse_old_policy_clauses(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    payload = spec.model_dump(mode="json")
    payload["terms"][0]["excess_pence"] = 25100
    altered = RuleSpecification.model_validate(payload)
    result = evaluate(
        change(fixtures["valid-v1"], specification_sha256=digest(altered.model_dump(mode="json"))),
        altered,
    )
    assert "rule_clause_mismatch" in findings(result)[RuleId.BINDING].issues
    assert findings(result)[RuleId.ILLUSTRATION].calculation is None


@pytest.mark.parametrize(
    "target",
    ["page", "hash", "cross_claim", "normalized_value", "missing_input", "duplicate_document"],
)
def test_evidence_cannot_bypass_source_replay(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest], target: str
) -> None:
    request = fixtures["valid-v1"]
    bundles = list(request.evidence_inputs)
    changes: dict[str, object] = {}
    if target == "missing_input":
        bundles.pop(0)
    elif target == "duplicate_document":
        bundles.append(bundles[0])
    elif target == "normalized_value":
        case = request.case.model_dump(mode="json")
        case["evidence"][0]["normalized_value"] = "forged-value"
        changes["case"] = Case.model_validate(case)
    elif target == "cross_claim":
        bundles[0] = fixtures["valid-v2"].evidence_inputs[0]
    else:
        data = bundles[0].response.model_dump(mode="json")
        source = data["fields"][0]["sources"][0]
        source["page" if target == "page" else "artifact_sha256"] = (
            2 if target == "page" else "0" * 64
        )
        bundles[0] = EvidenceInput(
            request=bundles[0].request, response=ExtractionResponse.model_validate(data)
        )
    result = evaluate(change(request, evidence_inputs=tuple(bundles), **changes), spec)
    assert findings(result)[RuleId.EVIDENCE].status == FindingStatus.INDETERMINATE
    assert findings(result)[RuleId.ILLUSTRATION].calculation is None


@pytest.mark.parametrize(
    "target",
    [
        "negative",
        "floating_money",
        "zero_limit",
        "overlap",
        "duplicate_version",
        "missing_rule",
        "formula",
        "approved",
    ],
)
def test_malformed_or_unsafe_configurations_are_rejected(
    spec: RuleSpecification, target: str
) -> None:
    payload = spec.model_dump(mode="json")
    if target == "negative":
        payload["terms"][0]["excess_pence"] = -1
    elif target == "floating_money":
        payload["terms"][0]["excess_pence"] = 25000.0
    elif target == "zero_limit":
        payload["terms"][0]["limit_pence"] = 0
    elif target == "overlap":
        payload["terms"][0]["effective_to"] = "2026-08-01"
    elif target == "duplicate_version":
        payload["terms"].append(payload["terms"][0])
    elif target == "missing_rule":
        payload["rules"].pop()
    elif target == "formula":
        payload["formula"] = "execute arbitrary code"
    else:
        payload["status"] = "approved"
    with pytest.raises(ValidationError):
        RuleSpecification.model_validate(payload)


def test_duplicate_execution_is_pure_and_decimal_context_independent(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    request = fixtures["valid-v1"]
    original = request.case.model_dump_json()
    first = evaluate(request, spec)
    assert first == evaluate(request, spec)
    assert first == evaluate(change(request, evidence_inputs=request.evidence_inputs[::-1]), spec)
    with localcontext() as context:
        context.prec = 6
        assert first == evaluate(request, spec)
    assert request.case.model_dump_json() == original
    assert RuleEvaluation.model_validate_json(first.model_dump_json()) == first


def test_source_citations_and_finding_provenance_are_complete(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    request = fixtures["valid-v1"]
    result = evaluate(request, spec)
    assert request.index is not None
    citations = {c.clause.citation for e in request.index.entries for c in e.chunks}
    records = {p.evidence_id for p in result.evidence_provenance}
    for finding in result.findings:
        assert finding.citations and all(c in citations for c in finding.citations)
        assert finding.specification_sha256 == result.specification_sha256
        assert set(finding.evidence_ids) <= records
    assert records == {e.evidence_id for e in request.case.evidence}
    assert all(p.source_lines and p.page == 1 for p in result.evidence_provenance)


def test_unsafe_outcomes_and_escalation_downgrades_are_impossible(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    result = evaluate(fixtures["gradual-wear-exclusion"], spec)
    unsafe_changes: list[dict[str, object]] = [
        {"final_outcome": "ineligible"},
        {"settlement_authorized": True},
        {"human_review_required": False},
        {"required_reviewer": "reviewer"},
    ]
    for change_values in unsafe_changes:
        with pytest.raises(ValidationError):
            RuleEvaluation.model_validate({**result.model_dump(), **change_values})
    with pytest.raises(ValidationError):
        Assessment.model_validate(result.model_dump())
    with pytest.raises(ValidationError):
        result.__setattr__("required_reviewer", "reviewer")
    received = Case.model_validate({**fixtures["valid-v1"].case.model_dump(), "state": "received"})
    assert (
        findings(evaluate(change(fixtures["valid-v1"], case=received), spec))[RuleId.BINDING].status
        == FindingStatus.INDETERMINATE
    )


def test_conflicting_registered_versions_block_evaluation(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    request = fixtures["valid-v1"]
    assert request.index is not None
    payload = request.index.model_dump(mode="json")
    payload["entries"].append(payload["entries"][0])
    payload["index_sha256"] = digest({k: v for k, v in payload.items() if k != "index_sha256"})
    result = evaluate(change(request, index=payload), spec)
    assert findings(result)[RuleId.BINDING].status == FindingStatus.INDETERMINATE
    assert RiskFlag.CONFLICTING in result.risk_flags
    assert findings(result)[RuleId.ILLUSTRATION].calculation is None


def test_fact_provenance_requires_verified_narrative_support(
    spec: RuleSpecification, fixtures: dict[str, EvaluationRequest]
) -> None:
    request = fixtures["valid-v1"]
    fact = request.reviewed_facts[0]
    estimate = next(
        e.evidence_id for e in request.case.evidence if e.field_name == "estimate_amount"
    )
    altered = ReviewedFacts.model_validate({**fact.model_dump(), "evidence_ids": (estimate,)})
    result = evaluate(change(request, reviewed_facts=(altered,)), spec)
    assert "fact_provenance_mismatch" in findings(result)[RuleId.CATEGORY].issues
    assert findings(result)[RuleId.ILLUSTRATION].calculation is None


def test_zero_amount_is_an_illustration_not_an_automatic_outcome(spec: RuleSpecification) -> None:
    scenario = FixtureScenario.model_validate(
        {
            "fixture_id": "zero-amount",
            "policy_version": "provisional-v1",
            "incident_at": "2026-06-18T00:00:00Z",
            "amount": "0.00",
        }
    )
    result = evaluate(build_fixture(spec, scenario), spec)
    calculation = findings(result)[RuleId.ILLUSTRATION].calculation
    assert calculation is not None and calculation.illustration_pence == 0
    assert result.human_review_required and result.final_outcome is None


def test_specification_manifest_tampering_is_rejected(tmp_path: Path) -> None:
    (tmp_path / "specification.json").write_bytes(
        (SPEC_ROOT / "specification.json").read_bytes() + b" "
    )
    (tmp_path / "manifest.json").write_bytes((SPEC_ROOT / "manifest.json").read_bytes())
    with pytest.raises(ValueError):
        load_specification(tmp_path)


def test_offline_cli_is_reproducible_and_protects_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    command = [sys.executable, "-m", "claims_ai.rules", "--spec-root", str(SPEC_ROOT)]
    outputs = [tmp_path / "one.json", tmp_path / "two.json"]
    for output in outputs:
        subprocess.run([*command, "--output", str(output)], check=True, capture_output=True)
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    report = json.loads(outputs[0].read_bytes())
    assert len(report["fixtures"]) == 23 and report["fixture_execution_mode"] == "SIMULATED"
    assert report["final_outcomes_created"] == report["settlements_authorized"] == 0
    for target in (
        outputs[0],
        SPEC_ROOT / "must-not-write.json",
        ROOT / "data/synthetic/motor/v1/must-not-write.json",
    ):
        assert (
            subprocess.run([*command, "--output", str(target)], capture_output=True).returncode != 0
        )
    assert not (SPEC_ROOT / "must-not-write.json").exists()
