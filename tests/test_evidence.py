"""Pure synthetic evidence-boundary tests; scan acceptance below is a test assertion only."""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.benchmark.adapters import FixtureAdapter
from claims_ai.benchmark.contracts import ExtractionRequest, ExtractionResponse, FieldSpec
from claims_ai.benchmark.scoring import field_kind
from claims_ai.dataset.render import render_document
from claims_ai.dataset.schema import GroundTruth, SourceDocument
from claims_ai.evidence import processing
from claims_ai.evidence.contracts import (
    Disposition,
    EvidenceHistory,
    IssueCode,
    ProcessingRequest,
    ProcessingResult,
)
from claims_ai.evidence.normalization import normalize
from claims_ai.evidence.processing import admit_evidence, process_extraction
from claims_ai.models import Case, DocumentKind, ScanStatus

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/synthetic/motor/v1"


@dataclass(frozen=True)
class Bundle:
    request: ProcessingRequest
    response: ExtractionResponse


@pytest.fixture(scope="module")
def truth() -> GroundTruth:
    return GroundTruth.model_validate_json((CORPUS / "ground_truth.json").read_bytes())


def bundle_for(truth: GroundTruth, sample_index: int = 0, document_index: int = 0) -> Bundle:
    sample = truth.samples[sample_index]
    original = sample.input_case.documents[document_index]
    # Deliberate local unit-test clearance assertion, never an actual malware scan or corpus edit.
    docs = tuple(
        type(d).model_validate({**d.model_dump(), "scan_status": ScanStatus.ACCEPTED})
        for d in sample.input_case.documents
    )
    case = Case.model_validate(
        {**sample.input_case.model_dump(), "state": "extracting", "revision": 3, "documents": docs}
    )
    doc = case.documents[document_index]
    content = (CORPUS / doc.artifact_ref).read_bytes()
    source = SourceDocument.model_validate_json(
        (CORPUS / (doc.artifact_ref + ".source.json")).read_bytes()
    )
    adapter = FixtureAdapter(truth)
    response = asyncio.run(
        adapter.extract(
            ExtractionRequest(
                request_id=doc.document_id,
                document=doc,
                content=content,
                fields=tuple(
                    FieldSpec(name=f.expected.field_name, kind=field_kind(f.expected.field_name))
                    for f in sample.extraction_fields
                    if f.expected.document_id == original.document_id
                ),
            )
        )
    )
    request = ProcessingRequest(
        case=case,
        document_id=doc.document_id,
        request_id=doc.document_id,
        expected_provider=adapter.profile.identity,
        content=content,
        fixture_source=source,
    )
    return Bundle(request, response)


@pytest.fixture
def bundle(truth: GroundTruth) -> Bundle:
    return bundle_for(truth)


def change_value(bundle: Bundle, name: str, value: str) -> Bundle:
    source = bundle.request.fixture_source
    assert source is not None
    lines = tuple(
        f"{name}: {value}" if line.startswith(name + ": ") else line for line in source.lines
    )
    updated = SourceDocument.model_validate({**source.model_dump(), "lines": lines})
    content = render_document(updated)
    digest = sha256(content).hexdigest()
    case = bundle.request.case
    docs = tuple(
        type(d).model_validate({**d.model_dump(), "sha256": digest, "byte_size": len(content)})
        if d.document_id == bundle.request.document_id
        else d
        for d in case.documents
    )
    case = Case.model_validate({**case.model_dump(), "documents": docs})
    data = bundle.response.model_dump(mode="json")
    data["artifact_sha256"] = digest
    for field in data["fields"]:
        if field["name"] == name:
            field["value"] = value
        for ref in field["sources"]:
            ref["artifact_sha256"] = digest
    return Bundle(
        ProcessingRequest.model_validate(
            {
                **bundle.request.model_dump(),
                "content": content,
                "fixture_source": updated,
                "case": case,
            }
        ),
        ExtractionResponse.model_validate(data),
    )


