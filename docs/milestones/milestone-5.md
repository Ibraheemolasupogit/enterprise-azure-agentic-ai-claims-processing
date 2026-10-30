# Milestone 5 — Document intelligence benchmark foundation

Status: **COMPLETE — offline benchmark foundation**. Harness code is implemented/tested; every fixture extraction result is **SIMULATED**. Live Azure Document Intelligence, Mistral Document AI and GPT multimodal adapters/results remain planned. Milestone 6 has not started.

## Delivered files and decisions

- New [contracts.py](../../src/claims_ai/benchmark/contracts.py), [adapters.py](../../src/claims_ai/benchmark/adapters.py), [scoring.py](../../src/claims_ai/benchmark/scoring.py), [runner.py](../../src/claims_ai/benchmark/runner.py), [CLI](../../src/claims_ai/benchmark/__main__.py) and [initializer](../../src/claims_ai/benchmark/__init__.py).
- New [scoring tests](../../tests/test_benchmark_scoring.py), [runner tests](../../tests/test_benchmark_runner.py), [benchmark guide](../quality/document-intelligence-benchmark.md) and this evidence record.
- Updated README, Makefile, architecture/quality status, roadmap and requirement traceability. No existing domain/dataset contract, generated M4 label, dependency or provider client is changed/added.

The benchmark uses an independent extraction DTO/protocol because the operational `DocumentProcessor` contract requires scanned input and is not a model-evaluation transport. A benchmark request has verified synthetic bytes and field names/kinds, never target values. Only the named oracle fixture receives ground truth; it performs no document parsing or model inference.

Each document ID is evaluated once, preserving all scenario references: 75 documents and 335 distinct field labels rather than weighting SCN-10's duplicate payload twice. The report still records the full 366 corpus annotations. Cohorts separate document kinds/media and declared identity/capability profiles. Unsupported dimensions have null rates; failures stay in supported-field denominators. No pooled provider ranking or fabricated performance result is produced.

The [guide](../quality/document-intelligence-benchmark.md#scoring-methodology--field-v1) defines exact/normalized text, numeric/date, missing-field, schema and provenance comparisons and their denominators. Confidence/token/cost/latency metadata is optional, never filled with zero when unavailable. Bounding rectangles are structurally validated but M4 has no localization truth. All policy/coverage/agent behavior remains out of scope.

## Verification

Reused Python 3.12.8, Pydantic 2.11.7, pytest 8.4.1, Ruff 0.16.4 and mypy 1.16.1. No dependencies were installed/upgraded or credentials/model services used.

- Full `make check`: **202 tests passed** (149 previous + 53 benchmark checks); Ruff formatting/lint passed; strict mypy passed across 26 Python files.
- Tests cover exact/normalization differences, strict numeric/date comparisons, missing/extra/unsupported fields, wrong provenance, invalid confidence/usage/rates, malformed/duplicate outputs, missing model version, identity mismatch, adapter errors, cooperative timeouts, unavailable metadata, live-mode rejection and CLI/output safety.
- Fixture report round-trip and repeated executions compare deterministic JSON. The PDF-only fixture profile explicitly excludes ten image documents/labels from accuracy denominators; numeric-only test support scores 21 fields and explicitly excludes 314.
- `make dataset-check` passed; all **153 M4 files** also match the existing Git blob baseline. The 366 approved annotations and generator/domain contracts are unchanged.
- Independent source CLI runs produced byte-identical SIMULATED JSON for 75 documents/335 unique labels/five cohorts. The PDF-only run reports ten unsupported image documents with null accuracy denominators, not ten successful extractions. Actual artifacts are local ignored files `outputs/benchmarks/m5-fixture-a.json`, `m5-fixture-b.json` and `m5-fixture-pdf-only.json`; all latency/usage values are null in the fixture.
- `make package` built wheel/source archives offline. Verified all six benchmark modules in the wheel and new tests/guide in the source archive. A separately installed wheel, executed outside the source tree, reproduced the source-run report byte for byte. The existing host packaging/license-validation warning remains non-blocking; no third-party dependency was installed/upgraded.
- Static documentation checks passed across **18 Markdown files, 232 local links/anchors and 83 actual Python/test symbol references**, plus table/fence/whitespace/reference checks and read-only Git diff checks. The deliverable change set is six updated files and ten new files; generated reports remain ignored local artifacts.

## Acceptance and remaining limitations

Accepted scope is the executable offline harness, common interfaces, reproducible result schema, deterministic field scoring, capability-specific aggregation and honest simulated fixture. This is not an independent accuracy benchmark: the fixture echoes its known answers, not OCR/vision predictions. No measured model latency, token consumption, price estimate or spend is reported.

Before live provider comparison: independently review/extend the development labels, define a held-out set and common support subset, verify native field/confidence/provenance mappings, choose explicit model/API versions and approve separate invocation/security/cost limits. A declared SIMULATED adapter is not a network sandbox; only the supplied fixture is exposed by this CLI. Cooperative async timeout behavior does not prove blocking-client/process isolation. No RAG, agents, MCP, APIM, coverage rules, identity service or operational ingestion is implemented.

The approved M5 request replaces the prior ingestion slot with benchmark work; ingestion moves to M6 and subsequent planned work shifts to M7–13. Architecture decisions and historical milestone records are preserved. No Azure operations, provisioning, model calls, spending, Git commits or pushes occurred. **Stop after Milestone 5.**
