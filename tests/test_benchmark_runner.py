"""Offline harness behavior with explicit test doubles; no provider implementation."""

import asyncio
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest

from claims_ai.benchmark.adapters import FixtureAdapter
from claims_ai.benchmark.contracts import (
    AdapterProfile,
    BenchmarkConfig,
    BenchmarkReport,
    DocumentStatus,
    ExtractionRequest,
    ExtractionResponse,
    FieldKind,
)
from claims_ai.benchmark.runner import run_benchmark, write_report
from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.schema import GroundTruth

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/synthetic/motor/v1"


@pytest.fixture(scope="module")
def truth() -> GroundTruth:
    return GroundTruth.model_validate_json((CORPUS / "ground_truth.json").read_bytes())


@pytest.fixture(scope="module")
def report(truth: GroundTruth) -> BenchmarkReport:
    return asyncio.run(run_benchmark(CORPUS, FixtureAdapter(truth)))


class TestDouble(FixtureAdapter):
    __test__ = False

    def __init__(self, truth: GroundTruth, behavior: str) -> None:
        super().__init__(truth)
        self.behavior = behavior
        self.requests: list[ExtractionRequest] = []

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        self.requests.append(request)
        if self.behavior == "timeout":
            await asyncio.sleep(1)
        if self.behavior == "error":
            raise RuntimeError("SYNTHETIC-SECRET-EXCEPTION")
        response = await super().extract(request)
        data = response.model_dump()
        data["fields"] = list(data["fields"])
        if self.behavior == "malformed":
            return cast(ExtractionResponse, {"fields": "malformed"})
        if self.behavior == "identity":
            data["document_id"] = "NS-DOC-00000099"
        if self.behavior == "model_missing":
            data["provider"].pop("model_version")
        if self.behavior == "duplicate_field":
            data["fields"].append(data["fields"][0])
        if self.behavior == "missing_field":
            data["fields"].pop()
        if self.behavior == "unexpected":
            data["fields"].append({"name": "unknown_field", "value": "SYNTHETIC"})
        if self.behavior == "confidence":
            data["fields"][0]["confidence"] = {"value": 2, "basis": "provider_reported"}
        return cast(ExtractionResponse, data)  # Deliberate SDK-boundary test double.


def test_fixture_report_is_simulated_unique_and_stratified(report: BenchmarkReport) -> None:
    assert (
        report.execution_mode == "SIMULATED" and report.profile.identity.provider.value == "fixture"
    )
    assert report.corpus_label_count == 366 and report.unique_label_count == 335
    assert len(report.documents) == 75 and len(report.cohorts) == 5
    assert all(doc.status == DocumentStatus.OK and doc.schema_valid for doc in report.documents)
    assert all(
        doc.metrics.exact.value == 1 and doc.metrics.normalized_text.value == 1
        for doc in report.documents
    )
    assert sum(c.metrics.exact.denominator for c in report.cohorts) == 335
    assert all(
        doc.response is not None and doc.response.latency_ms is None and doc.response.usage is None
        for doc in report.documents
    )
    assert all("latency" in doc.metadata_unsupported for doc in report.documents)
    assert BenchmarkReport.model_validate_json(report.model_dump_json()) == report
    duplicate_docs = [doc for doc in report.documents if "SCN-10" in doc.scenario_ids]
    assert len(duplicate_docs) == 7 and all("SCN-01" in doc.scenario_ids for doc in duplicate_docs)


def test_deterministic_results(truth: GroundTruth, report: BenchmarkReport) -> None:
    again = asyncio.run(run_benchmark(CORPUS, FixtureAdapter(truth)))
    assert json_bytes(report.model_dump(mode="json")) == json_bytes(again.model_dump(mode="json"))


def test_unsupported_documents_do_not_enter_accuracy_denominator(truth: GroundTruth) -> None:
    adapter = TestDouble(truth, "ok")
    adapter._profile = FixtureAdapter(truth, pdf_only=True).profile
    report = asyncio.run(run_benchmark(CORPUS, adapter))
    assert len(adapter.requests) == 65
    image_cohort = next(c for c in report.cohorts if c.media_type == "image/png")
    assert image_cohort.unsupported_documents == 10
    assert image_cohort.metrics.exact.denominator == 0 and image_cohort.metrics.exact.value is None
    assert sum(c.metrics.exact.denominator for c in report.cohorts) == 325


def test_unsupported_field_capabilities_are_excluded(truth: GroundTruth) -> None:
    adapter = TestDouble(truth, "ok")
    adapter._profile = AdapterProfile.model_validate(
        {
            **adapter.profile.model_dump(),
            "capabilities": {
                **adapter.profile.capabilities.model_dump(),
                "field_kinds": ["numeric"],
            },
        }
    )
    report = asyncio.run(run_benchmark(CORPUS, adapter))
    assert all(
        field.kind == FieldKind.NUMERIC for request in adapter.requests for field in request.fields
    )
    assert sum(c.metrics.exact.denominator for c in report.cohorts) == 21
    assert sum(c.metrics.unsupported_fields for c in report.cohorts) == 314


