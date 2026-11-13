"""Stage A authoring/integrity contracts, never a scored 60-case evaluation."""

import builtins
import json
from hashlib import sha256
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from claims_ai.quality_ops.candidate import (
    candidate_bytes,
    verify_candidate,
    write_candidate,
)
from claims_ai.quality_ops.cases import generate_inputs, scenarios
from claims_ai.quality_ops.contracts import (
    COHORT_COUNTS,
    Cohort,
    MacroRecallEvidence,
    Measurement,
    PredictionInputs,
    PredictionRecord,
    ReferenceLabels,
    ReviewTemplate,
    ReviewTemplates,
    ScalarMeasurement,
)
from claims_ai.quality_ops.prediction_access import bounded_bytes, load_prediction_inputs
from claims_ai.quality_ops.references import gate_plan, propose_labels

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_SHA256 = "42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b"


def test_repository_candidate_remains_verifiable_independently_of_future_authoring() -> None:
    root = ROOT / "data/evaluation/m22/v1"
    verify_candidate(root, expected_manifest_sha256=CANDIDATE_SHA256)
    manifest = json.loads((root / "candidate-manifest.json").read_bytes())
    assert manifest["review_status"] == "PENDING_REVIEW" and manifest["case_count"] == 60


@pytest.fixture
def bundle(tmp_path: Path) -> tuple[Path, str]:
    path = tmp_path / "candidate-v1"
    return path, write_candidate(path, repository_root=ROOT)


def test_sixty_distinct_new_cases_have_exact_cohorts_and_bound_sources() -> None:
    inputs = generate_inputs()
    labels = propose_labels(inputs)
    assert len(inputs.cases) == len(labels.labels) == len(scenarios()) == 60
    assert {c: sum(r.cohort == c for r in labels.labels) for c in Cohort} == COHORT_COUNTS
    assert len({a.content_sha256 for c in inputs.cases for a in c.assets}) == sum(
        len(c.assets) for c in inputs.cases
    )
    historical = b"".join(
        p.read_bytes() for p in (ROOT / "data").rglob("*.json") if "m22" not in p.parts
    )
    for case in inputs.cases:
        assert case.claim_id.encode() not in historical
        for asset in case.assets:
            assert asset.content_sha256.encode() not in historical
            assert asset.content.startswith("SYNTHETIC M22")


def test_construction_repeats_without_clocks_predictions_or_review_claims() -> None:
    first = candidate_bytes()
    assert first == candidate_bytes()
    manifest = json.loads(first["candidate-manifest.json"])
    assert manifest["review_status"] == "PENDING_REVIEW"
    assert manifest["scored_evaluation_allowed"] is False
    assert manifest["holdout_status"] == "CANDIDATE_NOT_SEALED_AUTHOR_VISIBLE"
    reviews = ReviewTemplates.model_validate_json(first["reviews/templates.json"])
    assert all(r.reviewer_identity is r.approval is r.signature is None for r in reviews.reviews)
    assert all(r.status == "PENDING_REVIEW" for r in reviews.reviews)


def test_every_field_quote_and_review_binds_the_exact_candidate(bundle: tuple[Path, str]) -> None:
    root, pin = bundle
    verify_candidate(root, expected_manifest_sha256=pin)
    labels = ReferenceLabels.model_validate_json((root / "references/labels.json").read_bytes())
    ordinary = [r for r in labels.labels if r.cohort == Cohort.DAMAGE]
    assert len(ordinary) == 15
    assert all(r.illustrative_net_pence is not None for r in ordinary)
    assert {0, 1, 300000} <= {r.illustrative_net_pence for r in ordinary}
    assert all(r.actual_insurance_authority is False for r in labels.labels)
    assert len({r.case_id for r in labels.labels}) == 60


