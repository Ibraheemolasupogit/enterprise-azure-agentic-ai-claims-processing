# Deterministic provisional motor rules

Status: **IMPLEMENTED and locally TESTED, offline only**. Inputs/scan/reviewer assertions in the CLI are **SIMULATED**. Specification and policy wording remain **PROVISIONAL / UNAPPROVED**. No approved coverage engine, autonomous outcome, settlement, lifecycle transition, authenticated reviewer, queue or persistence adapter is implemented.

## Contracts and authority

M9 composes existing `Case`, `Evidence`, M6 `ProcessingRequest` and M5 `ExtractionResponse`, M7 policy/chunk/index types, `PolicyCitation`, `ReviewerRole` and `RiskFlag`. Existing [domain contracts](../../src/claims_ai/models.py) and [human lifecycle guards](../../src/claims_ai/lifecycle.py) are unchanged. Their `RuleResult.outcome` cannot represent four-state non-binding findings; the separate [rules contracts](../../src/claims_ai/rules/contracts.py) deliberately avoid constructing an operational `Assessment`.

`RuleEvaluation` identifies the claim, case policy, requested policy/version, specification and complete input/case hashes. Each finding includes rule ID/version, a specification SHA/JSON pointer, exact supporting clause citations when bound, evidence/fact IDs, issues, fixed code explanations and optional calculation details. Accepted evidence provenance retains full M6 record fingerprints, artifact hashes, pages/source lines and replay keys. Failed bindings have no fabricated policy citation; their specification reference and input hashes still explain the failure.

| Finding | Meaning |
| --- | --- |
| PASS | This explicit provisional predicate or calculation succeeded. It does not mean coverage approval. |
| FAIL | A known predicate failed, such as date/category/exclusion or handler-only review routing. It is not a denial. |
| INDETERMINATE | A prerequisite, verified fact or binding is missing, unsafe, ambiguous or conflicting. No optimistic default. |
| NOT_APPLICABLE | A trusted out-of-scope category or known exclusion prevents the dependent illustration; no amount is returned. |

The result fixes `final_outcome=null`, `settlement_authorized=false` and `human_review_required=true`. Its validator rejects reviewer downgrades for adverse/indeterminate/risk-flagged findings and arithmetic without passing prerequisites. No method converts it into a final claim outcome or payment. Future case publication must still pass existing authenticated human/supervisor and durable-commit requirements; those integrations remain planned.

## Ordered checks

1. **PR01 — binding.** Require the assessing-stage case, pinned provisional specification, matching policy identity, explicit version, verified M7 index/sources and nonconflicting register. Rebuild all policy entries against case metadata; require accepted policy-document scan assertions. The selected policy interval must exactly match the version's specification interval and contain the incident calendar date. No nearest-version fallback. Every specified clause must match the new provisional wording, including the actual excess/cap values; a new pack hash cannot reuse old financial wording. Existing `Case.policy`, if present, must match. Nothing activates or replaces it.
2. **PR02 — evidence.** Replay every supplied extraction request/response through unchanged M6 validation against actual bytes and source records. Original claim/doc metadata must match the current case; replayed evidence must exactly equal admitted case evidence. Require every case document to be processed/accepted, the explicit three-kind checklist, complete M6 fields and consistent shared values. Claimed/estimated amounts must match under this provisional specification. Reject duplicate document inputs, orphan/forged records, missing provenance and partial promotion after a document hold. The current foundation accepts only explicitly opted-in SIMULATED fixture-origin evidence; other origins fail closed.
3. **PR03 — category.** Source-linked `ReviewedFacts` bind category/cause, a synthetic reviewer identity/role, fact ID and supporting verified narrative IDs to the complete current case hash. Unknown, missing, stale or contradictory assertions remain indeterminate. A reference establishes provenance, not semantic truth: the code never infers cause/category from narrative or image content.
4. **PR04 — exclusion.** Reviewed `gradual_wear_only` triggers a non-binding FAIL; reviewed impact passes; unknown cause stays indeterminate. Out-of-scope category makes this dependent rule not applicable. No additional exclusion is invented.
5. **PR05 — illustration.** Execute only after PR01–PR04 pass and no ambiguous/conflicting/injection/unsupported risk flag exists. Use exact integer-pence arithmetic from the [explicit specification](../../data/rules/motor/README.md): subtract the fixed version excess once, floor at zero, then cap the net amount. Return estimate, excess, post-excess amount, cap, illustrative amount and cap reduction. Zero amounts remain human-reviewed findings; there is no automatic approval/rejection or settlement.
6. **PR06 — oversight.** Preserve supplied risks and any existing assessment risks. At or above the specification's reported-amount threshold, add `high_risk`. Any FAIL/INDETERMINATE or risk flag requires a supervisor; all other findings still require a human reviewer. High-risk cases may have a valid non-binding illustration but cannot bypass supervisor review. Unresolved/unsafe evidence never receives an amount.

Dates use the supplied loss timestamp's calendar date, matching M7 conventions, with start-inclusive/end-exclusive intervals. No wall-clock expiry or implicit UTC date conversion is used. Business timezone, policy ownership/approval and eventual reviewer identity/assignment require separate decisions/integrations.

## Safety and reproducibility

[engine.evaluate](../../src/claims_ai/rules/engine.py) is pure: it returns frozen findings without changing the case, documents, evidence or outcomes. Identical requests yield identical execution keys/results; evidence-input ordering is canonicalized. Duplicate inputs within one request are held rather than silently merged. There is no durable exactly-once, signed audit or concurrent-write guarantee.

The [loader](../../src/claims_ai/rules/specification.py) pins canonical specification bytes and scenarios through a manifest. Known rule IDs, exact clause mappings, supported formula, integer parameters and unique nonoverlapping version intervals are validated before execution. No `eval`, prompt interpreter or arbitrary expression dispatch is used. An invalid typed request/configuration raises validation failure without an illustration; well-formed but incomplete/unsafe data returns explicit findings. Confidence does not become a calibrated coverage probability.

Caller-supplied case, scan and human assertions are not authenticated here. The CLI authors new synthetic snapshots with explicit test assertions, not evidence of real scanning/review or persisted lifecycle progression. New draft policy artifacts are generated in memory with reproducible hashes, separate from original M4 wording/labels. Source text and assertions remain untrusted to future consumers; supplied injection flags block arithmetic, but no new detector or semantic adjudicator is claimed.

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.rules --output outputs/rules/provisional-v1.json
make rules-check
```

Reports use exclusive creation, reject input-data output paths, label offline/provisional and simulated input status, record zero outcomes/settlements, and pin specification/scenario/manifest, rules/foundation source and runtime versions. The source archive includes input JSON; installed wheels use explicit external input paths. [M9 evidence](../milestones/milestone-9.md) records actual checks; [traceability](../business/traceability-matrix.md#milestone-9-provisional-rule-evidence) preserves all operational gaps.

This milestone implements the user's explicitly authorized fictional, non-binding rules foundation. The architecture's owner-approved operational rule/financial-release gate remains in force. M7/M8 semantics and the four documented lexical failures are unchanged; rule references are bound directly by exact clause identity, not selected by lexical search.
