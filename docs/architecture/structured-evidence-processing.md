# Structured claims evidence processing

Status: **IMPLEMENTED deterministic local validation/admission functions; fixture extraction remains SIMULATED**. No live extractor, malware scanner, API, database, RAG or coverage engine is implemented. Existing domain, dataset and benchmark contracts/semantics are unchanged.

## Entry points and trust boundary

[process_extraction](../../src/claims_ai/evidence/processing.py) consumes a typed `ProcessingRequest`, a decoded extraction response and an optional immutable `EvidenceHistory`. It reuses M5 `ExtractionResponse`/`ProviderIdentity`/`SourceReference`/`Confidence` and maps valid proposals into existing domain `Evidence`, wrapped by `EvidenceRecord`. [Contracts](../../src/claims_ai/evidence/contracts.py) preserve the additional raw value, all source references, provider/model/adapter/execution identity, reported confidence, normalization version, quality metadata and full record fingerprint.

The caller must supply an authoritative `Case`, document association, expected provider/request identity and scan status. Those assertions are checked for consistency, not authenticated. Hashes and receipts are neither authorization tokens nor signatures. Do not import an untrusted serialized history as authoritative state. Entra, scanner attestations and durable persistence remain future integrations.

Processing returns proposals and controlled issues; it never changes a case, scan status or outcome. Whole-document disposition is `accepted`, `quarantined` or `rejected`; an exact prior operation returns `duplicate` with its original disposition. **Rejected means extraction rejected, not claim denied.** Warning-only results may be structurally accepted without implying factual truth or a calibrated model confidence.

## Validation and normalization

1. Revalidate trusted context/history and enforce response-byte/field-count limits. Decode only JSON-shaped mappings or the existing typed extraction response; malformed bodies yield controlled codes without raw error text. Duplicate response field names are held before mapping.
2. Bind the document to the claim; compare actual content length/SHA-256 with case metadata and extraction envelope/request/provider/model identity. Check every source's document/hash/page, line/caption kind and bounds. Missing references are quarantined; contradictory identities, out-of-range or false references are rejected.
3. Independent source-text verification currently supports M4's one-page PDF/PNG fixture source records: header document/claim identity, media/page count, exact re-rendered bytes and field-line/caption text must match. General documents without this verifier remain quarantined with structural-only proposals. This is not a general PDF parser, OCR engine, malware scan or proof of semantic truth; rectangles are structurally validated, not independently localized.
4. Apply the explicit field schema for claim forms, estimates, schedules, wording and damage captions. Endorsements/unknown fields are held, not guessed. Required fields are extraction completeness requirements, not contractual evidence or coverage requirements. `instruction_payload` is not admitted by this schema; ordinary narrative remains untrusted data. This is an allowlist, not an injection detector.
5. Normalize syntactically using [normalization.py](../../src/claims_ai/evidence/normalization.py). Identifiers must retain valid uppercase synthetic prefixes; policy/vehicle identifiers must match the case. Nonnegative money strings accept valid comma groups and redundant trailing zeros, produce two decimal places and reject excess precision, exponents, currency symbols and oversized representations without rounding. ISO dates are validated, aware timestamps become UTC `Z`, and schedule intervals must be increasing. GBP/GB/motor-damage values reflect existing domain scope; loss-date coverage, excesses, limits and payouts are never computed.
6. Compare canonical shared claim fields against intake facts and accepted history; conflicting values are quarantined for human review. Policy-version/date fields are scoped to their individual document, so the two draft versions do not falsely conflict. Estimates/claim amounts and separate damage images are not compared using invented business rules. No preferred fact overwrites a previous value.

Generic text uses NFKC and collapsed whitespace while preserving case; damage captions become lowercase underscores. The envelope retains the exact `raw_value`, because existing domain `Evidence.observed_value` trims outer whitespace. The normalizer is a separate `evidence-v1` contract and does not change M5's scoring rules or M4 labels.

## Confidence, quarantine and limits

Reported confidence and its original M5 basis are retained with `calibrated=false`; missing confidence stays null with an actionable warning. The default applies no numeric confidence threshold. An explicitly supplied review threshold can hold low/missing scores, never override identity/source/scan failures or create a coverage decision. `QualityMetadata` distinguishes fixture-render verification from structural-only references and unavailable versus reported-uncalibrated confidence.

