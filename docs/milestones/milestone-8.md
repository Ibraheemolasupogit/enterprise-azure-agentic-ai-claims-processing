# Milestone 8 — Policy retrieval and RAG evaluation foundation

Status: **COMPLETE within offline lexical evaluation scope**. Labels are **authored, not independently adjudicated**; no semantic/hybrid RAG is evaluated. M9 has not started.

## Files and behavior

- New `claims_ai.retrieval_eval` [contracts](../../src/claims_ai/retrieval_eval/contracts.py), [dataset/source oracle](../../src/claims_ai/retrieval_eval/dataset.py), [scoring](../../src/claims_ai/retrieval_eval/scoring.py), [runner](../../src/claims_ai/retrieval_eval/runner.py), [CLI](../../src/claims_ai/retrieval_eval/__main__.py) and initializer.
- New [versioned query/manifest files and provenance guide](../../data/evaluation/policy-retrieval/README.md), [tests](../../tests/test_retrieval_eval.py), [metric methodology](../quality/policy-retrieval-evaluation.md) and this record.
- Updated README, Makefile, source-distribution manifest, quality baseline, architecture status, traceability and roadmap. Domain contracts, M4 truth/tools, M5 benchmark, M6 evidence, M7 retrieval semantics and prior tests remain unchanged; no dependencies are added.

The 30 authored queries cover 11 answerable, five no-answer, 10 policy-safety, two invalid-query and two simulated technical-failure cases. Explicit clause/grade selections were read from sources, never generated from retrieval outputs. Full expected chunk IDs and citation constraints are static and independently source-checked before any engine call. Engine inputs exclude labels. Metrics retain invalid ranks, withhold credit from bad citations/scope/version/binding and separate empty-relevance cohorts. See the [methodology](../quality/policy-retrieval-evaluation.md) for exact denominators, date semantics and fault handling.

## Measured offline results

The verified `OFFLINE_LEXICAL` report contains **30 queries and 14 returned hits**. Macro ranking at **k=3 over 11 answerable queries**: precision **0.333333**, recall **0.909091**, MRR **0.909091**, nDCG **0.909091**. Precision uses the fixed cutoff denominator even for short lists; most queries have one relevant clause, so a correct single-hit result scores 1/3. Empty relevance sets never enter ranking averages.

| Authored cohort | Expectations met | Interpretation |
| --- | --- | --- |
| Answerable | 9/11 | One missing relevant clause and one irrelevant extra result |
| No answer | 3/5 | Two false-positive retrievals; not hidden as technical successes |
| Policy safety | 10/10 | Explicit wrong/missing/expired/conflicting/source/scope blocks |
| Invalid query | 2/2 | Correct query-budget/punctuation abstentions |
| Simulated technical failure | 2/2 | Correct unavailable/missing-index outcomes, not no-answer quality |

All **14/14 citations** and **14/14 version/date bindings** passed; observed cross-policy and cross-claim hits were **0/14** each. Exact abstention correctness was **17/19** across the four abstaining cohorts; no-answer false-positive retrieval was **2/5**. Overall authored-expectation conformance was **26/30**, not a ranking score or general accuracy claim. All denominators, cohort/scenario summaries and query-level failures are retained.

Four measured failures remain unchanged:

- **Q-007:** `automobile collision` misses relevant C01; lexical matching has no synonym capability.
- **Q-012:** unsupported `repair warranty` returns C02 evidence wording through token overlap.
- **Q-015:** a command-seeking query returns the injected C03 as inert policy text, against the authored no-answer expectation. This is not evidence of command execution.
- **Q-029:** the adversarial query returns relevant X01 plus irrelevant C02 through a shared token.

Neither labels nor M7 semantics were changed to remove these failures. These are diagnostics on unapproved development fixtures, not an independently adjudicated retrieval-accuracy or production-readiness result.

## Verification

Reused Python 3.12.8, Pydantic 2.11.7, pytest 8.4.1, Ruff 0.16.4, mypy 1.16.1 and installed setuptools. No third-party dependency was installed/upgraded.

- `make check`: **325 tests passed** (296 prior + 29 new evaluation checks); Ruff format/lint and strict mypy passed across 45 Python files. Checks cover graded metric arithmetic, empty/short/duplicate/truncated rankings, gold/engine separation, bad citations/versions/scope/binding, ambiguous registers, abstention taxonomy, malformed gold/responses, sanitized errors and CLI safety.
- Two source CLI reports (`outputs/retrieval-eval/m8-verified-a.json` and `m8-verified-b.json`) matched byte-for-byte: SHA-256 `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`. Gold SHA-256 is `91b04bb8b8fd73b0e4ac32a5875e7c7bc4dc78224df1fd5bed4c53a25a9572b0`; the manifest pins M4 hash `0fa7439208fb8d08279fd38e938fc36ea8c8fdb5a5a9ba6a369b15b41a2a7617`.
- All 30 golden cases and 12 declared relevance observations passed source/metadata checks. A separate report audit verified all 14 returned source quotes, page/line/byte hashes, full chunk IDs and claim/policy bindings, including irrelevant results.
- `make dataset-check` passed all 12 M4 scenarios; all **153 corpus files** matched tracked Git blob hashes. Protected domain/ports, M4–M7 modules, prior tests and dependency declarations have no changes. Rerun M5/M6/M7 artifacts match prior outputs byte-for-byte; prior files were retained and new output filenames used.
- `make package` and isolated installed-wheel reproduction validate code packaging; the source archive includes the gold queries/manifest/guide, new tests/docs and original corpus. Existing third-party packages are reused with project-wheel installation restricted to a temporary target (`--no-index --no-deps`).
- Validated **25 Markdown files, 348 local links/anchors and 90 named test references**, table/fence/whitespace consistency and `git diff --check`. No live service/model test, operational fault test or coverage approval is inferred.

## Limitations and acceptance

Independent domain/relevance review and held-out evaluation remain outstanding. Chunk-ID reconstruction shares a documented serialization contract with M7; it is separate from relevance selection and retrieval, not independent implementation certification. The authored no-answer expectation for command-seeking text is a desired relevance boundary; quoting the injected instruction does not mean M7 executed it. Multi-clause semantic contradictions, generated-answer grounding, multilingual/large-corpus behavior, authentication and real service outages are not evaluated.

Acceptance concerns the reproducible measurement foundation and honest reporting of failures; it does not require pretending the retriever satisfies future release gates. All policy wording/coverage authority remains unapproved and human oversight unchanged. The user-authorized M8 scope supersedes the prior ingestion-service slot; remaining ingestion work moves to M9 and subsequent planned work shifts in the current roadmap. No Azure calls/spending, agents, coverage decisions, deployments, commits or pushes occurred. **Stop after Milestone 8.**
