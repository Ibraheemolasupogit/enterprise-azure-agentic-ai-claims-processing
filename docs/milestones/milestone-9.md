# Milestone 9 — Deterministic motor claims rules foundation

Status: **COMPLETE within offline provisional scope**, with verification recorded below. All policy parameters/wording are **fictional and unapproved**; scan/extraction/reviewer assertions in the demonstration are **SIMULATED**. M10 has not started.

## Deliverables and decisions

- New `claims_ai.rules` [contracts](../../src/claims_ai/rules/contracts.py), [specification loader](../../src/claims_ai/rules/specification.py), [engine](../../src/claims_ai/rules/engine.py), [fixture builder](../../src/claims_ai/rules/fixtures.py), [CLI](../../src/claims_ai/rules/__main__.py) and initializer.
- New [versioned specification/scenarios/manifest and guide](../../data/rules/motor/README.md), [focused tests](../../tests/test_rules.py), [architecture guide](../architecture/deterministic-provisional-rules.md) and this record. Updated README, architecture status, requirements annotation, traceability, roadmap, Makefile and source-distribution manifest.
- Existing domain/lifecycle/ports and M4–M8 code, labels, semantics and prior tests remain unchanged. No dependency is added. Four-state findings use a new contract because existing operational `RuleResult.outcome` cannot express their semantics without changing decision authority.

The provisional 0.1.0 specification defines six known rules and two separate fixture-policy versions. PR01 binds policy/version/incident date/specification/source clauses before dependent execution. PR02 replays actual extraction inputs through M6 and requires exact admitted evidence, complete processed documents and matching money observations. PR03/04 use only explicit source-linked synthetic human classifications for motor category and gradual-wear exclusion. PR05 illustrates the versioned excess/net-cap formula using integer GBP pence. PR06 preserves risks and requires human/supervisor oversight. All results fix final outcome to null and settlement authority to false; no `Assessment`, closure or payment is produced.

See the [architecture](../architecture/deterministic-provisional-rules.md) for trust assumptions, provenance, date conventions and limitations. This user-authorized provisional exercise does not approve any M4 wording, insurer policy, rule pack or operational release.

## Findings and boundaries

The 23 authored scenarios produced **138 findings: 76 PASS, 20 FAIL, 39 INDETERMINATE and three NOT_APPLICABLE**. Ten cases contain non-binding illustrations; seven require a reviewer and sixteen require a supervisor. Every case requires human review. There are **zero final outcomes and zero settlement authorizations**. These are fixture execution counts, not coverage accuracy or business-performance measurements.

| Boundary/example | Actual provisional finding |
| --- | --- |
| GBP 1,000.00, provisional-v1 / v2 | Illustrations GBP 750.00 / GBP 700.00 with explicit GBP 250.00 / GBP 300.00 excess |
| GBP 249.99 / 250.00 / 250.01, v1 | Illustrations GBP 0.00 / 0.00 / 0.01; human review still mandatory |
| GBP 10,250.00 / 10,250.01, v1 | Net illustrations capped at GBP 10,000.00; the latter records GBP 0.01 cap reduction; supervisor required |
| GBP 7,499.99 / 7,500.00, v1 | Below threshold requires a reviewer; exact high-value threshold adds high-risk and requires a supervisor |
| 2026-07-01 incident | v1 fails its exclusive expiry boundary; exact v2 start passes binding |
| Expired, missing/conflicting/quarantined/tampered or unapproved-simulation evidence | No arithmetic; explicit blocked/indeterminate findings and supervisor review |
| Reviewed gradual-wear exclusion / unsupported category | Non-binding FAIL and dependent NOT_APPLICABLE; no denial or amount |

Unknown/missing/stale/conflicting assertions stay indeterminate. New fixture documents are authored in memory; no M4 case is imported or scan-cleared. Repeated evaluation returns identical keys/results without case mutation.

## Verification

Reused Python 3.12.8, Pydantic 2.11.7, pytest 8.4.1, Ruff 0.16.4, mypy 1.16.1 and installed setuptools. No third-party dependency was installed/upgraded.

- `make check`: **385 tests passed** (325 prior + 60 new rule checks); Ruff format/lint and strict mypy passed across 52 Python files. Tests cover dates/expiry, missing/wrong/conflicting versions, source replay/tampering, evidence/fact completeness/staleness/conflicts, exclusion/category behavior, exact/zero/excess/cap/high-value boundaries, malformed configurations, pure duplicate execution, decimal-context independence, provenance, unsafe outcome rejection, manifest integrity and CLI input protection.
- `make dataset-check` passed all 12 original scenarios. All **153 M4 corpus files** and both M8 query/manifest files matched tracked Git blob hashes. Existing domain/lifecycle/ports, M4–M8 code and prior tests, dependency declarations and all M4 labels remain unchanged.
- Two CLI reports (`outputs/rules/m9-verified-a.json` and `m9-verified-b.json`) matched byte-for-byte: SHA-256 `2460f9e54a485a2e3d9670b9b8e36cfc3a676fd62eb744e29c21c561e07822cb`. The specification SHA-256 is `47398a0a1161ddfd01739830a5c5590de3595d57a2b106836aefe6f763524ac9`; scenario SHA-256 is `b047e92386ef6eb8066388fe8f7d1db099b83d090915cde9a076862ac7441cef`. Reports also pin reused foundation/rules code and runtime versions.
- A separate artifact audit replayed source evidence and checked **683 record-provenance observations and 140 clause citations**, case/spec hashes, exact version bindings, calculation dependencies and integer-pence arithmetic. These are reproducible consistency checks, not independent domain adjudication or signed provenance.
- New rerun files matched prior M5/M6/M7/M8 artifacts byte-for-byte. M8 report SHA-256 remains `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`; all four failures remain unchanged. Prior output files were retained.
- `make package` built wheel/sdist without fetching dependencies. The wheel includes six current rule modules; the source archive includes specification/scenarios/manifest/guide, tests/docs and all 153 original corpus files. Installing only the project wheel into a temporary target (`--no-index --no-deps`) and running its CLI matched the source report byte-for-byte.
- Validated **28 Markdown files, 399 local links/anchors and 108 named test references**, plus table/fence/whitespace consistency and `git diff --check`. No live cloud, scanning, reviewer-authentication or durable-workflow result is inferred.

## Limitations and acceptance

Policy terms and human classifications need independent owner/domain review before any operational use. Source/identity hashes are not signatures or authentication. Supported evidence is the explicitly opted-in fixture path; general documents, live providers, endorsements, calibrated thresholds, case queues, approved assessments, signed audit and concurrent/durable idempotency remain planned. Reviewed cause/category are trusted synthetic assertions whose semantic truth the code does not establish.

The M8 failures remain visible and unresolved: Q-007 paraphrase miss, Q-012 warranty false positive, Q-015 inert instruction-text false positive and Q-029 irrelevant extra clause. No lexical retrieval or evaluation behavior is changed to obtain rule results.

Acceptance covers deterministic, provenance-bound, non-binding rule findings with explicit fictional parameters and safe human review requirements. It does not approve an insurer policy or authorize a financial outcome. The user-authorized M9 scope supersedes the previous intake-service slot; remaining intake work moves to planned M10 and subsequent work shifts in the current roadmap. No Azure operations/spending, agents, MCP/APIM, UI, deployment, commits or pushes occurred. **Stop after Milestone 9.**
