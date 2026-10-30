"""Dataset correctness and reproducibility, not model accuracy or approved coverage tests."""

import json
import subprocess
import sys
from decimal import localcontext
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.dataset.generator import DEFAULT_SEED, UNTRUSTED_TEXT, build_corpus, json_bytes
from claims_ai.dataset.render import render_pdf, render_png
from claims_ai.dataset.schema import GroundTruth, Scenario, SourceDocument
from claims_ai.dataset.validation import check_reproduction, validate_corpus, write_corpus
from claims_ai.models import Case, DocumentKind, Evidence, Policy, RiskFlag, ScanStatus


@pytest.fixture(scope="module")
def corpus_bytes() -> dict[str, bytes]:
    return build_corpus()


@pytest.fixture(scope="module")
def truth(corpus_bytes: dict[str, bytes]) -> GroundTruth:
    return GroundTruth.model_validate_json(corpus_bytes["ground_truth.json"])


@pytest.fixture
def corpus_root(tmp_path: Path, corpus_bytes: dict[str, bytes]) -> Path:
    root = tmp_path / "corpus"
    root.mkdir()
    for relative, payload in corpus_bytes.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
    return root


def test_schema_compatibility_and_no_processed_evidence(truth: GroundTruth) -> None:
    for sample in truth.samples:
        case = Case.model_validate_json(sample.input_case.model_dump_json())
        assert not case.evidence and case.assessment is None and case.decision is None
        assert case.policy is None and case.state.value == "received"
        assert all(doc.scan_status == ScanStatus.QUARANTINED for doc in case.documents)
        assert all(Policy.model_validate_json(p.model_dump_json()) == p for p in sample.policies)
        for field in sample.extraction_fields:
            assert Evidence.model_validate_json(field.expected.model_dump_json()) == field.expected
            assert field.expected.confidence is None
        assert sample.review.coverage_outcome is None
        assert sample.review.human_outcome_required and not sample.review.automatic_outcome_allowed


def test_distinct_scenario_inventory(truth: GroundTruth, corpus_bytes: dict[str, bytes]) -> None:
    assert len(truth.samples) == 12
    assert {sample.scenario for sample in truth.samples} == set(Scenario)
    assert len({sample.input_case.claim.claim_id for sample in truth.samples}) == 11
    assert sum(path.endswith(".pdf") for path in corpus_bytes) == 65
    assert sum(path.endswith(".png") for path in corpus_bytes) == 10
    by_kind = {sample.scenario: sample for sample in truth.samples}
    assert by_kind[Scenario.MISSING_ESTIMATE].expected_missing_kinds == (
        DocumentKind.REPAIR_ESTIMATE,
    )
    assert by_kind[Scenario.MISSING_PHOTO].expected_missing_kinds == (DocumentKind.DAMAGE_PHOTO,)
    assert by_kind[Scenario.HIGH_VALUE].input_case.claim.claimed_amount == 48000
    assert by_kind[Scenario.HIGH_VALUE].review.risk_flags == (RiskFlag.HIGH_RISK,)
    assert by_kind[Scenario.EXCLUSION].hypothesis_status == "requires_fictional_policy_approval"


def test_policy_version_labels_are_metadata_not_coverage(truth: GroundTruth) -> None:
    by_kind = {sample.scenario: sample for sample in truth.samples}
    expired = by_kind[Scenario.EXPIRED]
    assert expired.input_case.claim.loss_at.year == 2025
    assert expired.policy_selection.expected_version is None
    conflict = by_kind[Scenario.CONFLICT]
    assert conflict.policy_selection.expected_version is None
    assert {
        f.expected.observed_value
        for f in conflict.extraction_fields
        if f.expected.field_name == "loss_at"
    } == {"2026-06-18T10:00:00+00:00", "2026-07-18T10:00:00+00:00"}
    wrong = by_kind[Scenario.WRONG_VERSION].policy_selection
    assert wrong.submitted_version == "draft-v1" and wrong.expected_version == "draft-v2"
    boundary = by_kind[Scenario.BOUNDARY]
    assert boundary.input_case.claim.loss_at.isoformat() == "2026-07-01T00:00:00+00:00"
    assert boundary.policy_selection.expected_version == "draft-v2"
    assert all(
        p.rule_pack_version == "unapproved-no-rules" for s in truth.samples for p in s.policies
    )


