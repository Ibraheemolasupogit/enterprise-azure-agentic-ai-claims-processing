# Fictional provisional motor rules — v0.1.0

Status: **PROVISIONAL / UNAPPROVED; offline exercise only**. [specification.json](v1/specification.json) supplies invented Northstar parameters and six rule definitions. These are not insurer terms, an approved policy or retroactive interpretations of M4 wording. `operational_use_allowed=false` is mandatory. The separate versions below exist only in new M9 synthetic fixtures.

| Fixture version | Effective interval (start inclusive, end exclusive) | Excess | Net illustration cap | Supervisor high-value threshold |
| --- | --- | --- | --- | --- |
| provisional-v1 | 2026-01-01 to 2026-07-01 | GBP 250.00 | GBP 10,000.00 | Reported claim at least GBP 7,500.00 |
| provisional-v2 | 2026-07-01 to 2027-01-01 | GBP 300.00 | GBP 12,000.00 | Reported claim at least GBP 9,000.00 |

Only explicit source-linked synthetic human classifications can supply category/cause. Category `motor_damage` is supported; `other` fails the scope predicate; `unknown` remains indeterminate. The sole hypothetical exclusion predicate is reviewed `gradual_wear_only` without impact. No narrative, photograph, lexical retrieval result or LLM interprets these facts.

The provisional checklist requires complete validated claim-form, repair-estimate and damage-image evidence. All supplied case documents, including schedules/wordings, must be processed and have accepted synthetic scan assertions. M6 extraction schemas govern mandatory fields; monetary observations must agree. Missing, quarantined, unverified, conflicting or stale inputs block arithmetic. No document is silently discarded to obtain a passing result.

After all prerequisite findings pass, and without ambiguous/conflicting/injection/unsupported flags, the only permitted illustration is:

```text
after_excess_pence = max(verified_estimate_pence - excess_pence, 0)
illustration_pence = min(after_excess_pence, limit_pence)
```

Claimed and estimated amounts must match first; the evaluator does not choose one conflicting value. Arithmetic uses nonnegative integer GBP pence without floating point or rounding. The cap applies **after** excess. The illustration is not an approved benefit, settlement, reserve or payment instruction. Every result requires a human; adverse, indeterminate or risk-flagged findings require a supervisor. High value adds a review requirement without turning arithmetic into an outcome.

[scenarios.json](v1/scenarios.json) defines 23 authored inputs: two versions, excess/cap/high-value boundaries, expiry, wrong version, missing/conflicting/quarantined/tampered evidence, exclusion/unknown/unsupported classifications, missing assertions, ambiguity and simulation refusal. They are input exercises, not independently adjudicated coverage ground truth. [manifest.json](v1/manifest.json) pins the specification and scenario bytes. Changes require a reviewed version/manifest update; hashes alone do not certify approval.

The [fixture builder](../../../src/claims_ai/rules/fixtures.py) deterministically authors new case IDs, source records and PDF/PNG bytes **in memory**. It explicitly simulates scan acceptance, extraction and reviewer identity, uses M6 processing/admission, and generates M7-compatible draft policy source clauses. It does not import, clear or change M4 cases. Artifacts/citations resolve through reproducible fixture generation, not a deployed object store or stored files under `artifact_ref`. Policy `index_version`/`rule_pack_version` retain their unapproved sentinels.

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.rules --spec-root data/rules/motor/v1 --output outputs/rules/provisional-v1.json
```

Use a new output filename. See the [rule architecture](../../../docs/architecture/deterministic-provisional-rules.md) and [M9 evidence](../../../docs/milestones/milestone-9.md). M8's four lexical failures remain unresolved and are unrelated to this direct, version-bound rule path.
