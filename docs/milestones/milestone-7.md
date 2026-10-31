# Milestone 7 — Policy knowledge ingestion and retrieval foundation

Status: **COMPLETE — local deterministic draft-policy foundation**. Knowledge remains **unapproved synthetic fixture content**. Azure AI Search is an interface only; semantic/hybrid retrieval and coverage decisions remain planned. Milestone 8 has not started.

## Files delivered

- New `claims_ai.knowledge` [contracts](../../src/claims_ai/knowledge/contracts.py), [ingestion/parser](../../src/claims_ai/knowledge/ingestion.py), [lexical retrieval](../../src/claims_ai/knowledge/retrieval.py), [CLI](../../src/claims_ai/knowledge/__main__.py) and [initializer](../../src/claims_ai/knowledge/__init__.py).
- New [focused tests](../../tests/test_knowledge.py), [design/usage guide](../architecture/policy-knowledge-retrieval.md) and this milestone record.
- Updated README, Makefile, architecture status, requirements traceability and roadmap. Existing domain contracts, ports, M4 corpus/tools, M5 benchmark, M6 evidence implementation and their tests remain unchanged. No new dependency is required.

## Decisions and safeguards

Strict single-page fixture parsing verifies bytes/hash/ownership and source metadata before segmenting complete clause lines. Full deterministic chunk IDs retain policy/version/date/expiry, section, clause and page/line provenance. Snapshot hashes pin immutable local indexes; retrieval rebuilds chunks against source records, so an outer rehash alone cannot authenticate tampered citations or content.

Every query binds claim/policy/incident date to the caller's case and requires an exact version/snapshot. Missing, expired, future, overlapping, duplicate, unsupported or unverifiable metadata abstains; invalid register entries block the whole snapshot. Token overlap is computed only after filters, with deterministic ranking and explicit no-match/absent-clause/outage outcomes. Provider interfaces neither connect nor simulate Azure search. The [guide](../architecture/policy-knowledge-retrieval.md) defines limits, trust assumptions and all normalization/date semantics.

Policy text and queries remain untrusted data with no command/tool dispatch. Retrieved hypothetical exclusion wording does not decide coverage. No approved policy resolver, assessment, case-state mutation or policy activation is implemented. Case access/register/date assertions must come from a future authenticated service; hashes are not authorization or signed provenance.

## Verification

Reused Python 3.12.8, Pydantic 2.11.7, pytest 8.4.1, Ruff 0.16.4, mypy 1.16.1 and installed setuptools. No third-party dependency was installed/upgraded.

- `make check`: **296 tests passed** (251 prior + 45 new knowledge checks); Ruff formatting/lint and strict mypy passed across 38 Python files. Tests exercise exact versions, start/end/expiry boundaries, missing/overlapping/duplicate registrations, malformed/conflicting clause definitions, tampered metadata/chunks/source quotes even after outer rehash, scope leakage, lexical limits/ties, untrusted instructions, sanitized outages/deadlines, schema guards and CLI safety.
- `make dataset-check` passed all 12 scenarios. All **153 M4 corpus files** also matched their tracked Git blob hashes. Domain/ports, dataset, benchmark, evidence modules, prior tests and dependency declarations have no changes.
- Two source CLI executions (`outputs/knowledge/m7-verified-a.json` and `m7-verified-b.json`) matched byte-for-byte: SHA-256 `0169ba38660ce7cc3a389df20a5b8a78769ceae731cc8eea525d01cac2b7360d`. Reports contain **11 case indexes, 22 draft bundles, 110 chunks and 36 queries: 20 retrieved, 16 abstained** (10 no lexical match, six outside the requested version interval). All 110 chunk/source/hash/date bindings and all 20 returned citations passed independent integrity checks. These are demonstration counts, not retrieval-accuracy measurements.
- M5 benchmark reproduction matched its prior artifact byte-for-byte: `bdc5031bc5ec7a99619db618f87f9122a5649dbe71c4b46ba3bd9afedb8bb465`. M6 evidence reproduction matched its prior artifact: `92b00d6b8aa5e8655a510342168756749f7ae192c6d783d3f25bc872ecac372e`. Prior outputs were retained; verification used new output filenames.
- `make package` built wheel/sdist offline without dependency downloads. The wheel contains all five current knowledge modules; the source archive includes new tests/docs and all 153 corpus files. Installing only this project wheel into a temporary isolated target (`--no-index --no-deps`) and running its CLI reproduced the source report exactly.
- Validated **22 Markdown files, 307 local links/anchors and 79 named test references**, plus table/fence/whitespace consistency and `git diff --check`. None of these checks constitutes live-service, insurance-policy approval, semantic retrieval or production-readiness evidence.

## Limitations and acceptance

The parser handles authored M4 PDF/source pairs, not general PDFs/OCR or endorsements. Duplicate-ID definitions and interval/register conflicts are detected; semantic contradictions across different clause IDs and conflicting claim facts need later reconciliation. Date interpretation follows the supplied loss timestamp's calendar date, with start-inclusive/end-exclusive intervals; business timezone, authoritative register and policy approval require owner decisions.

Local snapshots are caller-held, unsigned and nondurable. Authentication, scanning, durable indexing/revocation/publication, approved source adapters, held-out relevance labels, hybrid search and operational timeout isolation remain planned. Term overlap is neither relevance probability nor retrieval accuracy. Existing human/supervisor decision guards are preserved.

Acceptance covers only the requested offline ingestion/retrieval foundation and its documented safeguards. The user-authorized M7 scope replaces the earlier ingestion-service slot; that remaining work moves to M8, with subsequent planned work shifted in the current roadmap. Historical milestone records remain unchanged. No resources, Azure calls, embeddings, agents, deployments, new dependencies, commits or pushes were created. **Stop after Milestone 7.**