def test_prediction_access_never_opens_reference_or_review_files(
    bundle: tuple[Path, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    root, _ = bundle
    manifest = json.loads((root / "candidate-manifest.json").read_bytes())
    original = Path.open
    opened = []

    def guarded(path: Path, *args: Any, **kwargs: Any) -> Any:
        assert path in {root / "inputs/manifest.json", root / "inputs/cases.json"}
        opened.append(path)
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", guarded)
    inputs = load_prediction_inputs(
        root, expected_manifest_sha256=manifest["prediction_manifest_sha256"]
    )
    assert len(inputs.cases) == 60 and len(opened) == 2


@pytest.mark.parametrize("field", ["expected_outcome", "reference_labels", "reviewer", "cohort"])
def test_prediction_dto_rejects_label_or_approval_fields(field: str) -> None:
    data = generate_inputs().model_dump(mode="json")
    data["cases"][0][field] = "untrusted"
    with pytest.raises(ValidationError):
        PredictionInputs.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "APPROVED"),
        ("reviewer_identity", "fabricated-reviewer"),
        ("approval", True),
        ("signature", "invented"),
    ],
)
def test_pending_templates_cannot_be_used_as_approval_records(field: str, value: object) -> None:
    template = json.loads(candidate_bytes()["reviews/templates.json"])["reviews"][0]
    with pytest.raises(ValidationError):
        ReviewTemplate.model_validate({**template, field: value})


@pytest.mark.parametrize(
    "name",
    [
        "inputs/cases.json",
        "references/labels.json",
        "reviews/templates.json",
        "gates.json",
        "inventory.json",
    ],
)
def test_frozen_candidate_tamper_is_detected(bundle: tuple[Path, str], name: str) -> None:
    root, pin = bundle
    path = root / name
    path.chmod(0o644)
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError):
        verify_candidate(root, expected_manifest_sha256=pin)


def test_existing_candidate_cannot_be_regenerated(bundle: tuple[Path, str]) -> None:
    root, pin = bundle
    with pytest.raises(FileExistsError):
        write_candidate(root, repository_root=ROOT)
    verify_candidate(root, expected_manifest_sha256=pin)
    assert all(not p.stat().st_mode & 0o222 for p in root.rglob("*") if p.is_file())


@pytest.mark.parametrize(
    "folder",
    [
        "data/synthetic/motor/new-m22-test",
        "data/security/adversarial/new-m22-test",
        "outputs/new-m22-test",
    ],
)
def test_historical_namespaces_are_not_authoring_destinations(folder: str) -> None:
    destination = ROOT / folder
    assert not destination.exists()
    with pytest.raises(ValueError, match="historical evidence"):
        write_candidate(destination, repository_root=ROOT)
    assert not destination.exists()


def test_input_pin_and_symlinks_fail_closed(bundle: tuple[Path, str], tmp_path: Path) -> None:
    root, _ = bundle
    with pytest.raises(ValueError, match="manifest mismatch"):
        load_prediction_inputs(root, expected_manifest_sha256="0" * 64)
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    pin = sha256((root / "inputs/manifest.json").read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="alias"):
        load_prediction_inputs(alias, expected_manifest_sha256=pin)


def test_candidate_file_read_is_bounded(tmp_path: Path) -> None:
    path = tmp_path / "oversized"
    path.write_bytes(b"x" * 100)
    with pytest.raises(ValueError, match="capacity"):
        bounded_bytes(path, 10)


def test_frozen_proposal_retains_release_thresholds_and_honest_denominators() -> None:
    gates = gate_plan()
    values = {m.metric_id: m.threshold for m in gates.metrics}
    assert values["critical_fields"] == values["retrieval_recall_at_5"] == 0.95
    assert values["rule_agreement"] == values["grounding"] == 1.0
    assert values["unauthorised_actions"] == values["telemetry_leaks"] == 0.0
    assert gates.scored_evaluation_allowed is False
    assert gates.zero_denominator == "null_and_NOT_TESTED"
    assert gates.probabilistic_repeats == 3