def test_valid_mapping_preserves_metadata_and_admission_is_explicit(bundle: Bundle) -> None:
    result = process_extraction(bundle.request, bundle.response)
    assert result.disposition == Disposition.ACCEPTED and len(result.candidates) == 8
    assert len(result.history.records) == 8 and len(result.history.receipts) == 1
    assert all(
        r.provider == bundle.response.provider and r.reported_confidence is None
        for r in result.candidates
    )
    assert all(
        r.quality.source_verification == "fixture_render_verified" for r in result.candidates
    )
    assert all("simulated_extraction" in r.evidence.validation_flags for r in result.candidates)
    assert all(r.sources[0].source_line is not None for r in result.candidates)
    with pytest.raises(ValueError, match="simulation"):
        admit_evidence(bundle.request.case, result)
    admission = admit_evidence(bundle.request.case, result, allow_simulated=True)
    assert len(admission.current.evidence) == 8 and admission.current.revision == 4
    assert admission.previous == bundle.request.case and not admission.previous.evidence
    assert admission.current.state == bundle.request.case.state
    assert ProcessingResult.model_validate_json(result.model_dump_json()) == result


@pytest.mark.parametrize(
    "name,raw,expected",
    [
        ("claimed_amount", "001,234.5000", "1234.50"),
        ("estimate_amount", "0", "0.00"),
        ("loss_at", "2026-01-02T11:00:00+01:00", "2026-01-02T10:00:00Z"),
        ("effective_from", "2026-01-02", "2026-01-02"),
        ("damage_location", "FRONT BUMPER", "front_bumper"),
        ("narrative", " A\n  synthetic  story ", "A synthetic story"),
        ("policy_id", "NS-POL-00000001", "NS-POL-00000001"),
    ],
)
def test_normalization(name: str, raw: str, expected: str) -> None:
    assert normalize(name, raw) == expected


@pytest.mark.parametrize(
    "name,raw",
    [
        ("claimed_amount", "-1"),
        ("estimate_amount", "1.234"),
        ("estimate_amount", "NaN"),
        ("estimate_amount", "1,23"),
        ("claimed_amount", "GBP 1"),
        ("claimed_amount", "1e3"),
        ("loss_at", "2026-01-02T12:00:00"),
        ("effective_to", "01/02/2026"),
        ("effective_to", "2026-02-30"),
        ("policy_id", "ns-pol-00000001"),
        ("currency", "USD"),
        ("narrative", "bad\x00text"),
    ],
)
def test_bad_values_fail_closed(name: str, raw: str) -> None:
    with pytest.raises(ValueError):
        normalize(name, raw)


def test_numeric_normalization_in_mapping_preserves_raw(bundle: Bundle) -> None:
    amount = bundle.request.case.claim.claimed_amount
    changed = change_value(bundle, "claimed_amount", f"{amount:,.4f}")
    result = process_extraction(changed.request, changed.response)
    assert result.disposition == Disposition.ACCEPTED
    record = next(r for r in result.candidates if r.evidence.field_name == "claimed_amount")
    assert record.raw_value == f"{amount:,.4f}"
    assert record.evidence.normalized_value == f"{amount:.2f}"


@pytest.mark.parametrize(
    "target,value",
    [
        ("document_id", "NS-DOC-00000099"),
        ("artifact_sha256", "f" * 64),
        ("request_id", "wrong-request"),
    ],
)
def test_tampered_envelope_rejected_atomically(bundle: Bundle, target: str, value: str) -> None:
    response = {**bundle.response.model_dump(mode="json"), target: value}
    result = process_extraction(bundle.request, response)
    assert result.disposition == Disposition.REJECTED and not result.history.records
    assert IssueCode.IDENTITY in {i.code for i in result.issues}


@pytest.mark.parametrize(
    "target,value",
    [
        ("document_id", "NS-DOC-00000099"),
        ("artifact_sha256", "f" * 64),
        ("page", 2),
        ("source_line", 99),
        ("source_line", 5),
        ("location_kind", "image_caption"),
    ],
)
def test_tampered_sources_never_partially_admit(bundle: Bundle, target: str, value: object) -> None:
    response = bundle.response.model_dump(mode="json")
    response["fields"][0]["sources"][0][target] = value
    result = process_extraction(bundle.request, response)
    assert result.disposition == Disposition.REJECTED and not result.history.records
    assert IssueCode.PROVENANCE in {i.code for i in result.issues}
    with pytest.raises(ValueError):
        admit_evidence(bundle.request.case, result, allow_simulated=True)


