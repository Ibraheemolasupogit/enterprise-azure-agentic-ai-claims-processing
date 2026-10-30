# Document intelligence benchmark foundation

Status: **IMPLEMENTED offline harness; fixture extraction results SIMULATED**. Azure Document Intelligence, Mistral Document AI and GPT multimodal adapters are typed interfaces only. No service/model invocation, vendor capability claim, performance comparison or spending is included.

## Run the offline harness

From the repository root using the existing Python 3.12 environment:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.benchmark --corpus data/synthetic/motor/v1 --output outputs/benchmarks/fixture.json
PYTHONPATH=src .venv/bin/python -m claims_ai.benchmark --corpus data/synthetic/motor/v1 --output outputs/benchmarks/fixture-pdf-only.json --pdf-only
```

Each output must be a new file. The CLI refuses overwrites and output paths inside the corpus. Generated reports live in ignored `outputs/`; they are reproducible local artifacts, not checked-in provider results. `make benchmark-check` runs the benchmark-focused tests; `make check` includes them in the full suite. No additional dependency, credentials, endpoint or model name is needed.

The fixture adapter **echoes the known M4 extraction labels**, including exact source references. Its successful scores establish harness plumbing only: they are not OCR, vision, provider accuracy, calibration or throughput measurements. `--pdf-only` deliberately restricts this same fixture's declared media capability; it says nothing about any vendor's actual support. The only adapter selectable through the CLI is the fixture.

## Inputs and contracts

The runner first validates exact [M4 corpus reproduction](../../data/synthetic/motor/README.md), then evaluates each unique document ID once: **75 documents and 335 distinct field labels**. SCN-01/SCN-10 references remain attached to the same seven documents; their repeated submission does not increase scoring weight. The report separately records all 366 corpus annotations. Missing documents in M4 scenarios are not invented as extraction inputs; document/evidence completeness and review routing remain outside this field benchmark.

Existing domain/dataset contracts are unchanged. The [benchmark contracts](../../src/claims_ai/benchmark/contracts.py) define:

| Contract | Meaning |
| --- | --- |
| `ExtractionRequest` / `FieldSpec` | Purpose-bound synthetic request, pinned document metadata, verified bytes and requested names/value kinds. Bytes are excluded from normal serialization. No expected values, truth file paths or expected source locations are supplied to a general adapter. |
| `AdapterProfile` / `Capabilities` / `ProviderIdentity` | Provider, explicit model/adapter versions, execution mode, supported media/document/value kinds and optional metadata/provenance support. Capabilities are adapter declarations requiring later live verification. Page/line/confidence/usage support is not assumed for vendor interfaces. |
| `ExtractionResponse` / `ExtractedField` | Request/document/hash identity, field strings or null, optional confidence and source references; unique field names. Raw SDK output must be normalized into this contract. Numeric values use text to avoid silent binary-float coercion. |
| `SourceReference` / `Confidence` | Document/hash/page, optional normalized rectangle or source-line/caption location; optional confidence on a 0–1 scale with declared basis and `calibrated=false`. Adapters must document any native confidence conversion; scores are not comparable probabilities. |
| `Usage` | Optional nonnegative input/output token counts and an explicit decimal cost string/currency pair (currently GBP/USD/EUR). Absent is null; an explicitly reported zero is different. No prices, estimates or cost totals are derived. |
| `FieldScore` / `DocumentResult` / `CohortResult` | Field comparisons, missing/failed/unsupported states, schema/failure/metadata information, unexpected-field counts and per-document/per-field/cohort metrics. |
| `BenchmarkReport` / `Rate` | Versioned report with SIMULATED mode, provenance/configuration fingerprints, environment versions and numerator/denominator/value rates. Zero-denominator values are null. |

Benchmark [adapter interfaces](../../src/claims_ai/benchmark/adapters.py) are `ExtractionAdapter`, `AzureDocumentIntelligenceAdapter`, `MistralDocumentAIAdapter` and `GPTMultimodalAdapter`. They share one async request/response protocol; no vendor SDK/client is present. `FixtureAdapter` is the sole concrete adapter and intentionally receives truth separately. The existing operational `DocumentProcessor` protocol still requires scanned/validated input; this offline fixture harness does not implement or bypass that application workflow. All corpus scan statuses remain quarantined and no operational evidence or assessment is created.

## Scoring methodology — field-v1

All comparisons are deterministic functions in [scoring.py](../../src/claims_ai/benchmark/scoring.py). The response schema validates extraction structure, not an insurance claim's legal/domain validity. No LLM judge, fuzzy semantic matching or policy/financial rules run.

| Metric | Definition and denominator |
| --- | --- |
| Exact match | Predicted string equals M4 `observed_value`, character-for-character; denominator is every eligible labeled field. |
| Normalized text accuracy | Compare against M4 `normalized_value` (or observed value if absent), using Unicode NFKC, case folding and collapsed whitespace. Only `damage_location` additionally treats underscores as spaces, matching M4's explicit caption rule. Punctuation/signs remain significant. This lexical metric is separate from numeric/date correctness. |
| Numeric correctness | For `claimed_amount`/`estimate_amount`, compare exact Decimal values after accepting valid comma thousands groups and surrounding whitespace. No tolerance, rounding, currency-symbol guessing, exponent or nonfinite values. Non-numeric fields have no numeric denominator. This is a field comparison, not a settlement calculation. |
| Date correctness | `effective_from`/`effective_to` require valid ISO `YYYY-MM-DD`; `loss_at`/`estimate_issued_at` require timezone-aware ISO datetimes representing the same UTC instant. No locale/date-format guessing. Other fields are excluded. |
| Provenance correctness | When page references are declared supported, a present field must provide at least one source and **all** reported sources must match document ID, artifact hash and expected page. This verifies references, not semantic grounding. |
| Source-location correctness | When line references are declared supported, all sources must also match the M4 one-based source line and `pdf_line`/`image_caption` kind. M4 has no bounding-box truth, so supplied rectangles are stored/validated structurally but not scored for localization accuracy. |
| Schema validity | A response must validate against the common Pydantic schema and match request/document/hash/provider/model identity. Missing/blank field values are allowed structurally and scored as extraction failures. Duplicate names, invalid confidence/types or absent required identity are invalid responses. The denominator is returned/validation-attempted responses; timeout/unsupported/error-without-response has schema validity null. |

Absent fields, null values and whitespace-only strings fail eligible exact/normalized/numeric/date/reference comparisons. Document failures (invalid response, timeout or adapter error) also score false for every eligible field; they cannot disappear from accuracy denominators. A missing field increments `missing_fields`; a failed document increments `failed_fields`. Unexpected field names are counted separately, not silently ignored or rewarded; no precision/F1 score is claimed.

Unsupported media/document types or field kinds are not invoked/scored and remain explicitly visible with null rates and unsupported counts. Aggregation groups by **media type + document kind + the complete identity/capability profile fingerprint**. Each cohort includes per-field summaries. There is no single pooled cross-document/provider accuracy score. Compare future providers only over matched document/field/provenance support; do not interpret exclusion as correctness or compare profiles with different coverage without accounting for it.

## Failures and metadata

The runner uses a configured async timeout (default five seconds) and controlled error codes: `schema_invalid`, `identity_mismatch`, `timeout`, `unsupported_document`, `adapter_error`. It omits exception text/raw malformed outputs from errors, so embedded instructions or accidental secrets do not become operational logs. Valid synthetic responses and expected field values are retained in JSON as **untrusted data**; any later viewer must escape them. CLI output is a short SIMULATED summary only.

Optional metadata has separate `metadata_missing` (declared supported but unavailable) and `metadata_unsupported` lists. No-confidence/no-token/no-cost/no-latency values remain null; the fixture reports no measured performance, usage or cost. Availability warnings do not change field correctness or magically validate a model version; required identity omissions are invalid responses.

A document status of `ok` means a valid response, not that every field is correct or metadata is complete. Inspect its field metrics, missing/unexpected counts and availability warnings. Usage/latency remain per-document metadata; no aggregate currency, token-price or latency comparison is inferred.

Timeouts require cooperative asynchronous adapters; this is not isolation for a blocking SDK or malicious Python plugin. The runner rejects declared LIVE execution before calls, and the CLI provides no live/plugin-loading path. SIMULATED identity is an adapter contract, not an operating-system network sandbox. Actual future adapters require separate approval, configuration, support verification and integration tests.

## Reproducibility and limitations

Report JSON is sorted, versioned and timestamp-free. It pins corpus manifest/ground-truth hashes, benchmark source hash, scoring version, capability profile, timeout configuration and Python/Pydantic versions. `run_id` identifies that evaluation configuration, not a unique attempt, signed result or promise of deterministic future models. Reports from the supplied fixture are byte-identical across repeated executions in the recorded environment; only fixture determinism is claimed.

The M4 data is a small public development corpus with simple English PDFs/schematics, no realistic scans, handwriting or actual photographs, no independent held-out labels and no approved coverage outcomes. This benchmark tests field extraction and reference structure only. It does not evaluate policy selection, RAG, coverage/routing decisions, prompt-injection detection, reviewer quality or distributed operations. The malicious document remains untrusted field text; copying it is not executing it or proving a safety defense. See [M5 evidence](../milestones/milestone-5.md) and [traceability](../business/traceability-matrix.md#milestone-5-benchmark-evidence).
