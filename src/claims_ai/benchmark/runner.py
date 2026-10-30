"""Offline runner with pinned inputs, bounded async calls and capability-specific cohorts."""

import asyncio
import platform
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from pydantic import ValidationError

from claims_ai.benchmark.adapters import ExtractionAdapter
from claims_ai.benchmark.contracts import (
    AdapterProfile,
    BenchmarkConfig,
    BenchmarkReport,
    Capabilities,
    CohortResult,
    DocumentResult,
    DocumentStatus,
    ErrorCode,
    ExtractionRequest,
    ExtractionResponse,
    FieldSpec,
    FieldSummary,
    Rate,
)
from claims_ai.benchmark.scoring import field_kind, score_fields, summarize
from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.schema import FieldTruth
from claims_ai.dataset.validation import check_reproduction
from claims_ai.models import DocumentMetadata


def benchmark_digest() -> str:
    return sha256(
        b"".join(
            path.name.encode() + b"\x00" + path.read_bytes()
            for path in sorted(Path(__file__).parent.glob("*.py"))
        )
    ).hexdigest()


def _availability(
    response: ExtractionResponse, capabilities: Capabilities
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    missing = []
    unsupported = []
    usage = response.usage
    values = {
        "confidence": bool(response.fields)
        and all(f.confidence is not None for f in response.fields),
        "latency": response.latency_ms is not None,
        "token_usage": usage is not None
        and usage.input_tokens is not None
        and usage.output_tokens is not None,
        "cost": usage is not None and usage.cost_amount is not None,
        "page_references": bool(response.fields)
        and all(f.sources and all(s.page is not None for s in f.sources) for f in response.fields),
        "source_lines": bool(response.fields)
        and all(
            f.sources
            and all(s.source_line is not None and s.location_kind is not None for s in f.sources)
            for f in response.fields
        ),
    }
    for name, present in values.items():
        if not getattr(capabilities, name):
            unsupported.append(name)
        elif not present:
            missing.append(name)
    return tuple(missing), tuple(unsupported)


async def _document(
    root: Path,
    document: DocumentMetadata,
    expected: tuple[FieldTruth, ...],
    scenario_ids: tuple[str, ...],
    adapter: ExtractionAdapter,
    profile: AdapterProfile,
    config: BenchmarkConfig,
) -> DocumentResult:
    caps = profile.capabilities
    specs = tuple(
        FieldSpec(name=f.expected.field_name, kind=field_kind(f.expected.field_name))
        for f in expected
        if field_kind(f.expected.field_name) in caps.field_kinds
    )
    request = ExtractionRequest(
        request_id=document.document_id,
        document=document,
        fields=specs,
        content=(root / document.artifact_ref).read_bytes(),
    )
    status = DocumentStatus.OK
    response: ExtractionResponse | None = None
    schema_valid: bool | None = None
    error: ErrorCode | None = None
    missing: tuple[str, ...] = ()
    unsupported: tuple[str, ...] = ()
    if (
        document.media_type not in caps.media_types
        or document.kind not in caps.document_kinds
        or not specs
    ):
        status = DocumentStatus.UNSUPPORTED
        error = "unsupported_document"
    else:
        try:
            raw = await asyncio.wait_for(adapter.extract(request), timeout=config.timeout_seconds)
            response = ExtractionResponse.model_validate(raw)
            schema_valid = True
            if (
                response.request_id != request.request_id
                or response.document_id != document.document_id
                or response.artifact_sha256 != document.sha256
                or response.provider != profile.identity
            ):
                status, schema_valid, error = DocumentStatus.INVALID, False, "identity_mismatch"
            missing, unsupported = _availability(response, caps)
        except TimeoutError:
            status, error = DocumentStatus.TIMEOUT, "timeout"
        except ValidationError:
            status, schema_valid, error = DocumentStatus.INVALID, False, "schema_invalid"
        except Exception:
            status, error = DocumentStatus.ADAPTER_ERROR, "adapter_error"
    scores = score_fields(expected, response, caps, status)
    expected_names = {spec.name for spec in specs}
    unexpected = (
        tuple(sorted(f.name for f in response.fields if f.name not in expected_names))
        if response
        else ()
    )
    return DocumentResult(
        document_id=document.document_id,
        artifact_sha256=document.sha256,
        media_type=document.media_type,
        document_kind=document.kind,
        scenario_ids=scenario_ids,
        status=status,
        error_code=error,
        schema_valid=schema_valid,
        metadata_missing=missing,
        metadata_unsupported=unsupported,
        unexpected_fields=unexpected,
        response=response,
        fields=scores,
        metrics=summarize(scores),
    )


def _cohorts(documents: tuple[DocumentResult, ...], profile_hash: str) -> tuple[CohortResult, ...]:
    groups = {(doc.media_type, doc.document_kind) for doc in documents}
    result = []
    for media, kind in sorted(groups):
        docs = tuple(d for d in documents if (d.media_type, d.document_kind) == (media, kind))
        fields = tuple(f for doc in docs for f in doc.fields)
        names = sorted({field.name for field in fields})
        result.append(
            CohortResult(
                media_type=media,
                document_kind=kind,
                profile_sha256=profile_hash,
                documents=len(docs),
                unsupported_documents=sum(d.status == DocumentStatus.UNSUPPORTED for d in docs),
                failed_documents=sum(
                    d.status not in {DocumentStatus.OK, DocumentStatus.UNSUPPORTED} for d in docs
                ),
                schema_validity=Rate(
                    numerator=sum(d.schema_valid is True for d in docs),
                    denominator=sum(d.schema_valid is not None for d in docs),
                ),
                unexpected_fields=sum(len(d.unexpected_fields) for d in docs),
                metrics=summarize(fields),
                per_field=tuple(
                    FieldSummary(
                        name=name,
                        kind=field_kind(name),
                        metrics=summarize(tuple(f for f in fields if f.name == name)),
                    )
                    for name in names
                ),
            )
        )
    return tuple(result)


async def run_benchmark(
    root: Path, adapter: ExtractionAdapter, config: BenchmarkConfig | None = None
) -> BenchmarkReport:
    """Run only explicitly simulated adapters. No credential/configuration or live path exists."""
    config = BenchmarkConfig.model_validate(config or BenchmarkConfig())
    profile = AdapterProfile.model_validate(adapter.profile)
    if (
        profile.identity.execution_mode != "SIMULATED"
        or profile.identity.provider != adapter.provider
    ):
        raise ValueError(
            "offline benchmark requires matching explicitly SIMULATED adapter identity"
        )
    truth = check_reproduction(root)
    documents: dict[str, DocumentMetadata] = {}
    expected: dict[str, list[FieldTruth]] = {}
    scenarios: dict[str, list[str]] = {}
    for sample in truth.samples:
        for document in sample.input_case.documents:
            key = document.document_id
            documents.setdefault(key, document)
            scenarios.setdefault(key, []).append(sample.scenario_id)
            expected.setdefault(key, [])
        for field in sample.extraction_fields:
            fields = expected[field.expected.document_id]
            if field not in fields:
                fields.append(field)
    results = []
    for key in sorted(documents):
        results.append(
            await _document(
                root,
                documents[key],
                tuple(expected[key]),
                tuple(sorted(scenarios[key])),
                adapter,
                profile,
                config,
            )
        )
    hashes = {
        "manifest_sha256": sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "ground_truth_sha256": sha256((root / "ground_truth.json").read_bytes()).hexdigest(),
        "benchmark_sha256": benchmark_digest(),
    }
    runtime = {"python_version": platform.python_version(), "pydantic_version": version("pydantic")}
    run_id = sha256(
        json_bytes(
            {
                **hashes,
                **runtime,
                "profile": profile.model_dump(mode="json"),
                "config": config.model_dump(mode="json"),
            }
        )
    ).hexdigest()
    profile_hash = sha256(json_bytes(profile.model_dump(mode="json"))).hexdigest()
    return BenchmarkReport(
        run_id=run_id,
        config=config,
        profile=profile,
        manifest_sha256=hashes["manifest_sha256"],
        ground_truth_sha256=hashes["ground_truth_sha256"],
        benchmark_sha256=hashes["benchmark_sha256"],
        python_version=runtime["python_version"],
        pydantic_version=runtime["pydantic_version"],
        corpus_label_count=sum(len(s.extraction_fields) for s in truth.samples),
        unique_label_count=sum(len(f) for f in expected.values()),
        documents=tuple(results),
        cohorts=_cohorts(tuple(results), profile_hash),
    )


def write_report(report: BenchmarkReport, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("xb") as stream:
        stream.write(json_bytes(report.model_dump(mode="json")))
