# Authored lexical retrieval gold — v1

Status: **30 authored development queries, not independently adjudicated ground truth or a held-out set**. Relevant clauses/grades and no-result expectations were selected by reading fictional source wording and scenario metadata. No retrieval, ingestion, token scorer or M7 demonstration result generated those relevance selections. Independent adjudication remains outstanding; policy wording itself is unapproved.

[queries.json](v1/queries.json) freezes complete expected chunk IDs/text/citation/date metadata and graded relevance (1–3), exact request scopes, expected abstention reasons and source-reading rationales. [manifest.json](v1/manifest.json) pins query bytes and the unchanged M4 corpus manifest. Query SHA-256: `91b04bb8b8fd73b0e4ac32a5875e7c7bc4dc78224df1fd5bed4c53a25a9572b0`. The independent label checker reconstructs the documented M7 chunk serialization from each specified source line; it does not choose relevance or call M7 ingestion/retrieval. The static file is the label source; the runtime has no gold-generation command.

| Cohort | Queries | Authored expectation |
| --- | --- | --- |
| Answerable | 11 | C01 scope/paraphrase, C02 evidence, X01 hypothetical exclusion, R01 review, V01 revision; includes multi-clause, boundary and adversarial-query cases |
| No answer | 5 | Irrelevant terms, unsupported warranty, absent clause, malicious query and malicious policy text |
| Policy safety block | 10 | Wrong/expired/future/missing/unknown/conflicting versions, tampered source/snapshot and cross-policy/claim requests |
| Invalid query | 2 | Punctuation-only and 65 distinct tokens |
| Technical failure | 2 | SIMULATED store outage and missing snapshot; never legitimate no-answer successes |

All examples have `k=3`. The expired-policy example overrides only the evaluation case's loss timestamp to the exclusive expiry boundary. Other fault inputs duplicate a registered version, alter an index source record, mismatch the snapshot or reauthor a policy source with the fixed untrusted `C03` instruction line **in memory only**. M4 artifacts and labels never change. An instruction can be returned as inert source text; labeling the command-seeking query no-answer expresses a desired relevance/abstention boundary, not evidence that M7 executes text or has an injection detector.

The authoring step materialized chunk IDs from explicitly selected clause IDs/lines using the documented canonical serialization. This shares a serialization contract with M7 and is not independent implementation certification. Manifests detect changed bytes, not malicious authorship or approval. Version label edits, record the rationale/reviewer and repin the manifest; do not relabel after seeing a result merely to improve a score.

Run from the repository root using a fresh output filename:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.retrieval_eval --output outputs/retrieval-eval/lexical-v1.json
```

See [metric definitions and denominators](../../../docs/quality/policy-retrieval-evaluation.md) and [M8 evidence](../../../docs/milestones/milestone-8.md). No semantic/hybrid search, model judging, live provider comparison, coverage ground truth or cloud spending is involved.
