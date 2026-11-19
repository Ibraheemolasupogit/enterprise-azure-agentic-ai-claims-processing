# Milestone 25 — Evidence amendments and reassessment planning

## P1: planning correctness only

The authorised first phase adds a pure immutable, versioned metadata planner over existing
synthetic Case/document contracts. It identifies added, removed and replaced evidence,
binds output to the exact source case/policy/revision, rejects stale or conflicting input
and describes required verification, invalidation, reassessment and later authority gates.
It does not execute corrections or grant identity, review or insurance-outcome authority.

Implementation: [amendments.py](../../src/claims_ai/amendments.py).
Tests: [test_amendments.py](../../tests/test_amendments.py).
Contract/boundaries and reproducibility procedure: [P1 packet](m25-p1/README.md).
Actual checks, hashes and counts: [verification](m25-p1/verification.json).

Recorded validation: 64 focused tests passed twice with matching canonical plan hashes;
114 existing pure-domain/M6 normalization regressions passed. Repository-wide Ruff lint,
formatting and strict mypy passed; dependency consistency passed. These are 178 distinct
tests on local CPython 3.12.8/macOS arm64, not a complete source/wheel or Linux runtime run.

Acceptance applies only to pure planning and the recorded targeted regressions, not service
integration, independent claim-quality validation, deployment or demonstrations. No full
application or installed-wheel suite is asserted for this phase. P2 may proceed only within
a separately approved scope; integration needs explicit authority, lifecycle, audit and
execution-containment design. The existing M12/M20 source-fingerprint compatibility boundary
remains: no historical state migration/replay is authorised or performed.

M22 review restrictions, M23 SECURITY GATE NO-GO and unconditional build refusal, M24's
six NOT_TESTED demonstrations and historical M8/M12/M19 limitations/results remain intact.

## P2: dependency invalidation and reassessment planning only

The approved second phase adds a pure planner over P1. It
labels each derived item's dependency on changed evidence, keeps every item conservatively
invalidated, orders reassessment steps, makes per-state lifecycle preconditions explicit
and reconciles repeated or conflicting requests with fail-closed codes. P1 code and evidence
are unchanged; dependency labels never authorise reuse of prior conclusions.

Implementation: [reassessment.py](../../src/claims_ai/reassessment.py).
Tests: [test_reassessment.py](../../tests/test_reassessment.py).
Contract, findings and limitations: [P2 packet](m25-p2/README.md).
Actual checks, hashes and counts: [verification](m25-p2/verification.json).

Recorded validation: 62 focused tests passed twice with matching canonical plan hashes;
472 regressions (P1, models, lifecycle, selected M6, M15, M20, M21) passed. Ruff lint,
formatting and strict mypy passed. Local CPython 3.12.8/macOS arm64 only.

Finding M25-P2-F1: M20 `CORRECT` fails closed for a stored `VALIDATING` case, which occurs
after supervisor reopening or an earlier correction. P2 therefore marks direct correction of
`CLOSED`/`VALIDATING` cases BLOCKED. Amendment remains possible only indirectly, via
independent revalidation of the unchanged inputs first. A bounded M20 remediation is approved
in principle for a later phase and is not part of P2. Integration still
needs separately approved authority, lifecycle, audit and execution-containment design.

## P3: M20 correction-route remediation (Option E1)

The approved third phase fixes finding M25-P2-F1. M20 `CORRECT` now routes a stored
`VALIDATING` case through the existing `validating → awaiting_evidence → validating`
transitions, exactly as it already did for `assessing`. Supervisor reopening of a closed
case, and a second correction before revalidation, therefore no longer require independent
approval of known-stale inputs. The lifecycle table, commands, bindings, audit and storage
schemas, M15 and M21 are unchanged. A pre-implementation check confirmed that the change
grants a `VALIDATING` case exactly the correction authority an `awaiting_evidence` case
already had. The P2 planner's routes are realigned (plan format v2); `EXTRACTING`, which
M20 never stores, stays blocked.

Implementation: [reducer](../../src/claims_ai/outcomes/reducer.py) (one condition) and
[planner routes](../../src/claims_ai/reassessment.py).
Tests: [correction routes](../../tests/test_outcomes_correction_routes.py) and updated
[planner tests](../../tests/test_reassessment.py).
Authority check, tests and limitations: [P3 packet](m25-p3/README.md).
Actual checks, hashes and counts: [verification](m25-p3/verification.json).

Recorded validation: the new route tests failed on the unfixed reducer for the defect itself
(`invalid_transition`) and pass after the fix. 70 focused tests passed twice with matching
canonical plan hashes; 619 regressions (complete M20, P1, models, lifecycle, M15, M21, M22
operational, M19) passed. A full source-tree suite, Ruff, formatting and strict mypy passed.
No historical store, checkpoint or recorded M20 evidence was replayed, migrated or regenerated.
