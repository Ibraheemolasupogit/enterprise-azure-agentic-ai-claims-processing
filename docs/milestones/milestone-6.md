# Milestone 6 — Structured claims evidence processing

Status: **COMPLETE — deterministic local evidence foundation**. Existing extraction fixtures and CLI outputs are **SIMULATED**. No live model, scanner, API/persistence integration or autonomous case decision exists. Milestone 7 has not started.

## Files and behavior delivered

- New [contracts.py](../../src/claims_ai/evidence/contracts.py), [normalization.py](../../src/claims_ai/evidence/normalization.py), [processing.py](../../src/claims_ai/evidence/processing.py), [offline CLI](../../src/claims_ai/evidence/__main__.py) and [initializer](../../src/claims_ai/evidence/__init__.py).
- New [test_evidence.py](../../tests/test_evidence.py), [processing guide](../architecture/structured-evidence-processing.md) and this evidence record.
- Updated README, Makefile, architecture status, roadmap and traceability. Existing domain/dataset/benchmark modules, generated labels, prior tests, dependency declarations and interfaces remain unchanged.

Typed request/result/envelope/history/receipt/admission models compose M2/M5 contracts. Mapping validates source identity/bytes/claim ownership, quoted page/line/caption provenance, allowed/required field names, identifier bindings and canonical numeric/date/text representations. Provider/model/adapter/mode, all source references, exact raw text and uncalibrated confidence are preserved alongside existing `Evidence`.

Whole-document dispositions and actionable issues prevent partial promotion after missing/malformed/conflicting/duplicate/untrusted input. Document-scoped policy metadata avoids false conflicts between draft versions. Frozen histories append accepted records/attempt receipts, detect record-ID collisions and return idempotent retries without growth; capacity rejections preserve prior data. Guarded case admission is a separate in-memory operation requiring accepted receipts, valid document metadata, appropriate state/current claim and explicit simulation opt-in. It cannot close a claim or change scan status.

The [guide](../architecture/structured-evidence-processing.md) defines exact normalization, limits, trust assumptions and admission semantics. Expected identity/ownership/scan assertions are not authenticated by this library. Independent text verification is limited to reproducibly rendered fixtures; other inputs remain held pending a trusted source-index implementation. Confidence is not a probability, and quality holds never compute coverage/settlement outcomes.

## Verification

Reused Python 3.12.8, Pydantic 2.11.7, pytest 8.4.1, Ruff 0.16.4 and mypy 1.16.1. No third-party dependency was installed/upgraded.

- `make check`: **251 tests passed** (202 previous + 49 new evidence checks), Ruff format/lint passed, strict mypy passed across 32 Python files.
- New tests cover valid mapping/admission and immutable raw/provider metadata, numeric/date/identifier normalization, Unicode expansion limits, malformed/oversized payloads, wrong envelope/hash/page/line/source/claim data, missing/duplicate/untrusted fields, source-text/scan uncertainty, interval metadata ordering, conflicting versions/values, confidence triage, repeated processing/admission, history budgets, ID collisions, state/staleness and CLI/corpus safety.
- `make dataset-check` passed for all 12 scenarios; all 153 corpus files also matched their tracked Git blob hashes. Domain/dataset/benchmark modules, prior tests and dependency declarations have no changes. The rerun M5 report matched its prior artifact byte-for-byte (`bdc5031bc5ec7a99619db618f87f9122a5649dbe71c4b46ba3bd9afedb8bb465`).
- Two CLI runs (`outputs/evidence/m6-verified-a.json` and `m6-verified-b.json`) matched byte-for-byte: SHA-256 `92b00d6b8aa5e8655a510342168756749f7ae192c6d783d3f25bc872ecac372e`. Each records **82 attempts: 75 quarantined, seven duplicates, 334 proposals, zero accepted-history records and no case admission**; one conflict and one unsupported instruction-field issue are present. These are fixture-processing counts, not extraction-accuracy measurements.
- `make package` built the wheel and source archive offline without fetching dependencies. The wheel contains all five evidence modules; the source archive includes new tests/docs and all 153 corpus files. Installing only this project wheel into an isolated temporary target (`--no-index --no-deps`) and running its CLI produced the identical report. Existing third-party packages were reused.
- Documentation validation checks local links/anchors, named test references, Markdown structure/status consistency and whitespace; `git diff --check` checks tracked changes. These checks do not constitute live extraction/scanning or durable audit evidence.

## Limitations and acceptance

The offline CLI retains original M4 quarantine statuses: mapped proposals are inspectable but no original case is admitted or scan-cleared. Accepted/admitted paths are tested using explicit synthetic clearance assertions; simulation opt-in is mandatory. Source quote verification currently covers single-page generated fixtures; multi-page/general PDF/image text indexing, semantic grounding, bounding-box localization and scanner/authentication integration remain unimplemented. The allowlist is not a prompt-injection classifier; narrative remains untrusted data.

History/receipts are local caller-held data with bounded capacity, not durable queues, signed attestations, concurrent transactions or legal audit retention. Corrected conflicting evidence requires a later authorized workflow; old values are never silently selected/replaced. Provider confidence calibration, approved thresholds, evidence checklists and policy rules remain future decisions. No changes to M4 truth or M5 scoring are authorized by this milestone.

Acceptance is met for typed deterministic mapping, validation/holds, immutable local history, guarded admission and reproducible synthetic execution. The prior roadmap's broader ingestion slot is refined: remaining intake/scanning/persistence work moves to planned M7, later work shifts accordingly. No Azure/model invocation, cloud resources/spend, Git commits or pushes occurred. **Stop after Milestone 6.**
