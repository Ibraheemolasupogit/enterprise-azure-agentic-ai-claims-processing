# M25 P2 — Controlled dependency invalidation and reassessment planning

Status: **PLANNING CORRECTNESS ONLY**. Implemented from clean published baseline
`fd19899` (M25 P1). This packet contains new authored synthetic development tests, not
independently approved claim labels or an operational integration acceptance.

## Capability and usage

[Reassessment planner](../../../src/claims_ai/reassessment.py) and
[focused tests](../../../tests/test_reassessment.py) extend P1 without modifying it:

```python
from claims_ai.amendments import AmendmentRequest, source_binding
from claims_ai.reassessment import canonical_reassessment, plan_reassessment, reconcile_requests

request = AmendmentRequest(expected=source_binding(source_case), proposed_documents=candidates)
plan = plan_reassessment(source_case, request)          # embeds the unchanged P1 plan
payload = canonical_reassessment(plan)
decision = reconcile_requests(source_case, [request, other_request])
```

`plan_reassessment` recomputes the P1 `AmendmentPlan` through the unchanged
`plan_amendment` and embeds it with its hash. It never accepts a serialized plan as input.
Output is canonical JSON in the P1 convention. There is no clock, randomness or I/O.

### 1–2. Dependency impact with conservative invalidation

Each existing derived item in the source Case is reported. These are evidence records, the
reviewer decision (reviewed facts), the policy selection, each rule result, the advisory
assessment and the external M15 review binding and assignments. Each one gets a dependency
label and fixed-order bases:

| Label | Meaning |
| --- | --- |
| `traced_to_changed_document` | A supplied trace cites evidence from a removed/replaced document, or the change touches policy material (policy artifact ID or policy document kind). |
| `dependency_not_reliably_traceable` | Dependency cannot be established: added documents may supply untraced facts; empty or duplicated rule traces; holistic advisory outcome/rationale/flags; decisions bound to stale advice; M15 bindings to the whole case hash. |
| `no_traced_dependency_on_changed_document` | The supplied trace does not cite changed evidence. Traces are unverified, so this is not evidence of independence. |

**Every item remains invalidated (`invalidated=true`, `reuse_authorized=false`) and carries
the `m20_correction_clears_all_derived_material` basis.** M20 correction requires a
replacement Case with no evidence, policy, assessment or decision. P2 labels only order and
focus later reassessment. They never narrow invalidation. Narrowing would change an
existing authority contract and is out of scope. Advisory output is never labelled untraced.

### 3. Ordered reassessment plan

Changed inventories produce contiguous, uniquely ordered steps: source recheck, M21 identity
recheck, lifecycle prerequisites (below), M15 invalidation, M20 correction, byte/scan/M6
admission (only when documents remain), policy, rules, advisory, fresh human review and
independent M20 revalidation approval. Every P1 requirement maps to a step. `focus` lists
directly affected item IDs to examine first; it never narrows a step. Unchanged inventories
have no impact items or steps.

### 4. Lifecycle preconditions

Routes mirror `lifecycle.ALLOWED_TRANSITIONS` and the M20 `CORRECT`/`REOPEN` branches.
Tests check every listed transition against the table, call the pure `transition_case`
to confirm supervisor requirements, and include a source drift guard on the reducer.

| Source state | Route | Notes |
| --- | --- | --- |
| `QUARANTINED` | SUPPORTED → `validating` | Lifecycle requires a supervisor; explicit supervisor step. |
| `ASSESSING` | SUPPORTED → `awaiting_evidence` → `validating` | M20 adds the intermediate hop. |
| `PROCESSING_FAILED` | SUPPORTED → `validating` | Full revalidation required. |
| `CLOSED` | **BLOCKED** (direct) | Supervisor reopening lands in `validating`. A direct M20 `CORRECT` then attempts `validating → validating`, which the lifecycle table does not allow. |
| `VALIDATING` | **BLOCKED** (direct) | M20 stores this state after `REOPEN` or a prior `CORRECT`. A direct `CORRECT` attempts the same disallowed self-transition. |
| `EXTRACTING` | **BLOCKED** | No `→ validating` edge. M20 never stores this state: revalidation passes through it within one command. |
| `RECEIVED`, `AWAITING_REVIEW`, `AWAITING_EVIDENCE` | SUPPORTED → `validating` | |