def test_cross_claim_request_and_bad_bytes_rejected(bundle: Bundle) -> None:
    foreign = ProcessingRequest.model_validate(
        {
            **bundle.request.model_dump(),
            "content": bundle.request.content,
            "document_id": "NS-DOC-00000099",
        }
    )
    assert process_extraction(foreign, bundle.response).disposition == Disposition.REJECTED
    tampered = ProcessingRequest.model_validate(
        {**bundle.request.model_dump(), "content": b"tampered"}
    )
    assert IssueCode.HASH in {i.code for i in process_extraction(tampered, bundle.response).issues}
    with pytest.raises(ValueError, match="ownership"):
        process_extraction(
            bundle.request, bundle.response, EvidenceHistory(claim_id="NS-CLM-00000099")
        )


def test_unverified_and_unscanned_inputs_are_held(bundle: Bundle) -> None:
    no_source = ProcessingRequest.model_validate(
        {**bundle.request.model_dump(), "content": bundle.request.content, "fixture_source": None}
    )
    result = process_extraction(no_source, bundle.response)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert all(r.quality.source_verification == "structural_only" for r in result.candidates)
    for status, disposition in [
        (ScanStatus.QUARANTINED, Disposition.QUARANTINED),
        (ScanStatus.REJECTED, Disposition.REJECTED),
    ]:
        case = Case.model_validate(
            {
                **bundle.request.case.model_dump(),
                "documents": [
                    {**d.model_dump(), "scan_status": status} for d in bundle.request.case.documents
                ],
            }
        )
        request = ProcessingRequest.model_validate(
            {**bundle.request.model_dump(), "content": bundle.request.content, "case": case}
        )
        result = process_extraction(request, bundle.response)
        assert result.disposition == disposition and not result.history.records


def test_missing_duplicate_and_untrusted_fields_held(bundle: Bundle) -> None:
    response = bundle.response.model_dump(mode="json")
    response["fields"].pop(0)
    result = process_extraction(bundle.request, response)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert IssueCode.MISSING in {i.code for i in result.issues}
    response = bundle.response.model_dump(mode="json")
    response["fields"].append(response["fields"][0])
    result = process_extraction(bundle.request, response)
    assert result.disposition == Disposition.QUARANTINED
    assert IssueCode.DUPLICATE_FIELD in {i.code for i in result.issues}
    response = bundle.response.model_dump(mode="json")
    response["fields"].append({"name": "instruction_payload", "value": "UNTRUSTED SYNTHETIC DATA"})
    result = process_extraction(bundle.request, response)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert IssueCode.UNSUPPORTED in {i.code for i in result.issues}


def test_conflicting_values_preserve_immutable_history(bundle: Bundle) -> None:
    initial = process_extraction(bundle.request, bundle.response)
    snapshot = initial.history.model_dump_json()
    changed = change_value(bundle, "loss_at", "2026-06-19T10:00:00+00:00")
    result = process_extraction(changed.request, changed.response, initial.history)
    assert result.disposition == Disposition.QUARANTINED
    assert IssueCode.CONFLICT in {i.code for i in result.issues}
    assert result.history.records == initial.history.records and len(result.history.receipts) == 2
    assert initial.history.model_dump_json() == snapshot
    with pytest.raises(ValidationError):
        initial.history.records[0].evidence.normalized_value = "changed"  # type: ignore[misc]


def test_policy_versions_have_document_scopes(truth: GroundTruth) -> None:
    history = None
    for index, document in enumerate(truth.samples[0].input_case.documents):
        if document.kind not in {DocumentKind.POLICY_SCHEDULE, DocumentKind.POLICY_WORDING}:
            continue
        bundle = bundle_for(truth, 0, index)
        result = process_extraction(bundle.request, bundle.response, history)
        assert result.disposition == Disposition.ACCEPTED
        assert IssueCode.CONFLICT not in {i.code for i in result.issues}
        history = result.history