def test_duplicate_reuses_exact_payload(truth: GroundTruth) -> None:
    original = truth.samples[0]
    duplicate = next(s for s in truth.samples if s.scenario == Scenario.DUPLICATE)
    assert duplicate.duplicate_of == original.scenario_id
    assert duplicate.submission_id != original.submission_id
    assert duplicate.input_case == original.input_case
    assert duplicate.extraction_fields == original.extraction_fields
    assert duplicate.review.expected_action == "duplicate_triage"


def test_untrusted_payload_is_labeled_data(
    truth: GroundTruth, corpus_bytes: dict[str, bytes]
) -> None:
    sample = next(s for s in truth.samples if s.scenario == Scenario.INJECTION)
    assert sample.review.risk_flags == (RiskFlag.INJECTION_FLAGGED,)
    field = next(
        f for f in sample.extraction_fields if f.expected.field_name == "instruction_payload"
    )
    assert field.expected.observed_value == UNTRUSTED_TEXT
    doc = next(
        d for d in sample.input_case.documents if d.document_id == field.expected.document_id
    )
    assert UNTRUSTED_TEXT.encode() in corpus_bytes[doc.artifact_ref]
    assert b"UNTRUSTED TEST PAYLOAD" in corpus_bytes[doc.artifact_ref]
    assert sample.review.coverage_outcome is None and sample.input_case.assessment is None


@pytest.mark.parametrize("seed", [0, 1, 42, DEFAULT_SEED])
def test_reproducible_for_seed(seed: int) -> None:
    assert build_corpus(seed) == build_corpus(seed)


def test_seed_changes_nuisance_values_not_scenario_coverage(corpus_bytes: dict[str, bytes]) -> None:
    other = build_corpus(DEFAULT_SEED + 1)
    assert other != corpus_bytes
    assert {
        s.scenario for s in GroundTruth.model_validate_json(other["ground_truth.json"]).samples
    } == set(Scenario)


def test_decimal_context_does_not_change_fixture_bytes(corpus_bytes: dict[str, bytes]) -> None:
    with localcontext() as context:
        context.prec = 2
        assert build_corpus() == corpus_bytes


@pytest.mark.parametrize("seed", [-1, 2**32, True])
def test_invalid_seed_rejected(seed: int) -> None:
    with pytest.raises(ValueError, match="seed"):
        build_corpus(seed)


def test_integrity_and_exact_regeneration(corpus_root: Path, truth: GroundTruth) -> None:
    assert validate_corpus(corpus_root) == truth
    assert check_reproduction(corpus_root) == truth


def test_checked_in_corpus_is_current() -> None:
    root = Path(__file__).resolve().parents[1] / "data/synthetic/motor/v1"
    assert check_reproduction(root).seed == DEFAULT_SEED