Missing/invalid values, uncertain references, unsupported fields, conflicts and unscanned documents cannot partially promote the rest of that response. Valid proposals may still be returned for inspection; **only the accepted receipt/history and guarded admission function authorize this layer's next step**. Do not append proposals manually. Malformed/oversized/tampered responses are rejected. Rejected document status cannot be cleared by this code; quarantine/closed-case workflow release remains governed by M2's supervisor transitions.

Defaults: 128 KiB serialized response, 64 fields, 1,024 accepted records and 128 receipts per caller-held history. Configurable hard maxima are 1 MiB, 128 fields, 2,048 records and 256 receipts. At capacity, return a controlled rejection and the previous history unchanged; never evict accepted evidence silently. A replay is still permitted at capacity. These are local allocation/history limits, not a network request parser, process sandbox or durable quarantine queue. The upstream API must enforce wire-size limits before decoding.

Issues expose stable codes, optional field names, severity and actions (`verify_source`, `request_fields`, `human_review`, etc.), never raw malformed payloads/exceptions. Rejected raw bodies are not retained; digest/issue receipts and returned valid proposals support review. Any future storage/viewer needs access control and escaping of the untrusted raw strings.

## Immutable history and admission

Histories use frozen models/tuples. Accepted records append; old records never change. Quarantined/rejected attempts append bounded metadata receipts and preserve accepted history. Processing fingerprints pin claim/document/bytes, provider, semantic response fields, source index and processing policy; field/source ordering is canonicalized and volatile latency/token/cost metadata is excluded. Exact retries return the original receipt outcome without growing history. Non-JSON failures use a stable sentinel; distinct malformed JSON bodies retain distinct digests. Changed confidence/provider/validation policy/value creates a new attempt. Future normalization changes must version the processing policy before replaying existing histories.

Evidence IDs fit the existing eight-character `NS-EVD` suffix; full SHA-256 is retained and collisions reject instead of overwriting. Equal normalized values may coexist as distinct provenance/producer observations; different values in the same comparison scope require review. This is local deterministic idempotency, not database uniqueness, concurrency control or tamper-proof audit retention.

[admit_evidence](../../src/claims_ai/evidence/processing.py) accepts only a complete accepted receipt for the current claim snapshot in `extracting`/`assessing`. It resolves every record, requires accepted document metadata through existing `Case` validation, appends new IDs and increments the revision once only when something changes. Repeated admission is a no-op. Existing review/closed states, stale claim input and held/rejected receipts are blocked. Simulation requires explicit `allow_simulated=True`; records retain `simulated_extraction` flags and the admission is labeled SIMULATED. This opt-in is used by local unit tests with declared scan assertions, not by the CLI.

`EvidenceAdmission` returns previous/current snapshots and an operation key. It does not call the existing repository port: future persistence must atomically compare the previous revision and store the case, evidence envelopes/history and audit. No adapter/concurrent update guarantee is implemented. Human case outcomes remain solely in the existing reviewer workflow.

## Reproducible offline demonstration

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.evidence --corpus data/synthetic/motor/v1 --output outputs/evidence/processing.json
```

Choose a new output file; overwrites and paths within the corpus are refused. The CLI validates M4 reproduction, obtains M5 oracle responses, and processes the original quarantined cases without changing them. It does not use ground-truth values to validate normalization/ownership; the fixture supplies extraction data and byte-verified source sidecars supply quotes. Reports are timestamp-free, versioned, fingerprinted, labeled SIMULATED and contain untrusted synthetic proposals.

Expected current demonstration: 82 document attempts, 75 quarantined operations, seven duplicate retries, 334 mapped proposals and zero accepted-history records/case admissions. The conflict scenario produces a conflict issue; the instruction field is held as unsupported. All other scan gates still apply. A successful CLI is not evidence of scanning, real extraction, admission or model safety performance. [M6 evidence](../milestones/milestone-6.md) records actual checks; [traceability](../business/traceability-matrix.md#milestone-6-evidence-processing) records remaining gaps.