def test_repeated_processing_and_admission_are_idempotent(bundle: Bundle) -> None:
    first = process_extraction(bundle.request, bundle.response)
    replay = process_extraction(bundle.request, bundle.response, first.history)
    assert replay.disposition == Disposition.DUPLICATE and replay.replay_of == Disposition.ACCEPTED
    assert replay.history == first.history and not replay.candidates
    changed = {
        **bundle.response.model_dump(mode="json"),
        "latency_ms": 10.0,
        "usage": {"input_tokens": 10, "output_tokens": 1},
    }
    assert (
        process_extraction(bundle.request, changed, first.history).disposition
        == Disposition.DUPLICATE
    )
    admission = admit_evidence(bundle.request.case, first, allow_simulated=True)
    again = admit_evidence(admission.current, replay, allow_simulated=True)
    assert again.current == admission.current


def test_confidence_is_uncalibrated_and_never_overrides_provenance(bundle: Bundle) -> None:
    data = bundle.response.model_dump(mode="json")
    for field in data["fields"]:
        field["confidence"] = {"value": 0.5, "basis": "fixture_assigned"}
    request = ProcessingRequest.model_validate(
        {
            **bundle.request.model_dump(),
            "content": bundle.request.content,
            "policy": {"minimum_reported_confidence": 0.9},
        }
    )
    result = process_extraction(request, data)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert all(
        r.reported_confidence is not None and not r.reported_confidence.calibrated
        for r in result.candidates
    )
    assert IssueCode.CONFIDENCE_LOW in {i.code for i in result.issues}
    data["fields"][0]["confidence"]["value"] = 1.0
    data["fields"][0]["sources"][0]["artifact_sha256"] = "f" * 64
    assert process_extraction(request, data).disposition == Disposition.REJECTED


def test_bounded_failures_do_not_retain_raw_malformed_data(bundle: Bundle) -> None:
    bad = {"SYNTHETIC-SECRET": "private"}
    result = process_extraction(bundle.request, bad)
    assert result.disposition == Disposition.REJECTED and not result.candidates
    assert "SYNTHETIC-SECRET" not in result.model_dump_json()
    other = process_extraction(bundle.request, {"other": "malformed"}, result.history)
    assert other.disposition == Disposition.REJECTED and len(other.history.receipts) == 2
    small = ProcessingRequest.model_validate(
        {
            **bundle.request.model_dump(),
            "content": bundle.request.content,
            "policy": {"max_response_bytes": 1024},
        }
    )
    assert IssueCode.LIMIT in {i.code for i in process_extraction(small, bundle.response).issues}
    capped = ProcessingRequest.model_validate(
        {
            **bundle.request.model_dump(),
            "content": bundle.request.content,
            "policy": {"max_records": 1},
        }
    )
    result = process_extraction(capped, bundle.response)
    assert result.disposition == Disposition.REJECTED and not result.history.receipts
    assert result.issues[0].code == IssueCode.HISTORY_LIMIT


def test_id_collisions_reject_without_overwriting(
    bundle: Bundle, monkeypatch: pytest.MonkeyPatch
) -> None:
    real = processing.digest
    monkeypatch.setattr(processing, "digest", lambda value: "11111111" + real(value)[8:])
    result = process_extraction(bundle.request, bundle.response)
    assert result.disposition == Disposition.REJECTED and not result.history.records
    assert IssueCode.COLLISION in {i.code for i in result.issues}


def test_stale_or_review_case_cannot_admit(bundle: Bundle) -> None:
    result = process_extraction(bundle.request, bundle.response)
    initial = Case.model_validate({**bundle.request.case.model_dump(), "state": "received"})
    with pytest.raises(ValueError, match="state"):
        admit_evidence(initial, result, allow_simulated=True)
    changed = Case.model_validate(
        {
            **bundle.request.case.model_dump(),
            "claim": {**bundle.request.case.claim.model_dump(), "narrative": "New synthetic input"},
        }
    )
    with pytest.raises(ValueError, match="stale"):
        admit_evidence(changed, result, allow_simulated=True)


