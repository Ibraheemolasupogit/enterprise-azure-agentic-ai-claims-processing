# Policy knowledge ingestion and lexical retrieval

Status: **IMPLEMENTED and locally TESTED for unapproved synthetic fixtures**. Deterministic parsing/lexical lookup runs real local code; it is not a simulated Azure search engine. Knowledge remains `unapproved_fixture_only`. No embeddings, semantic search, hybrid RAG, live Azure adapter, policy activation or coverage/financial decision is implemented.

## Inputs and ingestion

[IngestionRequest](../../src/claims_ai/knowledge/contracts.py) composes an authoritative caller-supplied `Case`, existing `Policy` metadata and `PolicyDocument` inputs (document metadata, bytes and M4 source sidecar). The [parser](../../src/claims_ai/knowledge/ingestion.py) supports only the current one-page generated PDF grammar. It verifies actual input bytes against the rendered source, SHA-256/size, exact case document association, page/media type and claim/document headers. Schedule identity/version/effective dates/vehicle and wording version/product/jurisdiction must exactly match the supplied metadata.

Parsing deliberately consumes authored source sidecars, not OCR or a general PDF parser. Quarantined M4 artifacts can be inspected in this explicit offline authoring path; their scan status never changes and the resulting index cannot claim operational approval. Existing `Policy.index_version=fixture-not-indexed` and `rule_pack_version=unapproved-no-rules` are retained and required. Endorsements, other formats and multi-page documents fail closed pending a verified source-index/parser design.

Each wording line `C01 - …`, `X01 - …`, `R01 - …` or `V01 - …` becomes one complete clause chunk, never a split clause. `section` is the literal source ID prefix, not an invented heading. Categories are clause, hypothetical exclusion candidate, review and revision. The disclaimer/footer and metadata lines are verified but not indexed as clauses. Unknown syntax, empty wording and repeated clause IDs (including conflicting definitions) invalidate ingestion. Semantic contradictions across different clause IDs are **not detected** by this parser.

Each frozen `PolicyChunk` wraps existing `PolicyClause`/`PolicyCitation` and records case identity, effective-from and exclusive effective-to/expiry, section/category, one-based source line range, page, document/hash and parser version. Its full SHA-256 ID covers that metadata and text. `KnowledgeIndex` retains source records and policy bundles, canonicalizes input order and fingerprints the complete snapshot. Limits are 16 registered versions, 64 supplied documents, two source artifacts per bundle and 32 chunks per bundle; M4 source bounds also apply. This is a small in-memory index, not a scalable search service.

## Retrieval and filtering

[retrieve](../../src/claims_ai/knowledge/retrieval.py) requires both an authoritative `Case` and typed `RetrievalRequest`: claim ID, policy ID, exact requested version (or explicit missing value), incident date, pinned index hash, query, optional clause IDs and limit (1–10). Checks precede scoring:

1. Bind request/index claim and policy identity to the case; bind incident date to `case.claim.loss_at.date()`. This uses the supplied timestamp's calendar date, matching M4, not wall-clock expiry or an assumed UTC conversion. The eventual business timezone requires approval.
2. Verify the pinned snapshot hash, then rebuild every registered bundle/chunk from source records against current case metadata. Changed text, source, line/page, dates, category, citation or chunk IDs cannot be authenticated merely by recomputing the outer hash.
3. Require a complete, verified register with unique versions and nonoverlapping intervals. Any ingestion issue blocks the entire snapshot, including queries for an otherwise valid entry. Missing/ambiguous metadata never causes a guessed policy selection.
4. Select exactly the requested version and require `effective_from <= incident_date < effective_to`. A missing, expired, not-yet-effective or wrong version produces no hits; no nearest-version fallback exists. Requested clause IDs must all exist in that version or the entire request abstains.
5. Apply lexical scoring **only within that bundle and optional clause subset**. NFKC/casefold text, extract distinct ASCII alphanumeric tokens and count overlapping query/body tokens. Sort by descending count, then clause ID and full chunk ID. Repeated terms do not boost score. Queries with no tokens or over 64 distinct tokens abstain. No stemming, synonyms, embeddings, probabilistic confidence or semantic relevance is inferred.

`RetrievedClause` preserves the complete chunk/citation, matched terms and integer overlap count. `RetrievalResponse` pins the request/index and contains either hits or a stable abstention reason, never both. Exclusion-category hits are quoted draft text, not applied exclusions or denials. Zero lexical matches does not prove the absence of an applicable insurance term.

`retrieve_from` defines the optional snapshot-store boundary: scope is checked before loading, a cooperative async deadline defaults to one second (configurable within 0–30 seconds, exclusive at zero), and missing indexes/errors/timeouts abstain without backend exception text or fallback. A cancellation-resistant/blocking backend requires isolation before integration; no retry, network client or durable store is provided. [AzureAISearchAdapter](../../src/claims_ai/knowledge/contracts.py) is a typed protocol only. The older operational `ports.PolicyRetriever` remains unchanged and is not claimed to have an approved-policy implementation.

## Authority and untrusted content

The caller must authenticate case access and supply a trusted policy register, case/date and expected snapshot. Local consistency checks and hashes are not signatures, malware clearance, access grants or proof that a document is truthful/approved. Do not accept a rewritten case/register and rehashed index from an untrusted caller as authority. Cross-case/policy metadata is checked, but Entra/tenant authorization remains planned.

Policy prose, query strings and returned chunks are untrusted data. Embedded instructions can be retained as quoted text; nothing in this module executes commands, agents, tools, URLs or policy rules. The parser is not an injection classifier. Future consumers must escape display content, avoid raw operational logging and enforce their own instruction/data separation. Retrieved draft clauses cannot enter approved assessments or silently replace `Case.policy`.

The caller must resolve conflicting incident facts before any operational policy resolution. This foundation checks the supplied intake date and register; it does not reconcile M6 evidence, detect arbitrary semantic conflicts, assign supervisors, mutate lifecycle state or override human approval. Abstentions require later case-workflow handling.

## Offline reproduction

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.knowledge --corpus data/synthetic/motor/v1 --output outputs/knowledge/draft-lexical.json
```

Use a new output filename; overwrites and corpus output paths are refused. The CLI validates exact M4 reproduction, reads draft bundles and submitted-version text, and runs three fixed demonstration queries per submission. It never uses expected clause relevance or expected policy-selection labels to choose a successful version. Reports include indexes, quoted clauses/citations, exclusion candidates, explicit abstentions, source/code/manifest hashes and runtime versions. The mode is `OFFLINE_SYNTHETIC`, with untrusted-content and no-policy-activation markers; outage test doubles are separately simulated failures.

The [M7 record](../milestones/milestone-7.md) records actual test/reproduction counts. [Traceability](../business/traceability-matrix.md#milestone-7-policy-knowledge-evidence) retains all hybrid retrieval, policy approval, authorization and held-out evaluation gaps. No retrieval-accuracy, semantic-search or production-readiness result is claimed.
