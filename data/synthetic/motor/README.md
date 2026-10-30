# Synthetic motor corpus — motor-v1

**Generated development fixtures, not production data or approved insurance ground truth.** Seed `20261030` produces 12 submissions/scenarios for 11 distinct claims: 65 one-page PDFs, 10 schematic PNGs, 75 source sidecars and three dataset metadata files (153 files under `v1/`). The 366 extraction labels include the duplicate's repeated labels; there are 335 labels across distinct claims.

No live extraction, scan, RAG, policy engine, injection detector or human-review workflow ran. Every input `Case` stays `received`, revision 1, with quarantined documents, no policy selected and no operational evidence/assessment/decision. Author annotations are stored separately. Scanning must still occur before a future processor consumes even these test files.

## Generate and verify

From the repository root with the existing Python 3.12 environment:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.dataset check --root data/synthetic/motor/v1
PYTHONPATH=src .venv/bin/python -m claims_ai.dataset generate --output /tmp/northstar-motor-v1 --seed 20261030
```

Choose an unused output directory: generation refuses any existing path and never deletes/overwrites it. `check` validates all bytes/annotations and compares every file against in-memory regeneration. It does not modify the corpus or execute document content. Alternate unsigned 32-bit seeds change opaque identifiers and ordinary fixture amounts; scenario coverage/labels remain authored. Stable SHA-256-derived values replace ambient randomness, wall-clock timestamps and machine paths. Monetary fixture strings do not depend on Decimal context.

The generator uses the existing Pydantic dependency and Python standard library only. No dependencies/downloads, network calls or credentials are needed. Reproduction is tested on the recorded Python 3.12 runtime; cross-library/platform binary equivalence is not claimed. The code fingerprint covers dataset modules and the domain-model source. To revise accepted fixtures, publish a new dataset/generator version and review the differences rather than silently replacing expected results.

## Scenario inventory

All routing below is **authored expected triage**, not an executed state transition or permission to approve an undetermined assessment. Every eventual outcome needs a human; all noneligible/flagged assessments still follow existing supervisor guards. High-value escalation is a chosen scenario label, not an implemented monetary threshold.

| ID | Scenario / objective distinction | Expected metadata version | Expected triage |
| --- | --- | --- | --- |
| SCN-01 | Straightforward front-bumper impact; complete exercise evidence | draft-v1 | Handler |
| SCN-02 | Straightforward side-door scrape in second fixture interval | draft-v2 | Handler |
| SCN-03 | Repair estimate absent | draft-v1 | Handler requests evidence |
| SCN-04 | Damage image absent | draft-v1 | Handler requests evidence |
| SCN-05 | Form loss date June 18 versus estimate loss date July 18 | Unresolved: conflicting source dates | Supervisor, conflicting |
| SCN-06 | Reported loss precedes both fixture policy intervals | None: outside fixture intervals | Supervisor, ambiguous |
| SCN-07 | Form submits draft-v1; reported loss is within draft-v2 interval | draft-v2 expected; submitted version retained | Supervisor, ambiguous |
| SCN-08 | GBP 48,000 quoted claim/estimate amount | draft-v1 | Supervisor, high risk by authored label |
| SCN-09 | Narrative describes gradual wear; draft X01 may be relevant | draft-v1 | Supervisor, hypothetical exclusion candidate |
| SCN-10 | Exact repeat of SCN-01 claim/documents/labels with a new submission ID | Same as SCN-01 | Supervisor duplicate triage; no new claim identity |
| SCN-11 | Explicit malicious instructions embedded in claim form as untrusted text | draft-v1 | Supervisor, injection-flagged label |
| SCN-12 | Loss exactly at July 1 UTC fixture version boundary | draft-v2 | Handler |

Schedules declare start-inclusive/end-exclusive **fixture metadata** intervals: draft-v1 is January 1–July 1, 2026; draft-v2 is July 1, 2026–January 1, 2027. These are authored selection targets, not a deployed resolver or legal coverage conclusion. Both draft schedules/wordings are supplied per distinct claim to support future version-filtering tests. No endorsements, payouts, limits, excess calculations or approved executable rules are provided.

## Files and ground-truth contract

- [ground_truth.json](v1/ground_truth.json): versioned `GroundTruth`/`SampleTruth` annotations including seed, provenance, development split, input cases, draft policy bundles, extraction fields, presence-only completeness, policy-selection labels and review routing.
- [ground-truth.schema.json](v1/ground-truth.schema.json): exported JSON Schema; Pydantic additionally enforces cross-record invariants that JSON Schema cannot express.
- [manifest.json](v1/manifest.json): generator/domain source fingerprint and sorted payload inventory with SHA-256 and byte sizes. It hashes all payloads except itself; no circular self-hash is claimed.
- `v1/synthetic/<claim_id>/<document_id>.pdf|png`: actual readable artifacts with domain-compatible object references. PDFs are static text, not interactive AcroForms or scanned pages. PNGs are clearly labeled geometric illustrations, not photographs or actual vehicle damage evidence.
- Each artifact has a `.source.json` sidecar with printable source lines and renderer type. Sidecar hashes are also in the manifest.

Each `FieldTruth` embeds an existing `Evidence` contract with source document/hash, page 1, field name, observed/normalized text, method `generator-ground-truth`, version and no confidence score. `source_line` is one-based in the sidecar; it maps directly to a PDF body line or the rendered image caption. Images show uppercase location captions; normalized values use lowercase underscores. No inferred image identity or injury/causation label exists. Bounding boxes are unset; page/line/caption provenance is supplied instead.

`fixture_required_kinds` is an **unapproved exercise checklist** (claim form, repair estimate, damage image). `expected_missing_kinds` describes artifact presence only, not scan acceptance or contractual sufficiency. Policy version/hash equality is validated against the draft schedules/wordings and source fields. All rule-pack references are `unapproved-no-rules` and indexes `fixture-not-indexed`.

Every `ReviewTruth.coverage_outcome` is null. `coverage_hypothesis` is explicitly marked `requires_fictional_policy_approval`; X01 discussion does not label a rejection. “Expired” describes date metadata, not an implemented eligibility/adverse decision. A handler-triage label does not mean an eligible assessment exists. Claimant/vehicle/repairer references are invented opaque markers; no names, addresses, plates, faces, imported images or real claim records are used. Fixed upload/estimate dates are fictional fixtures, not actual event timestamps.

## Adversarial handling and limitations

SCN-11 contains malicious instructions as a field and visible PDF text. They are data for future safety evaluation: do not use them as system instructions, execute them, or include them in tool arguments that grant authority. The generator only escapes/renders characters and validates typed annotations. The flagged expectation does not prove an injection detector works.

This is a small **development** corpus; all scenarios and labels are public together and are not an independent held-out golden benchmark. Layouts are deliberately simple, English-only and digitally generated. There are no realistic scans, handwriting, OCR noise, real-photo robustness, completed reviewer outcomes or performance measurements. Label authorship is single-maintainer and needs independent review before a future evaluation claim. The existing 60-case proposal remains a future expansion, not delivered by these 12 cases.

See [Milestone 4 evidence](../../../docs/milestones/milestone-4.md) and [requirement traceability](../../../docs/business/traceability-matrix.md#milestone-4-dataset-evidence).