def measurement(**changes: object) -> Measurement:
    return Measurement.model_validate(
        {
            "metric_id": "supervisor_routing",
            "cohort": "security",
            "execution": "RUNTIME",
            "capability_available": True,
            "review_status": "APPROVED",
            "verdict": "PASS",
            "numerator": 2,
            "denominator": 2,
            "rate": 1.0,
            **changes,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"review_status": "PENDING_REVIEW"},
        {"capability_available": False},
        {"execution": "NOT_EXECUTED"},
        {"failures": ("harness_error",)},
        {"failures": ("safety_violation",)},
        {"failures": ("unavailable_capability",)},
        {"denominator": 0, "numerator": 0, "rate": None},
        {"rate": 0.5},
        {"numerator": 3},
        {"denominator": True},
        {"rate": float("nan")},
    ],
)
def test_unavailable_incomplete_or_failing_observations_cannot_pass(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        measurement(**changes)


def test_zero_denominator_and_pending_review_remain_not_tested() -> None:
    row = measurement(
        review_status="PENDING_REVIEW",
        verdict="NOT_TESTED",
        numerator=0,
        denominator=0,
        rate=None,
        execution="NOT_EXECUTED",
        capability_available=False,
        failures=("pending_review",),
        unavailable_reason="Independent review and prediction execution are pending",
    )
    assert row.rate is None and row.verdict == "NOT_TESTED"


def test_observed_safety_failure_is_not_hidden_by_pending_label_review() -> None:
    row = measurement(
        review_status="PENDING_REVIEW", verdict="FAIL", failures=("safety_violation",)
    )
    assert row.verdict == "FAIL"
    with pytest.raises(ValidationError):
        measurement(
            review_status="PENDING_REVIEW",
            verdict="NOT_TESTED",
            unavailable_reason="review pending",
            failures=("safety_violation",),
        )


def test_macro_recall_keeps_query_denominators_instead_of_pooling() -> None:
    ids = [c.case_id for c in generate_inputs().cases[:2]]
    data = dict(
        queries=[
            dict(case_id=ids[0], relevant=1, valid_unique_relevant_at_5=1),
            dict(case_id=ids[1], relevant=3, valid_unique_relevant_at_5=1),
        ],
        excluded_empty_relevance_queries=1,
    )
    assert MacroRecallEvidence.model_validate({**data, "macro_recall_at_5": (1 + 1 / 3) / 2})
    with pytest.raises(ValidationError):
        MacroRecallEvidence.model_validate({**data, "macro_recall_at_5": 2 / 4})


def test_unavailable_scalar_measurement_is_null_not_zero() -> None:
    data = dict(
        metric_id="packet_p95_seconds",
        value=None,
        sample_count=0,
        review_status="PENDING_REVIEW",
        verdict="NOT_TESTED",
        unavailable_reason="No approved workload or live provider",
    )
    assert ScalarMeasurement.model_validate(data).value is None
    with pytest.raises(ValidationError):
        ScalarMeasurement.model_validate({**data, "value": 0.0})


def test_prediction_record_distinguishes_missing_fields_from_explicit_unknown() -> None:
    case = generate_inputs().cases[0]
    fields: dict[str, None] = dict.fromkeys(
        ["policy_id", "loss_date", "vehicle_reference", "estimate_pence", "currency"]
    )
    data = dict(
        case_id=case.case_id,
        input_sha256="1" * 64,
        execution="SIMULATED",
        critical_fields=fields,
        returned_clause_ids=(),
        proposed_findings=(),
        proposed_route="supervisor",
    )
    assert PredictionRecord.model_validate(data)
    fields.pop("currency")
    with pytest.raises(ValidationError):
        PredictionRecord.model_validate(data)


def test_stage_a_authoring_does_not_require_sdk_or_provider_imports(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = builtins.__import__

    def guarded(name: str, *args: Any, **kwargs: Any) -> Any:
        assert not name.startswith(("opentelemetry.sdk", "azure", "openai"))
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded)
    assert json.loads(candidate_bytes()["candidate-manifest.json"])["case_count"] == 60
