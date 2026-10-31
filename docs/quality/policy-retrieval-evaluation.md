# Offline policy retrieval evaluation

Status: **IMPLEMENTED offline lexical evaluation**, with **authored, not independently adjudicated** labels. M7's retriever is unchanged. No embeddings, semantic/hybrid RAG, answer generation, LLM judge, provider benchmarking or live service evaluation is implemented. This is a development diagnostic, not the approved retrieval release gate.

## Dataset and separation from the engine

The [versioned 30-query dataset](../../data/evaluation/policy-retrieval/README.md) pins M4 sources and specifies query/cohort/fault inputs, exact relevant chunks, grades, citation constraints and expected abstention reasons. Its labels were selected from source wording and scenario facts without retrieval results. Complete expected chunk metadata is stored statically; [load_gold/source_chunk](../../src/claims_ai/retrieval_eval/dataset.py) independently checks specified line text, document/hash/page/section, policy/version/date and deterministic IDs using the documented serialization, without calling M7 ingestion or retrieval. A malformed label, duplicate ID or stale manifest aborts evaluation before engine invocation rather than becoming a scored no-answer.

The [runner](../../src/claims_ai/retrieval_eval/runner.py) first validates exact M4 reproduction and the gold manifest, then prepares case-bound M7 indexes/requests. `EvaluationEngine.run` receives only the case, request, index and injected fault configuration, never expected clauses, grades, cohort, reason or rationale. It is a local harness seam, not a provider SDK. The default engine invokes unchanged M7 code. Scores are computed after receiving outputs. Expected technical faults are explicit SIMULATED store exceptions/missing snapshots; unexpected engine exceptions, malformed responses and a cooperative two-second deadline produce technical-failure observations, not successful abstentions.

Policies, facts and incident dates remain unapproved synthetic fixtures. Fault mutation is confined to new in-memory snapshots, including an authored instruction clause; inputs and prior reports are never overwritten. Output JSON contains untrusted query/quoted policy text and must not be used as operational logs or executable instructions.

## Ranking metrics

Only queries with a nonempty authored relevance set enter ranking averages. Each is measured at its declared cutoff `k` (v1 uses 3); aggregate separately by cutoff. Grades greater than zero are binary relevance for precision/recall/MRR and graded gains for nDCG.

| Metric | Exact definition |
| --- | --- |
| Precision@k | Number of unique, valid relevant hits in the first k ranks divided by **k**, including unfilled positions. A perfect single-clause return at k=3 scores 1/3, not 1. |
| Recall@k | Unique valid relevant hits in the first k ranks divided by the complete authored relevance-set size. Missing/failed answerable queries score zero. |
| MRR@k | Reciprocal of the first valid relevant rank within k, or zero; macro-average over answerable queries. |
| nDCG@k | DCG uses `(2^grade - 1) / log2(rank + 1)`; divide by ideal DCG from descending authored grades truncated at k. Missing results have zero gain. |
| Empty relevance set | All four ranking metrics are **null/not applicable**; excluded from ranking means. Evaluate expected no-answer/safety/invalid/failure behavior instead. |

Invalid hits retain their original rank and earn zero relevance credit. Citation/source checks, case/policy scope, requested version/date and response request/index binding must pass before a hit earns credit. A repeated chunk receives credit only at its first occurrence; duplicates and result-limit violations are separately flagged. Invalid items are never removed to improve later ranks. Full responses remain available for inspection, even if only the first k ranks score.

## Safety, citations and abstentions

[Scoring](../../src/claims_ai/retrieval_eval/scoring.py) compares every returned chunk with the independent source oracle. Citation validity checks complete source-bound text/metadata/ID, not just citation syntax. It is distinct from relevance: a valid quote can be irrelevant. Policy-version/date correctness checks the exact requested version and its incident interval; cross-policy/claim counts compare against both request scope and the authoritative case. Response schema validity and request/index binding are separate checks; malformed bodies and backend exception text are omitted.

| Report field | Denominator / interpretation |
| --- | --- |
| Ranking means | Answerable queries only, grouped by k; every failed answerable query contributes zero rather than disappearing. |
| Citation and version/date rates | All hits in schema-valid responses, including irrelevant/duplicate hits; report numerator and denominator. No hits gives a null rate, not 100%. |
| Unsafe cross-policy / cross-claim | Count and rate among those returned hits. Zero observed in a small offline set does not prove authenticated tenant isolation. |
| Abstention correctness | Queries authored to abstain: requires schema-valid, correctly bound, hit-free output with the exact expected reason. Always inspect the separate five cohort summaries. |
| No-answer false-positive retrieval | No-answer queries with returned hits divided by schema-valid no-answer responses. Malformed outputs are unscorable here, explicitly counted as schema/technical failures and incorrect abstentions. An outage with no hits is still not a correct no-answer. |
| Expected behavior | Requires no recorded expectation/quality/scope failure: relevant labels present at k with no irrelevant hits, or an exact correct abstention. This is conformance to authored examples, not insurance accuracy or an approved release threshold. |

`no_lexical_match`/`requested_clause_absent` are observed no-answer types; query-budget errors are invalid queries; policy/version/source/scope failures are safety blocks. Outages and the explicitly injected missing-index condition are technical failures. M7 uses `missing_policy` for both unknown versions and missing stores; the pinned fault context disambiguates the latter. An unexpected adapter exception or malformed response is always a technical failure. The report keeps cohort identity, observed classification, exact reasons and failure codes for audit.

Overall counts/rates are diagnostics with their denominators. **No single ranking score averages incompatible cohorts.** Reports also include per-cohort and per-scenario summaries and all failure examples by query ID/code; narrow scenarios often have one query and are not statistically reliable slices. Technical-failure handling success does not imply retrieval success or live availability.

## Reproduction and evidence

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.retrieval_eval --corpus data/synthetic/motor/v1 --gold data/evaluation/policy-retrieval/v1/queries.json --output outputs/retrieval-eval/lexical-v1.json
make retrieval-eval-check
```

Run from the repository root, or provide absolute input paths when using an installed wheel. The source distribution includes gold/corpus files; the wheel contains code and uses explicitly supplied external datasets. Outputs use exclusive creation, refuse corpus/gold directories, omit timestamps and pin gold/manifest/corpus/evaluator/retriever hashes plus Python/Pydantic versions. Reproduction means byte-identical local evaluation, not model determinism. [M8 evidence](../milestones/milestone-8.md) records the actual results and failures.

Independent domain/relevance adjudication, held-out queries, additional policy wording/endorsements, graded-label review and approved gates remain outstanding. The corpus is small, public, templated and unapproved. A miss on a paraphrase is a lexical limitation; returning command text as data is a relevance/abstention finding, not proof of tool execution. This harness cannot establish grounded answer quality, semantic/hybrid RAG quality, coverage correctness, production security or service performance.
