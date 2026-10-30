# Milestone 4 — Synthetic motor claims dataset and ground truth

Status: **COMPLETE — offline synthetic dataset/tooling scope**, 2026-10-30. No live document processor, RAG, policy/financial engine, agent, gateway, API or cloud integration is implemented. Milestone 5 has not started.

## Delivered files

- [Dataset guide](../../data/synthetic/motor/README.md) and `data/synthetic/motor/v1/`: 12 scenarios/submissions, 11 distinct claims, 65 PDF documents, 10 schematic PNGs, 75 source sidecars, ground truth, exported JSON Schema and manifest (153 generated files).
- [schema.py](../../src/claims_ai/dataset/schema.py): frozen versioned ground-truth/source/manifest contracts composing existing domain models; cross-record integrity and explicit unapproved/null-outcome annotations.
- [generator.py](../../src/claims_ai/dataset/generator.py), [render.py](../../src/claims_ai/dataset/render.py), [validation.py](../../src/claims_ai/dataset/validation.py), [CLI](../../src/claims_ai/dataset/__main__.py), [initializer](../../src/claims_ai/dataset/__init__.py): seeded authoring, fixed-layout PDF/PNG output, source/byte/date/schema checks and exact reproduction; no new dependencies.
- [test_dataset.py](../../tests/test_dataset.py): generation, contract compatibility, required scenario distinctions, byte integrity, bad annotations, untrusted text, seed/Decimal independence, safe fresh-directory writes and CLI checks.
- Updated [Makefile](../../Makefile) (`dataset-check`) and [MANIFEST.in](../../MANIFEST.in) (corpus included in source distributions); Python/dependency constraints and existing foundation modules/tests unchanged.
- Updated README, architecture/requirements status, quality baseline, [traceability](../business/traceability-matrix.md#milestone-4-dataset-evidence) and [roadmap](roadmap.md). Existing acceptance IDs and historical milestone records are retained.

## Inventory and truth boundaries

The [scenario table](../../data/synthetic/motor/README.md#scenario-inventory) records straightforward front/side damage, missing estimate/image, conflicting loss dates, expired metadata, wrong submitted version, high-value claim, draft exclusion candidate, exact duplicate submission, malicious document instructions and an exact version boundary.

Seed `20261030` derives synthetic IDs/ordinary quoted amounts using SHA-256; text/layout/scenario choices and timestamps are fixed. Repeated generation with the same code/runtime/seed has identical paths and bytes. No real people, policies, images or external inputs are sampled. PNGs are labeled schematic illustrations, not real photographs. PDFs are static digitally generated single pages with synthetic/draft warnings; no interactive form or signature validity is implied.

The `motor-v1` ground truth is versioned and marked development-only. It supplies 366 source-linked extraction labels (335 distinct-claim labels), fixture presence completeness, two draft policy versions per distinct claim and authored triage labels. Duplicate SCN-10 reuses the original case/documents/labels rather than creating a second claim identity. Raw and normalized source values, page/line/caption, real artifact hashes and source sidecars are independently checked. Case documents remain quarantined and `Case.evidence` is empty; standalone annotation `Evidence` objects do not certify extraction or scanning.

Fixture metadata intervals, including outside-period and wrong-version labels, are objective authoring facts; they do not decide coverage. All coverage outcomes are null, rule-pack references unapproved and index references inactive. Draft X01 is a hypothetical policy interpretation requiring owner approval. High-value routing is a scenario label, not a monetary rule. Handler triage is not approval of an undetermined assessment; existing supervisor guards remain unchanged.

Malicious instructions are visible untrusted field data with authored injection/escalation labels. No document text is executed, used as a system prompt or granted operational tool authority. No injection detector or model safety evaluation is claimed.

## Verification

The implementation reuses Python 3.12.8/Pydantic 2.11.7, pytest 8.4.1, Ruff 0.16.4 and mypy 1.16.1 already present. No dependency was installed/upgraded. The following checks passed; none represents insurance/model performance.

- `make check`: **149 tests passed** (115 existing foundation + 34 dataset checks), Ruff format/lint passed, strict mypy passed across 18 Python files.
- `make dataset-check`: schema/reference/date/identifier/hash/source-label integrity plus exact byte regeneration of the canonical corpus passed.
- Two independent fresh-directory CLI generations matched all **153 canonical files byte for byte**. Existing output directories are refused rather than overwritten/deleted; alternate-seed and Decimal-context checks passed.
- Native macOS PDFKit independently opened/rendered all 65 PDFs, verified one page and every source line, and checked character bounds. All-page contact-sheet and representative full-page visual review found no clipping/overlap. Existing Pillow independently decoded/verified all 10 PNGs; illustrative content was visually inspected. These are artifact checks, not OCR results.
- The PDF skill's packaged marker script, ReportLab/Poppler and PDF Python parsers were unavailable. A small standard-library encoder and existing macOS PDFKit provided generation/independent inspection without adding dependencies. Temporary QA files stay outside the corpus/repository deliverables.
- `make package`: wheel and source distribution built without dependency downloads. Verified all six current dataset modules in the wheel and every corpus/guide payload in the source distribution. The pre-existing host packaging/license-validation warning remains non-blocking as documented in M2.
- Markdown links/symbols and read-only Git whitespace/diff checks passed. Existing domain/lifecycle/config/logging/protocol modules, foundation tests, pyproject dependency constraints and Git metadata were not modified by this milestone. Temporary generation/render QA remains outside deliverables.

## Limits, decisions and next review

This is a small single-author development corpus, not an independently labeled held-out golden set or the planned 60-case evaluation suite. Simple layouts, English text and schematic images do not establish noisy-scan, handwriting, real-photo, model, fairness, production-privacy or operational reliability performance. No bounding-box truth, endorsements, external communications, payouts or approved coverage/financial calculations are included. Independent label/policy review, realistic synthetic variation, a separate held-out split and policy/routing approvals remain future decisions.

The approved dataset-only scope replaces the roadmap's prior M4 ingestion slot: ingestion moves to M5, later planned work to M6–12. This changes sequencing, not contracts or architecture. No Azure operation, spend, Git initialization, commit or push occurred. **Stop after Milestone 4; do not begin ingestion or policy-rule implementation.**