**Finding M25-P2-F1 (corrected wording):** M20 `CORRECT` fails closed for a stored
`VALIDATING` case, before any audit record is written (`invalid_transition`). That state
arises after a supervisor reopens a closed case and after an earlier correction. A direct
correction of a reopened case, and a second correction before revalidation, are therefore
unavailable. **Amendment is not impossible:** by code reading (not executed), the case can
first be revalidated with a new independent approval of its *unchanged* inputs, reach
`assessing`, and then be corrected. That indirect route needs approval of inputs already
known to be stale, so P2 still reports the direct route as `BLOCKED` with an explicit
`resolve_unsupported_m20_correction_route_before_execution` step. P2 code identifiers
`reopened_validating_case_has_no_m20_correction_route` and
`in_flight_processing_state_has_no_m20_correction_route` refer to the direct `CORRECT`
route only. P2 does not change the lifecycle table or M20. A separately approved bounded
remediation will route `validating` through the existing `awaiting_evidence` transitions,
as M20 already does for `assessing`. Route `SUPPORTED` means only that the lifecycle table
permits the transitions. M20 assignment, self-review, supervisor and approval checks still
apply at execution.

### 5. Conflicting and repeated requests

`reconcile_requests` handles 1–16 requests against one source, independent of order:

1. Any request failing P1 binding/metadata checks rejects the set (`invalid_request_rejected`)
   with sorted unique codes: `wrong_claim_binding`, `wrong_policy_binding`,
   `stale_case_revision`, `source_hash_mismatch`, `conflicting_artifact_metadata`.
2. Otherwise, differing desired inventories are rejected (`conflicting_desired_inventories`)
   with no plan and no merging.
3. Otherwise, identical repeats yield one byte-identical plan (`repeated_identical_request`).

Empty sets and sets over 16 fail with `empty_request_set` / `request_capacity_exceeded`.
Replaying a request after the source revision advances is rejected as stale. The decision
is a deterministic computation. It is not a durable idempotency receipt
(`durable_receipt=false`). Forged nested inputs are revalidated.

### Authority and integrity

Plans and decisions are frozen, forbid extra fields and validate internal consistency on
load. They check P1 hash, step order and requirement coverage, the canonical lifecycle
route, state-specific steps and status/code agreement. Fields `execution_authorized`,
`reuse_authorized`, `automatic_transition`, `settlement_authorized` and `durable_receipt` are
fixed to false, and `final_outcome` to null. Output contains IDs and codes only, not
narrative, observed values or rationale. The module's imports are limited to
the standard library, pydantic, `claims_ai.models` and `claims_ai.amendments`.

## Validation and reproducibility

[Verification](verification.json) binds the new implementation, tests, documentation and
raw reports by size and SHA-256 and records commands, tool versions and preservation checks.
SHA-256 inventories are integrity evidence, not signatures or independent approval.

Two separate focused invocations retain [run 1](focused-run-1.xml) and
[run 2](focused-run-2.xml). The canonical development plan has 12,476 bytes and SHA-256
`3641f433537812d2250a3b4774f1579d29ae452dc5a7f119437522d5803b876d` in both runs, with ten
reversed-order repetitions per run. [Regressions](regressions.xml) cover P1, domain models,
lifecycle, P1's selected M6 normalization cases and the M15 human-review, M20 outcomes and
M21 security-hardening suites. Those suites use temporary SQLite files created by the
existing tests. No historical store or checkpoint is opened. A full source-tree suite run is
recorded in the verification file. In-process denied-access patches are **not OS isolation
or process-containment evidence**.

## Preservation and limitations

`src/claims_ai/amendments.py`, `tests/test_amendments.py` and all `m25-p1/` evidence are
unchanged and are hash-checked by a focused test against the P1 record. Following the
earlier milestone precedent, appending P2 sections to `README.md`, `roadmap.md` and
`milestone-25.md` supersedes P1's point-in-time bindings for those three shared documents.
Their P1 bytes remain verifiable at commit `fd19899`.

Planning analyses only the supplied Case. It does not read external M15 review stores, M20
stored cases or approvals. It treats supplied rule traces as unverified, and checks
metadata, not document bytes or authenticity. No installed-wheel or Linux/container run was
performed. Adding this module changes the whole-package source fingerprint used by M12/M20.
No historical checkpoint or store is read, migrated or replayed.

Historical boundaries remain unchanged: M22 60 PENDING_REVIEW candidates and 12
independent-quality metrics NOT_TESTED; M23 **DEFERRED — SECURITY GATE NO-GO**; M24
**EXECUTION BLOCKED / DEPLOYMENT NO-GO** with all six demonstrations NOT_TESTED. No API
endpoint, persistence, asynchronous execution, cloud use or automatic case reopening is
implemented or authorised.