def test_offline_cli_reproducibility_and_corpus_protection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    command = [sys.executable, "-m", "claims_ai.evidence", "--corpus", str(CORPUS)]
    outputs = [tmp_path / "one.json", tmp_path / "two.json"]
    for output in outputs:
        result = subprocess.run([*command, "--output", str(output)], capture_output=True, text=True)
        assert result.returncode == 0 and "SIMULATED" in result.stdout, result.stderr
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    report = json.loads(outputs[0].read_bytes())
    assert report["execution_mode"] == "SIMULATED" and not report["case_admission_performed"]
    assert len(report["attempts"]) == 82
    assert sum(a["disposition"] == "duplicate" for a in report["attempts"]) == 7
    assert all(not h["records"] for h in report["histories"])
    blocked = subprocess.run(
        [*command, "--output", str(CORPUS / "blocked.json")], capture_output=True, text=True
    )
    assert blocked.returncode == 1 and not (CORPUS / "blocked.json").exists()


@pytest.mark.parametrize("missing", ["sources", "page", "source_line"])
def test_missing_provenance_is_quarantined(bundle: Bundle, missing: str) -> None:
    data = bundle.response.model_dump(mode="json")
    if missing == "sources":
        data["fields"][0]["sources"] = []
    else:
        data["fields"][0]["sources"][0][missing] = None
    result = process_extraction(bundle.request, data)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert any(i.code == IssueCode.PROVENANCE and i.severity == "quarantine" for i in result.issues)


def test_metadata_interval_order_is_not_a_coverage_rule(truth: GroundTruth) -> None:
    index = next(
        i
        for i, d in enumerate(truth.samples[0].input_case.documents)
        if d.kind == DocumentKind.POLICY_SCHEDULE
    )
    bundle = bundle_for(truth, 0, index)
    changed = change_value(bundle, "effective_to", "2025-01-01")
    result = process_extraction(changed.request, changed.response)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert any(i.code == IssueCode.VALUE and i.field_name == "effective_to" for i in result.issues)


def test_full_receipt_budget_allows_replay_but_never_evicts_history(bundle: Bundle) -> None:
    request = ProcessingRequest.model_validate(
        {
            **bundle.request.model_dump(),
            "content": bundle.request.content,
            "policy": {"max_receipts": 1},
        }
    )
    first = process_extraction(request, bundle.response)
    assert first.disposition == Disposition.ACCEPTED
    assert (
        process_extraction(request, bundle.response, first.history).disposition
        == Disposition.DUPLICATE
    )
    data = bundle.response.model_dump(mode="json")
    data["fields"][0]["confidence"] = {"value": 0.5, "basis": "fixture_assigned"}
    full = process_extraction(request, data, first.history)
    assert full.disposition == Disposition.REJECTED and full.history == first.history
    assert full.issues[0].code == IssueCode.HISTORY_LIMIT


def test_source_claim_header_cannot_be_rebound(bundle: Bundle) -> None:
    source = bundle.request.fixture_source
    assert source is not None
    lines = list(source.lines)
    lines[2] = "claim_id: NS-CLM-00000099"
    foreign = SourceDocument.model_validate({**source.model_dump(), "lines": lines})
    request = ProcessingRequest.model_validate(
        {
            **bundle.request.model_dump(),
            "content": bundle.request.content,
            "fixture_source": foreign,
        }
    )
    result = process_extraction(request, bundle.response)
    assert result.disposition == Disposition.REJECTED and not result.candidates


def test_fixture_page_count_must_match_renderer(bundle: Bundle) -> None:
    case = Case.model_validate(
        {
            **bundle.request.case.model_dump(),
            "documents": [
                {**doc.model_dump(), "page_count": 2}
                if doc.document_id == bundle.request.document_id
                else doc
                for doc in bundle.request.case.documents
            ],
        }
    )
    request = ProcessingRequest.model_validate(
        {**bundle.request.model_dump(), "content": bundle.request.content, "case": case}
    )
    result = process_extraction(request, bundle.response)
    assert result.disposition == Disposition.REJECTED and not result.history.records


def test_unicode_expansion_is_a_controlled_quality_hold(bundle: Bundle) -> None:
    response = bundle.response.model_dump(mode="json")
    for field in response["fields"]:
        if field["name"] == "narrative":
            field["value"] = "\ufdfa" * 4000
    request = ProcessingRequest.model_validate(
        {**bundle.request.model_dump(), "content": bundle.request.content, "fixture_source": None}
    )
    result = process_extraction(request, response)
    assert result.disposition == Disposition.QUARANTINED and not result.history.records
    assert any(
        issue.code == IssueCode.VALUE and issue.field_name == "narrative" for issue in result.issues
    )