def test_new_directory_only_and_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / "fresh"
    assert write_corpus(root, 42).seed == 42
    before = (root / "manifest.json").read_bytes()
    with pytest.raises(FileExistsError):
        write_corpus(root, 1)
    assert (root / "manifest.json").read_bytes() == before
    monkeypatch.setenv("PYTHONPATH", str(Path(__file__).resolve().parents[1] / "src"))
    result = subprocess.run(
        [sys.executable, "-m", "claims_ai.dataset", "check", "--root", str(root)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0 and "12 synthetic scenarios" in result.stdout, result.stderr


@pytest.mark.parametrize("attack", ["bytes", "missing", "extra", "symlink", "label"])
def test_corrupt_corpus_rejected(corpus_root: Path, truth: GroundTruth, attack: str) -> None:
    artifact = corpus_root / truth.samples[0].input_case.documents[0].artifact_ref
    if attack == "bytes":
        artifact.write_bytes(artifact.read_bytes() + b"corruption")
    elif attack == "missing":
        artifact.unlink()
    elif attack == "extra":
        (corpus_root / "unlisted.txt").write_text("synthetic")
    elif attack == "symlink":
        (corpus_root / "alias").symlink_to(artifact)
    else:
        data = json.loads((corpus_root / "ground_truth.json").read_bytes())
        data["samples"][0]["extraction_fields"][0]["source_line"] = 999
        (corpus_root / "ground_truth.json").write_bytes(json_bytes(data))
    with pytest.raises(ValueError):
        validate_corpus(corpus_root)


@pytest.mark.parametrize(
    "attack",
    [
        "missing_scenario",
        "false_synthetic",
        "missing_kind",
        "hash",
        "wrong_version",
        "duplicate",
        "automatic",
        "supervisor",
        "scan",
    ],
)
def test_bad_ground_truth_rejected(truth: GroundTruth, attack: str) -> None:
    data = truth.model_dump(mode="json")
    sample = data["samples"][0]
    if attack == "missing_scenario":
        data["samples"].pop()
    elif attack == "false_synthetic":
        sample["synthetic"] = False
    elif attack == "missing_kind":
        sample["expected_missing_kinds"] = ["repair_estimate"]
    elif attack == "hash":
        sample["extraction_fields"][0]["expected"]["artifact_sha256"] = "f" * 64
    elif attack == "wrong_version":
        sample["policy_selection"]["expected_version"] = "draft-v2"
    elif attack == "duplicate":
        data["samples"][9]["duplicate_of"] = "SCN-99"
    elif attack == "automatic":
        sample["review"]["automatic_outcome_allowed"] = True
    elif attack == "supervisor":
        sample["review"]["risk_flags"] = ["high_risk"]
    else:
        sample["input_case"]["documents"][0]["scan_status"] = "accepted"
    with pytest.raises(ValidationError):
        GroundTruth.model_validate(data)


@pytest.mark.parametrize(
    "field,wrong", [("observed_value", "NS-POL-00000099"), ("normalized_value", "invented")]
)
def test_rehashed_but_false_extraction_label_rejected(
    corpus_root: Path,
    field: str,
    wrong: str,
) -> None:
    path = corpus_root / "ground_truth.json"
    data = json.loads(path.read_bytes())
    # Use a nonduplicated case so the test reaches source checks, not duplicate equality.
    data["samples"][1]["extraction_fields"][0]["expected"][field] = wrong
    payload = json_bytes(data)
    path.write_bytes(payload)
    manifest_path = corpus_root / "manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    entry = next(item for item in manifest["files"] if item["path"] == "ground_truth.json")
    entry.update(sha256=sha256(payload).hexdigest(), byte_size=len(payload))
    manifest_path.write_bytes(json_bytes(manifest))
    with pytest.raises(ValueError, match="source|normalized"):
        validate_corpus(corpus_root)


def test_source_rendering_bounds_and_pdf_escaping() -> None:
    source = SourceDocument(
        document_id="NS-DOC-00000001",
        title="SYNTHETIC",
        lines=("UNTRUSTED (text) \\ DATA",),
        rendering="pdf-text",
    )
    pdf = render_pdf(source)
    assert b"\\(text\\) \\\\ DATA" in pdf
    assert b"/JavaScript" not in pdf and b"/OpenAction" not in pdf
    for invalid in ["non-ASCII \u2014", "x" * 95, "embedded\nline"]:
        with pytest.raises(ValidationError):
            SourceDocument.model_validate({**source.model_dump(), "lines": [invalid]})
    image = SourceDocument(
        document_id="NS-DOC-00000001",
        title="SYNTHETIC",
        lines=("damage_location: FRONT BUMPER",),
        rendering="png-schematic",
    )
    assert render_png(image).startswith(b"\x89PNG\r\n\x1a\n")
    with pytest.raises(ValueError, match="schematic"):
        render_png(
            SourceDocument.model_validate(
                {**image.model_dump(), "lines": ["damage_location: UNKNOWN"]}
            )
        )
