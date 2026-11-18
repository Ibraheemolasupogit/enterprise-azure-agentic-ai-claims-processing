# M24 — Readiness and portfolio evidence

**OFFLINE DOCUMENTATION COMPLETE / EXECUTION BLOCKED / DEPLOYMENT NO-GO.**

P4 consolidation, 2026-11-18, bound to Git `11a64399d8e0166d2e1087dcb8e43242a7a7b711` plus the uncommitted documentation listed in [P4 verification](m24-p4/verification.json). This closes the authorized documentation scope only. M24's original end-to-end demonstration and restore/recovery exit evidence is **not fulfilled**; no operational, independent-quality, production-security or deployment acceptance is granted. All six M24 demonstrations remain **NOT_TESTED**.

## Verified capability inventory, not new execution

The [P1 catalogue](m24-p1/README.md) covers **23/23 milestones** with implementation, evidence availability, environment, limitations and approvals. Its [machine catalogue](m24-p1/catalogue.json) and [154 file hashes](m24-p1/evidence-hashes.json) distinguish code existence, historical scoped validation and independent acceptance. Historical reports were inspected/hashed, not rerun.

| Milestones | Implemented or documented capability | Acceptance boundary retained |
| --- | --- | --- |
| M1–M3 | Charter, architecture/requirements/authority decisions; typed domain models, guarded lifecycle, logging, protocols and engineering tooling. | Reference/local scope; no live insurer identity, service or business-performance acceptance. |
| M4–M9 | Synthetic development corpus, SIMULATED extraction benchmark, byte/source/evidence validation, exact-version lexical policy retrieval/evaluation and provisional deterministic rules. | Authored development expectations, draft policies and non-binding illustrations. M8 retains **26/30** with **Q-007/Q-012/Q-015/Q-029** failures; no approved coverage outcomes. |
| M10–M14 | Genuine bounded Agent Framework/tool execution, six-stage workflow/checkpoints and genuine MCP stdio/HTTP interfaces over three governed read-only services. | Scripted model/provider responses and synthetic grants; APIM remains static. M12 cooperative timing/retry-history limitations remain; no live-model quality or general durable workflow service. |
| M15–M19 | Canonical synthetic human assignments/supervisor review; FastAPI/ASGI and reviewer HTML; offline identity verification and adversarial controls. | API/UI approval is **recommendation approval**, not M20 publication or a human case outcome. M19 original **79 PASS / 1 FAIL / 8 NOT_TESTED** and corrected **80 PASS / 0 FAIL / 8 NOT_TESTED** remain distinct. No production authentication/security acceptance. |
| M20–M21 | Separately supplied host-approved synthetic Assessments; current canonical human authority; atomic SQLite outcomes/audit/receipts/outbox; same-runtime recovery; authenticated grant expiry/revocation/disablement. | No automatic advisory-to-outcome promotion. Fresh current authority, independently retained trust context/keys/anchors and exact source/runtime remain necessary; local SQLite, shared revocation/admission and host-compromise limits remain. No live Entra acceptance. |
| M22 | Offline engineering evaluator, genuine local SDK telemetry, redaction, dashboard/alert specifications, fault/recovery infrastructure and independent-review packet. | Historical [Stage B](milestone-22-stage-b.md): **1,436 source and 1,436 installed-wheel tests; 17 operational controls**. Not rerun by M24. Offline engineering remains conditional; **60 PENDING_REVIEW** cases and **12 independent-quality metrics NOT_TESTED**, no held-out release/scoring. |
| M23 | Offline Azure IaC/deployment contracts, supply-chain admission hardening, pinned artifact integrity and security/remediation investigations. | **DEFERRED — SECURITY GATE NO-GO**. No Linux container build/run or Azure deployment acceptance. B1 still unconditionally refuses builds. [M23's exact reopening criteria](milestone-23.md#explicit-reopening-criteria) remain authoritative. |

## Completed M24 checks and exact evidence

| Stage | Completed check / observed result | Retained evidence |
| --- | --- | --- |
| P1 | 23-milestone catalogue; 175 references (**133 Git-tracked / 42 ignored-local-only**), 154 file hashes, 39 historical pin matches, 222 local-link checks; eight evidence/environment/publication gaps retained. | [Catalogue](m24-p1/catalogue.json), [hash inventory](m24-p1/evidence-hashes.json), [verification](m24-p1/verification.json). Directory references have no single digest; hashes are not authentication or new acceptance. |
| P2 | Architecture reconciliation and six-scenario design; five existing CLI contracts, 13 entry-point symbols and 12 selected test functions checked statically. | [Design/commands](m24-p2/README.md), [bindings](m24-p2/verification.json). No demonstration/test execution. |
| P3A | Six fixture IDs, two rules manifest members, seven identity members and six candidate inventory members verified; metadata matches all 39 runtime pins. Writable historical paths and absent containment/controller receipts recorded. | [Preflight/matrix](m24-p3a/README.md), [verification](m24-p3a/verification.json). Python/native imports and enforcement NOT_TESTED. |
| P3B | A native isolation bootstrap, not a claims demonstration, returned **71** in **0.006855 s**: `sandbox-exec: sandbox_apply: Operation not permitted`. `/usr/bin/true` did not launch. Required policy could not be applied; further probes stopped. Fresh private directories verified; isolation, inheritance and resource enforcement remain NOT_TESTED. | Byte-identical archived [bootstrap receipt](m24-p4/p3b/bootstrap-result.json) and [failed profile](m24-p4/p3b/bootstrap-profile.txt). Original full decision, preservation record and private session remain local-only; their hashes/paths are bound in P4 verification and [P3C](m24-p3c/verification.json). |
| P3C | Twelve local primary-source/metadata bindings support alternative assessment. Apple documents legacy API deprecation and recommends App Sandbox. Applying it inside an already restricted context is a **leading explanation**, not proof of the exact denying profile. `ps` and virtualization-support queries were denied. No alternative implemented. | [Assessment](m24-p3c/README.md), [bindings](m24-p3c/verification.json). App Sandbox is a candidate only; VM/privilege/runtime prerequisites remain unverified. |
| P4 | Existing stage bindings and historical pins rechecked; this consolidated decision, six NOT_TESTED statuses, reopening conditions, documentation consistency and exact manual-review list recorded. | [P4 verification](m24-p4/verification.json). Only current README/roadmap status is amended; earlier stage records remain historical. No application code, historical dataset/report, dependency, test, security gate or frozen pin changed. |

Archival copies above preserve existing bytes; they are **not regenerated evidence or a new probe**. Receipt SHA-256: `25e924642806d6e62a171201dfc0d2cc28c62ec673d273fd8ce89af3a65e8de0`. Failed-profile SHA-256: `c60efe20fa6f8cb61a14badd065343c77a646ba2ecbf0b7c1861da9886cf6fb9`. The profile is failed historical evidence, not an approved or executable isolation recommendation.

## Demonstration status

| P2 scenario | M24 status | Reason |
| --- | --- | --- |
| D01 Normal advisory | **NOT_TESTED** | G1/API/UI demonstration not run. |
| D02 Missing evidence | **NOT_TESTED** | Designed fixture/assertions not executed. |
| D03 Supervisor escalation | **NOT_TESTED** | Designed workflow/API/UI assertions not executed. |
| D04 Unauthorised access | **NOT_TESTED** | No new API/UI/MCP negative demonstration. |
| D05 Revoked replay | **NOT_TESTED** | No new lifecycle/outcome replay demonstration. |
| D06 Recovery/failure handling | **NOT_TESTED** | No new checkpoint, SQLite, crash, telemetry-failure or outbox exercise. |

P3B's failed isolation bootstrap is neither a PASS nor a failed claims-processing demonstration. Historical M12/M19/M20–M22 results do not fill these six M24 rows. Current reproducibility, trace continuity, redaction and recovery assertions also remain unexecuted.

## Blockers and limits

- **Isolation/execution:** policy installation failed; no supported ready host runner, reviewed entitlements/runtime packaging, inherited network/read-only enforcement, descriptor controls, independently bounded supervisor or complete positive/negative containment receipt exists. Per-process limits do not establish P3A's aggregate **1 GiB** scratch cap. A normal-user App Sandbox runner is only a separately reviewable design candidate. No uncontained, elevated or deprecated-API fallback is accepted.
- **Security/deployment:** M23 retains unresolved High findings/applicability, authenticated provenance/reviewer requirements, incomplete CPython/bundled OpenSSL/Cargo/native coverage and licence/runtime gaps. Its historical Trivy database is **1,764,941,824 bytes**, above the unchanged **1,073,741,824-byte** cap. A complete authenticated compatible database within that cap and at most seven days old at admission is not established. Zero unresolved Critical/High thresholds, false-only deployment gates and B1 refusal remain unchanged. No new CVE scan or remediation conclusion is made here.
- **Cloud/production:** real Entra/OIDC/APIM, approved policies, production persistence/telemetry adapters, private networking, restore/migration/rollback, infrastructure risks including AZU-0058, costs and approvals remain open. No Azure environment was deployed by these stages; the existing [lifecycle/teardown approval plan](../deployment/m23/lifecycle-and-approvals.md) remains prospective. M24 does not reopen M23.
- **Independent quality/evidence:** M22 review/verifier and live-quality capabilities are unavailable; no reviewer, signature or approval is fabricated. P1 G01–G08 remain open, including unlocated historical raw receipts, qualified environment details and local-only security archives. Git publication does not make those archives portable or independently authenticated. This packet preserves the small P3B failure receipt; it does not close the wider gaps.

## Conditions to reopen offline demonstrations

All conditions require actual source-bound evidence and separate approval; this list grants no execution permission.

1. **Approve a supported host-isolation implementation separately.** Review signing/entitlements, exact Python/dependency/executable chain, non-elevated launch context, read-only source/fixtures and denied historical-state/credential access. Do not reuse the failed P3B directory as a fresh session or infer a supported mechanism from installed binaries. No application/dependency/security-gate changes are implicit.
2. **Demonstrate containment before any claims payload.** Harmless positive/negative tests must prove permitted private writes and required local IPC, denied network/listeners, protected-source/history/SQLite write-open denial without mutation, disposable alias/rename/unlink/truncate denial and child/grandchild inheritance. Close inherited writable descriptors. Establish exact scope with real observations, not refused connections, existing hashes or Python patches alone.
3. **Prove the unchanged resource and fail-closed contract.** Enforce five minutes per invocation, thirty minutes per session, **1 GiB aggregate new outputs/temporary state**, bounded capture and owned process-tree termination/reaping. Missing/changed policy, hash, root, limit or receipt must block before a marker payload starts. No polling-only aggregate-cap claim or automatic uncontained retry.
4. **Freeze a fresh execution record.** Bind then-current HEAD/diff, all application source, installed environment, actual fixtures/manifests, approved controller and capture paths/hashes. Require exclusive private roots, reviewed redaction, pre/post preservation and disposable same-runtime state only. Preserve raw repetitions and M12 timing differences; no historical replay/repair/rekey/migration or output overwrites.
5. **Obtain separate demonstration approval.** The smallest proposed first batch remains **G1 twice**, covering D01–D03 and only D06's workflow portion; other demonstrations remain NOT_TESTED. Full P2 coverage is G1–G5 twice plus G6 once, with explicitly approved synthetic outcome publication, disposable corruption/restart/SIGKILL and cleanup. No automatic progression from isolation proof to demonstrations.

M22 independent scoring and M23 container/cloud execution have **separate** reopening requirements. They need not be enabled to run a later correctly isolated, unscored synthetic G1 batch; their restrictions must remain enforced. No demonstration can establish independent quality or deployment acceptance by implication.

## Manual Git review and final decision

The exact **16-file** review list is in [P4 verification](m24-p4/verification.json): README and roadmap status edits; this record; ten existing P1/P2/P3A/P3C documents; P4 verification; and the two small P3B archival copies. Review/stage only those named text files manually. Do not include downloaded wheels/layers, databases, ignored historical outputs, temporary execution directories, host SDKs, credentials or the full private preservation records. Earlier documents retain their stage-specific dates/decisions; this record is the current consolidated status.

**Manual Git readiness: GO for review and a manual documentation-only commit of that exact set.** The index remains untouched; no commit/push or application/runtime validation is performed by P4. Documentation checks and byte preservation are the acceptance basis for **documentation closeout only**.

**Final milestone decision: OFFLINE DOCUMENTATION COMPLETE / EXECUTION BLOCKED / DEPLOYMENT NO-GO.**
