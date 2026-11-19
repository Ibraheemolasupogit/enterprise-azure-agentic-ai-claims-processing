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
