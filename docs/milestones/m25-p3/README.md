# M25 P3 — M20 correction-route remediation (Option E1)

Status: **REMEDIATED WITHIN BOUNDED OFFLINE SCOPE**. Implemented from clean published
baseline `43eda8b` (M25 P2) under owner decisions approving Option E1 with no additional
supervisor-role requirement. Synthetic, local and offline only. Not an operational,
deployment or production-outcome acceptance.

## Defect (M25-P2-F1)

M20 `CORRECT` (`src/claims_ai/outcomes/reducer.py`) added an `awaiting_evidence` hop only
from `assessing`, then always stepped to `validating`. A case stored in `validating` arises
after supervisor `REOPEN` or an earlier `CORRECT`. Correcting it therefore attempted
`validating → validating`, which `lifecycle.ALLOWED_TRANSITIONS` does not allow. The store
failed closed (`invalid_transition`, no audit write). The only route was independent
`REVALIDATE` approval of inputs already known to be stale. The P3 tests reproduced this by
execution before the fix: five tests failed for exactly that reason.

## Change

```python
if case.state in (CaseState.ASSESSING, CaseState.VALIDATING):  # was: == ASSESSING
    step(CaseState.AWAITING_EVIDENCE)
step(CaseState.VALIDATING)
```

A correction from `validating` records two transitions, the maximum the existing
`AuditEvent` contract allows. The replacement Case revision must be the stored revision
plus three. Nothing else in M20 changed.

## Pre-implementation authority-path check: PASS

| Control | Why Option E1 preserves it |
| --- | --- |
| Guards apply regardless of state | Known actor, human-only correction, an assignment bound to current inputs and assessment hash, self-review and supervisor-when-required all run before the action branch, unchanged for `validating`. |
| Who can produce stored `validating` | Only supervisor `REOPEN` or assigned-human `CORRECT`. Both clear assignments, so a fresh host assignment is required. Assignment refuses non-human and forbidden principals. |
| What a correction can carry | A replacement Case only, never an approval, decision or assignee. |
| Closed cases | `CORRECT` on `closed` is still refused; reopening remains supervisor-only. |
| Independent approval | `REVALIDATE` requires `parent == current binding` (store revision and case hash), so each correction invalidates any pending approval. |
| Lifecycle table and audit | Unchanged. Both transitions already existed and carry no actor rules for these states. Two transitions fit the existing audit limit. |
| Net effect | A `validating` case gets exactly the correction authority an `awaiting_evidence` case already had. |
| Other layers | M21 wraps authentication only, independent of action and state. M15 is unaffected. M22 drives only `DECIDE`. |

No authority contract, command, binding, audit or storage schema, M15 or M21 change was needed.

## Tests

[Correction-route tests](../../../tests/test_outcomes_correction_routes.py) use temporary
SQLite created by each test:

- **Positive:** closed → supervisor reopen → fresh assignment → correction with genuinely
  changed bytes. Both transitions are recorded, evidence, policy, assessment, decision and
  assignments are cleared, and the prior closure decision is retained. Then independent
  revalidation and separate publication follow. A chained second correction makes the
  approval issued for the first correction stale (`revalidation_binding_required`).
  Existing `assessing` and `awaiting_review` routes are unchanged.
- **Refusals that must still hold** (state unchanged after each): correcting `closed`
  directly; reviewer reopening; unassigned reviewer, supervisor or outsider; agent, MCP or
  model tokens; host; replacement revision offsets 1, 2 and 4; replacements carrying
  evidence or policy, or another policy ID; stale bindings. A supervisor-required
  assessment still refuses a reviewer.
- **Duplicates:** after a correction clears assignments, even an identical replay is refused
  (`assignment_required`), following M20's documented rule that the current assignment is
  checked before duplicate-receipt lookup. After re-assignment the identical request returns
  the original receipt; a changed one fails (`changed_duplicate`).
- **Adversarial:** the approval's own approver cannot be assigned. A forged in-memory state
  injecting that assignment is refused by the pure reducer (`self_review_forbidden`).
  Restart performs full audit replay. A rehashed audit event hiding the invalidation hop
  is detected (`audit_semantics_mismatch`).
- **Contract guards:** the lifecycle table is asserted unchanged, with no
  `validating → validating` self-loop; the audit transition limit is still 2.

**P2 planner alignment:** `validating` is now SUPPORTED via `awaiting_evidence`; `closed` is
SUPPORTED as supervisor reopen then the same hop, with no blocker step; `extracting` stays
BLOCKED. The plan format moves to `m25-reassessment-plan-v2`, so a serialized P2-era v1 plan
is rejected. The P2 reducer drift guard was updated to the new source.

## Validation

[Verification](verification.json) binds the changed files and raw reports by size and SHA-256,
and records commands, environment, the authority check and preservation checks. These are
integrity hashes, not signatures or independent approval.

| Check | Result |
| --- | --- |
| Before the fix | 5 of 8 new tests failed with `invalid_transition`; the 3 tests outside the defect path passed |
| [Focused run 1](focused-run-1.xml) / [run 2](focused-run-2.xml) | 70 passed each (8 route + 62 planner). Canonical v2 plan is 12,476 bytes, SHA-256 `6bb6b87286c2e68cdd25604a5e5e933155cbddfbb17d50d6f7c51b0bb223a2c6`, identical across runs with ten reversed-order repetitions |
| [Regressions](regressions.xml) | 619 passed: complete M20, P1, models, lifecycle, M15, M21, M22 operational, M19 adversarial/remediation |
| Full source-tree suite | Recorded in the verification file |
| Ruff lint/format, strict mypy | Pass |

## Preservation and limitations

- **Package fingerprint** changes again. Existing M20 stores already refuse to open
  (`incompatible_runtime`) since M25 P1. Nothing is migrated, repaired, rehashed or replayed.
- **Recorded histories:** only previously refused sequences become accepted, so they replay
  identically.
- **Frozen evidence:** M20's recorded reports, `outcomes/evidence.py`, `milestone-20.md`, and
  P1/P2 evidence under `m25-p1/` and `m25-p2/` are unchanged. P2's packet remains the accurate
  record of pre-remediation behaviour. Its bindings for the planner, its tests and the shared
  docs are superseded by this phase, following earlier precedent. The 39 historical pins are
  unaffected.
- **Not covered:** no installed-wheel, Linux/container or SIGKILL probe was run for the new path.
  Existing fault-boundary tests are path-independent and pass in the regressions. No API, UI,
  MCP or cloud integration exists for M20 corrections.
- **Gates:** M22 60 PENDING_REVIEW candidates and 12 independent-quality metrics NOT_TESTED; M23
  **DEFERRED — SECURITY GATE NO-GO**; M24 **EXECUTION BLOCKED / DEPLOYMENT NO-GO**, with all six
  demonstrations NOT_TESTED. No production insurance outcome is authorised.
