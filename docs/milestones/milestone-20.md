# Milestone 20 — Durable human case outcomes and recovery

Status: **COMPLETE within the bounded offline synthetic foundation scope**, verified 2026-11-10. Bounded offline synthetic SQLite foundation, not production deployment or real insurance authority. The explicit M20 request authorises local persistence and supplied synthetic case dispositions; M15 recommendation approval and M9 provisional policy/rule status remain unchanged. No M21 work is included.

## Delivered scope

Ten modules under `src/claims_ai/outcomes/`: typed commands/approval/recovery/state/audit contracts, current authority, recovery validation, pure lifecycle reducer, SQLite adapter, explicit fixture authoring, trusted fault worker, reproducible evidence and CLI. New focused tests, [architecture](../architecture/governed-durable-outcomes.md), [ADR-0003](../architecture/decisions/0003-local-synthetic-outcomes-and-recovery.md) and chained constraints. README, Makefile, MANIFEST, security/target architecture, risk register, requirements traceability and roadmap are updated. Prior runtime modules and historical milestone records remain unchanged.

Publication requires an independent host-approved synthetic test assessment and original source proof, plus an opaque publication permit. No M9 outcome mapping or M15 action promotion exists. Fresh existing capabilities/canonical sessions, exact case assignments, source/approver separation, full bindings, supervisor guards and timestamps protect each human action. No credential or restored role field grants authority.

Eleven SQLite tables atomically retain state, assessment versions, decisions, assignments, receipts, append-only audit, source bytes/checkpoints and local outbox/sink history. BEGIN IMMEDIATE, FULL synchronous DELETE journal and exact in-transaction bindings provide bounded local durability/CAS. Every read/mutation verifies schema/runtime, integrity, independent source equality and complete semantic audit replay. No automatic repair, migration or source rehashing exists.

Corrections invalidate assessments, remove admitted evidence and require actual M12 byte/provenance revalidation; new publication/assignment is separate. Supervisor reopening returns to VALIDATING. Prior input/assessment/decision versions remain reconstructable. Outbox delivery is a local metadata ledger only, with three-attempt dead-letter handling and one idempotent local sink receipt.

## Verification

| Verification | Result |
| --- | --- |
| Focused M20 | **99 passed in 181.23 seconds**, including actual SQLite, canonical authority, signed M18 revocation and subprocess faults |
| Full source pytest | **1,227 passed in 533.07 seconds**: prior 1,128 plus 99 M20 tests |
| Independent installed-wheel pytest | **1,227 passed in 530.25 seconds**, no warnings; isolated Python, separate target, pytest source path replaced and all loaded application origins checked |
| M19 adversarial regression | All 153 adversarial/remediation pytest cases retained in both full suites; new source/wheel evaluations are byte-identical at **80 PASS / 0 FAIL / 8 NOT_TESTED**, with unchanged 88 scenarios/criteria |
| Ruff / strict mypy | Lint/format pass; strict typing passes across **141** source/test Python files |
| Dependencies | `pip check` passes; all **37** nested M20/M19/M18/M17/M16/M13/M10 pins match; **zero new dependencies**, standard-library SQLite **3.45.3** |
| Package verification | Offline wheel/source archive; **115 runtime Python modules plus py.typed** match source and tested installation; all **378** nonignored repository files match the source archive byte for byte |
| Reproduction | Two source and one independent installed-wheel M20 CLI demonstrations are byte-identical: **13 scenarios and seven actual SIGKILL/restart probes per demonstration** |
| Preservation | All **153** pre-existing output artifacts, **164** reference-data files, prior runtime/tests and original milestone records remain byte-identical; historical M16 OpenAPI is unchanged |

Reports: `outputs/outcomes/m20-source-verified-a.json`, `m20-source-verified-b.json` and `m20-wheel-verified.json`. Common SHA-256: **`5a7797e44f9f39b07c94ce483547c0270abe7e2d55a811f7f22f0604b2dd555c`**. Runtime fingerprint: **`66fca831561e671c032cd3ff629c1f23d471812f456916c25678638fe8530171`**. `m20-reproduction-verification.json` records equality, the preserved M19 criteria/NOT_TESTED identities, counts and hashes. M20 reports contain no credentials, raw evidence or actual insurance authority and record zero Azure, live-model, payment, notification or external-delivery operations. Existing M12 simulated advisory preparation is explicitly labeled; replay/commit makes no model calls.

M19 regression artifacts are separately named `outputs/adversarial/m20-source-regression.json` and `m20-wheel-regression.json`; original reports are not overwritten. Package artifacts, independent pytest log and byte/hash verification are under `outputs/packages/m20/`. Independent tests share the existing pinned dependency environment and repository reference fixtures. Historical CLI tests retain deliberate source-launch paths; the M20 and adversarial CLIs are additionally launched outside the repository against the independent installation, without PYTHONPATH or editable installation.

Exact created/modified paths and artifact hashes are in `outputs/packages/m20/package-verification.json`. M20 creates ten runtime modules, one test file, three architecture/ADR/milestone documents and one constraints file; it modifies eight existing documentation/build files. No existing runtime, earlier test, dataset or original milestone record is rewritten.

 Actual SIGKILL probes cover after-projection, after-audit, pre-commit, post-commit/lost-ack, sink-before-ack and delivery-commit boundaries. Tests also cover independent connection/process races, duplicate/revoked/stale requests, changed source correction/revalidation, wrong authority/role/case/permit, signed M18 revocation, corrupt/rehash-forged projections and incompatible schema/runtime.

The initial focused run had 80 passes and three test-fixture/expectation failures: evidence-request actions invalidate their old assignment binding; a deliberately stale revision exceeded the DTO limit; a copied rollback database had public permissions. Fixtures now renew current assignment where required, use an in-range stale value and restore private permissions. Controls were not weakened. The following 93-case run passed before adding final changed-source/identity integration coverage.

## Limits and acceptance boundary

All outcomes are supplied synthetic test dispositions, not actual coverage, payments or settlement. M9 remains unapproved; M15 remains advisory-only. No API/UI redesign or new outcome endpoint is added. Current identity, session delivery, approval registry and host/OS remain trusted; no real Entra provider exists. SQLite triggers/hashes do not prove WORM/host-compromise protection; independently retained heads are required to detect coherent database rollback. Recovery requires the same runtime and independently provisioned historical approval/principal context. No automatic version migration or live policy publication is implemented.

Process termination is proved locally; power failure, storage hardware/OS guarantees, PostgreSQL/cloud recovery, shared authentication/revocation, distributed delivery and production retention remain unverified. The local outbox has no external consumer or notification path. M8 Q-007/Q-012/Q-015/Q-029 and M12 timing sensitivity remain documented, and all eight M19 production scenarios remain NOT_TESTED.

**Acceptance recommendation: ACCEPT M20 within the requested bounded offline synthetic scope.** Source, wheel, real process-crash, concurrency/replay and artifact evidence support that scope. This is not production-security, real-human identity, approved insurance policy or cloud-durability acceptance.

No Azure operations/spending, live model/provider calls, new agents, real insurance authority, payments/communications, Git staging/commits/pushes or M21 implementation. Stop after M20 for review.
