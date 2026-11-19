# M25 P1 — Pure evidence amendment and reassessment planner

Status: **PLANNING CORRECTNESS ONLY**. Implementation authorised from clean baseline
`89e18be56d02556fe40e2feda80c186b180503ef`. This packet contains new authored development
tests, not independently approved claim labels or an operational integration acceptance.

## Capability and usage

[Planner](../../../src/claims_ai/amendments.py) and
[focused tests](../../../tests/test_amendments.py) implement a pure bounded comparison:

```python
from claims_ai.amendments import AmendmentRequest, canonical_plan, plan_amendment, source_binding

# source_case: validated, host-supplied synthetic Case (not read by the planner).
# candidates: tuple of ProposedDocument metadata, not actual document bytes.
request = AmendmentRequest(
    expected=source_binding(source_case),
    proposed_documents=candidates,
)
plan = plan_amendment(source_case, request)
payload = canonical_plan(plan)
```

The proposed inventory is the **complete desired set**: omission means removal. An empty
inventory removes all documents; it never establishes that missing evidence is satisfied.
Added/removed/replaced references include document ID, artifact hash and metadata hash.
References and proposal inventory are sorted by document ID. Fixed versioned enum order
defines reasons, requirements, invalidations and preconditions. Serialization uses sorted
JSON keys, two-space indentation, ASCII escapes, no non-finite numbers and a final newline.
There is no clock, random identifier or mutable global execution state.

`ProposedDocument` reuses M6's domain `DocumentMetadata` validation and allows only
quarantined candidates. A proposal cannot assert scan acceptance. The comparison excludes
scan status: submitting unchanged metadata is a no-op, not a scan-status update. The exact
source-case hash still includes original scan status, evidence, policy and all other case
fields. Any other metadata change, including a changed upload time with unchanged bytes,
is a replacement. Conflicting intrinsic media/size/page claims for the same hash fail closed.
Matching metadata hashes **do not prove authenticity or possession of actual bytes**.

P1 caps each source/proposed inventory at 64 documents, each declared document at 10 MiB,
source evidence at 1,024 records and canonical source case at 4 MiB. These conservative
budgets align with M12's evidence-input cap, the local configuration's default document
limit, M6's default record limit and M15's default snapshot budget. They do not raise any
existing service limit. This is an in-memory typed interface, not a bounded file/body loader.
Case and request instances are revalidated, including nested unvalidated model copies.

## Existing boundaries reused, without integration

| Existing control | P1 relationship |
| --- | --- |
| [M6](../../../src/claims_ai/evidence/contracts.py), [domain](../../../src/claims_ai/models.py) | Reuses document identity, ownership, hash, synthetic scope and metadata contracts. Plans require actual bytes/size/hash/ownership checks, host scan clearance and fresh extraction/provenance/admission. No evidence is admitted. |
| [M15](../../../src/claims_ai/human_review/service.py) | A changed inventory requires invalidating old reviewed facts, advice and review bindings through existing host controls, clearing assignments and obtaining fresh canonical human review. No review session, decision or invalidation request is created. |
| [M20](../../../src/claims_ai/outcomes/reducer.py) | Reuses correction semantics as requirements: clear derived material and revalidate the entire remaining inventory. Closed cases require supervisor reopening first. Later execution must check supported lifecycle transitions and their actual revisions; P1 constructs no replacement Case or transition sequence. Independently supplied synthetic approval remains separate from API/UI recommendation approval. |
| [M21](../../../src/claims_ai/security_hardening/bindings.py) | Plans require current identity/revocation/canonical-scope checks at later execution. P1 accepts no credentials, grants, roles, assignees or approvals and does not authenticate anyone. It cannot grant or restore authority, including on repeated plans. |

Output always has `execution_authorized=false`, `final_outcome=null` and
`settlement_authorized=false`. A source binding is a comparison precondition, not an
authorization token. Repeated plans are deterministic computations, not durable duplicate
receipts. A forged/edited plan is untrusted data; later integration must recompute against
trusted current state and enforce existing service gates rather than execute a serialized
plan on its own authority. Source Case and policy hashes use the existing canonical JSON
convention. Existing signed snapshots and source ordering are not normalized or rewritten.
`case_revision` is the domain Case revision, not an M15 review revision or M20 store revision;
later callers must obtain and check those independent bindings through the existing services.

All changes conservatively invalidate admitted evidence, reviewed facts, policy selection,
rule results, advisory, review bindings and assignments. Prior outcomes/audit history are
not erased or altered. No-op plans require no revalidation; unchanged rejected/quarantined
metadata is not elevated to accepted evidence. Preconditions remain explicit in every plan.

## Validation and reproducibility

[Verification](verification.json) binds the new implementation, tests, this explanation,
milestone record and raw validation reports by byte size and SHA-256. It records exact
commands, installed tool versions, test totals and preservation checks. SHA-256 inventories
are integrity evidence, not signatures or independent reviewer approval.

Two separate focused pytest invocations retain [run 1](focused-run-1.xml) and
[run 2](focused-run-2.xml). The reproducibility test records canonical plan hash/length,
source-case hash, proposal hash and ten repetitions with reversed proposal ordering in
JUnit properties. These properties must match between runs; report timestamps/durations
are not required to match. [Regression results](regressions.xml) cover existing pure models,
lifecycle and selected M6 normalization cases. No M6 corpus-rendering demo, M12 framework
run, API/UI/MCP transport, SQLite recovery, historical checkpoint replay or M24 G1 batch
is run. Targeted denied-access patches and static imports test the new pure dependency
surface; they are **not OS isolation or process-containment evidence**.

Final results: **64 focused tests passed in each of two invocations; 114 existing regression
tests passed** (178 distinct tests, no failures/skips). The recorded 3,377-byte canonical
development plan has SHA-256
`d698a9c11555c8b6bf1d3cad5c16892cf6a1490958e858a3fd752feffc8b92a4`
in both invocations, with ten reversed-order repetitions per invocation. Repository-wide
Ruff lint/format checks and strict mypy passed; `pip check` found no broken requirements.
The environment is local CPython 3.12.8 on macOS arm64, not Linux/container/wheel validation.

## Limitations and P2 decision

**P2 GO for separately scoped offline contract work and pure tests only.** An amendment
executor, API endpoint or service/recovery integration is not accepted by P1. A later
proposal must specify trusted source acquisition, supported lifecycle/state handling,
current M21 identity and canonical assignment checks, M15 invalidation, M20 independent
approval and atomic audit/outbox, bounded disposable execution and its approval/isolation
requirements before integration testing. P1 grants no demonstration approval.

Adding this module changes the whole-package source fingerprint used by M12/M20. P1 does
not read, migrate, replay, repair or rehash historical checkpoints, SQLite stores or anchors.
Future integration must use fresh same-runtime state and independently retained trust.

Historical boundaries remain: M8 26/30 and four recorded failures; M12 cooperative timing
limitations; corrected M19 80 PASS / 0 FAIL / 8 NOT_TESTED with original evidence retained;
M22 60 PENDING_REVIEW candidates and 12 independent-quality metrics NOT_TESTED;
M23 **DEFERRED — SECURITY GATE NO-GO** and unconditional B1 build refusal;
M24 **OFFLINE DOCUMENTATION COMPLETE / EXECUTION BLOCKED / DEPLOYMENT NO-GO**,
with all six demonstrations NOT_TESTED. No production security/quality claim is made.