@pytest.mark.parametrize(
    "behavior,status,code",
    [
        ("malformed", DocumentStatus.INVALID, "schema_invalid"),
        ("model_missing", DocumentStatus.INVALID, "schema_invalid"),
        ("duplicate_field", DocumentStatus.INVALID, "schema_invalid"),
        ("confidence", DocumentStatus.INVALID, "schema_invalid"),
        ("identity", DocumentStatus.INVALID, "identity_mismatch"),
        ("timeout", DocumentStatus.TIMEOUT, "timeout"),
        ("error", DocumentStatus.ADAPTER_ERROR, "adapter_error"),
    ],
)
def test_clean_failures_keep_supported_fields_in_denominator(
    truth: GroundTruth,
    behavior: str,
    status: DocumentStatus,
    code: str,
) -> None:
    report = asyncio.run(
        run_benchmark(CORPUS, TestDouble(truth, behavior), BenchmarkConfig(timeout_seconds=0.005))
    )
    assert all(d.status == status and d.error_code == code for d in report.documents)
    assert sum(c.metrics.exact.denominator for c in report.cohorts) == 335
    assert all(c.metrics.exact.value == 0 for c in report.cohorts)
    assert "SYNTHETIC-SECRET-EXCEPTION" not in report.model_dump_json()


def test_missing_fields_and_unexpected_fields_are_visible(truth: GroundTruth) -> None:
    missing = asyncio.run(run_benchmark(CORPUS, TestDouble(truth, "missing_field")))
    assert all(d.schema_valid is True and d.metrics.missing_fields == 1 for d in missing.documents)
    assert sum(c.metrics.exact.numerator for c in missing.cohorts) == 260
    extra = asyncio.run(run_benchmark(CORPUS, TestDouble(truth, "unexpected")))
    assert sum(c.unexpected_fields for c in extra.cohorts) == 75


def test_supported_but_missing_metadata_is_not_zero_filled(truth: GroundTruth) -> None:
    adapter = TestDouble(truth, "ok")
    adapter._profile = AdapterProfile.model_validate(
        {
            **adapter.profile.model_dump(),
            "capabilities": {
                **adapter.profile.capabilities.model_dump(),
                "confidence": True,
                "latency": True,
                "token_usage": True,
                "cost": True,
            },
        }
    )
    report = asyncio.run(run_benchmark(CORPUS, adapter))
    assert all(
        set(d.metadata_missing) == {"confidence", "latency", "token_usage", "cost"}
        for d in report.documents
    )
    assert all(
        d.response is not None and d.response.usage is None and d.response.latency_ms is None
        for d in report.documents
    )


def test_live_execution_is_rejected_before_any_adapter_call(truth: GroundTruth) -> None:
    adapter = TestDouble(truth, "ok")
    adapter._profile = AdapterProfile.model_validate(
        {
            **adapter.profile.model_dump(),
            "identity": {**adapter.profile.identity.model_dump(), "execution_mode": "LIVE"},
        }
    )
    with pytest.raises(ValueError, match="SIMULATED"):
        asyncio.run(run_benchmark(CORPUS, adapter))
    assert not adapter.requests


def test_requests_contain_no_answer_values(truth: GroundTruth) -> None:
    adapter = TestDouble(truth, "ok")
    asyncio.run(run_benchmark(CORPUS, adapter))
    for request in adapter.requests:
        data = request.model_dump(mode="json")
        assert "content" not in data and "ground_truth" not in data
        assert all(
            set(field) == {"schema_version", "synthetic", "name", "kind"}
            for field in data["fields"]
        )


def test_report_write_is_exclusive(tmp_path: Path, report: BenchmarkReport) -> None:
    output = tmp_path / "report.json"
    write_report(report, output)
    before = output.read_bytes()
    with pytest.raises(FileExistsError):
        write_report(report, output)
    assert output.read_bytes() == before


def test_cli_is_reproducible_and_cannot_write_into_corpus(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    command = [sys.executable, "-m", "claims_ai.benchmark", "--corpus", str(CORPUS)]
    outputs = [tmp_path / "one.json", tmp_path / "two.json"]
    for output in outputs:
        result = subprocess.run([*command, "--output", str(output)], capture_output=True, text=True)
        assert result.returncode == 0 and "SIMULATED" in result.stdout, result.stderr
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    blocked = subprocess.run(
        [*command, "--output", str(CORPUS / "blocked.json")], capture_output=True, text=True
    )
    assert blocked.returncode == 1 and not (CORPUS / "blocked.json").exists()
