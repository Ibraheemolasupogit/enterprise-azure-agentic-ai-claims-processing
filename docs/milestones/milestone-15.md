# Milestone 15 — Governed human review workflow

Status: **COMPLETE within the offline synthetic human-review foundation scope**. Offline synthetic human review consumes verified M12 tasks with case-specific assignment, separation of duties, exact snapshot/version guards, immutable audit and process-local CAS. Recommendation approval/rejection is separate from insurance claim approval, denial, payment or settlement. No M16 API or M17 UI is implemented.

## Scope and changes

The approved M15 request supersedes the former roadmap's evidence-ingestion slot. Intake/service integration moves to planned M16 and reviewer UI to M17. Later policy/model/security/operations/deployment deepening remains planned. Historical M1–M14 records retain their original sequencing and evidence.

- New five-module `claims_ai.human_review` package: [contracts](../../src/claims_ai/human_review/contracts.py), [source/audit validation](../../src/claims_ai/human_review/validation.py), [queue/detail service](../../src/claims_ai/human_review/service.py), [offline CLI](../../src/claims_ai/human_review/__main__.py) and initializer.
- New [review tests](../../tests/test_human_review.py) and [architecture](../architecture/governed-human-review.md). README, Makefile, current architecture/security, requirement status, traceability and roadmap updated.
- M2 lifecycle/domain, M9 rules, M12 orchestration and M13/M14 transport/tool code are reused without modification. No dependency or additional agent is introduced. M4–M9 data and historical evaluations remain preserved.

## Actual behavior and authority

Admission reuses M12's pure checkpoint restoration with original bytes, workflow grant and limits; a rehashed forged task cannot pass semantic replay. Bindings pin case/revision/evidence, policy/version/bundle/index, rule version/specification/execution, checkpoint/workflow and advisory/task identities. Successful advisory routes support all four explicit actions. A source-verified rule/agent abstention with a complete context enters supervisor evidence triage only; absent recommendations cannot be approved/rejected.

Opaque host-registered synthetic sessions and canonical principal roles control access. Only assigned humans read or decide; workflow producers and prior reviewed-fact authors cannot review their own work. Agents, MCP/model/host principals cannot act as reviewers. Supervisor assignment is mandatory for adverse, ambiguous, high-risk, conflicting or manually escalated work. The three MCP tools remain read-only and expose no review capability.

Review states are `awaiting_reviewer`, `awaiting_supervisor`, `recommendation_approved`, `recommendation_rejected`, `additional_evidence_requested` and `snapshot_invalidated`. Approvals/rejections/escalations leave the M12 ASSESSING case unchanged. Evidence requests reuse M2's ASSESSING → AWAITING_EVIDENCE transition and increment the case revision, retaining original evidence/history. No operational `Assessment`, final `ReviewerDecision`, closure or insurance outcome is constructed.

Every accepted queue/assignment/action/invalidation event contains actor/kind/role, reason/rationale, timestamp, correlation and chained hashes. A process-local lock atomically commits review revision, immutable event projection, current binding and head. Exact authorized duplicates reuse receipts; altered duplicates, stale revisions/bindings and forbidden transitions fail closed. Semantic replay and a separate memory head detect tested audit tampering/rollback. Host invalidation is required when upstream versions/evidence change; no automatic service-store watcher exists.

## Verification

Environment: Python 3.12.8, Agent Framework 1.23.0, MCP 2.2.0, Pydantic 2.14.2, pytest 8.4.2, Ruff 0.16.10, mypy 1.20.2 and setuptools 82.0.1. No dependency version or optional extra changes. The current project wheel was installed offline into the working environment and an independent package-only target, both without dependency installation.

| Verification | Actual result |
| --- | --- |
| Focused review tests | **84 passed** in 43.58 seconds |
| Complete source suite | **729 passed** in 139.57 seconds: all 645 prior cases + 84 review cases |
| Ruff / strict mypy | Formatting/lint passed; no typing issues in all 93 source/test Python files |
| Wheel / installed bytes | Offline wheel built; all 73 Python modules and `py.typed` match source and the independent installation |
| Independent installed-wheel full suite | **729 passed** in 139.96 seconds; package origin asserted in a package-only target and pytest source-path configuration overridden |
| Source archive | Offline sdist includes current source/tests/docs, constraints, APIM references and all 161 tracked data files; file bytes checked |
| Demonstrations | Two fresh source reports and independent wheel execution from another working directory are byte-identical; six scenarios and 24 accepted audit events |
| Dependency / documentation / preservation | `pip check` passes, all 35 nested M13/M10 pins match; 398 changed-document local links and 14 traceability test names checked; prior runtime/tests/data/evaluation files preserved |

Tests cover explicit actions, separation of duties, synthetic/nonhuman identity, assignments/cross-case scope, all 15 binding fields, adverse/risk/supervisor routing, missing recommendations, snapshot invalidation, concurrent actions/duplicates, rationale/references, audit tampering, time/capacity bounds, source-grant/content/checkpoint forgery, no review model/network calls and CLI/reference protection. The conflicting-amounts M12 fixture genuinely abstains before drafting; its M15 test requires supervisor evidence handling and forbids approving/rejecting an absent recommendation. No fixture or M12 behavior is rewritten to make it approvable.

New reports `outputs/review/m15-verified-a.json`, `m15-verified-b.json` and `m15-wheel-verified.json` have SHA-256 `2e215ab9de99aa278acbe4521fd53703944427787e62432d7041cd2e70e35ec1`. They contain synthetic case detail, not durable audit storage. The original M4–M14 artifacts are not overwritten. The CLI's normal M12 advisory preparation uses the existing simulated client once; review admission/replay/actions make **zero model calls**, with zero live calls, autonomous outcomes, Azure operations or insurance-outcome authority.

| Scenario | Actual result |
| --- | --- |
| Reviewer approval | `recommendation_approved`; case remains ASSESSING, with no final decision |
| Reviewer rejection | `recommendation_rejected`; no insurance denial |
| Escalation and supervisor handling | Reviewer escalates; assigned supervisor explicitly approves the recommendation |
| Evidence request | `additional_evidence_requested`; actual M2 AWAITING_EVIDENCE transition and incremented case revision |
| Stale evidence | Host appends invalidation; old action returns `review_snapshot_stale` without an accepted decision event |
| Unauthorized access | Unassigned synthetic human receives `review_access_denied`, with no review detail |

Final artifacts are `outputs/packages/m15/northstar_claims_ai-0.1.0-py3-none-any.whl` and `northstar_claims_ai-0.1.0.tar.gz`. Wheel SHA-256: `916e71eed137767ec612a0f60428de12e0ea08a6d2d5a0652c947a4e6ae56f6f`. Historical CLI tests retain their explicit source-selection behavior; new review subprocess tests use the active package location and therefore exercise the wheel in the independent suite. No SDK or project runtime class is mocked in the demonstration.

Reproduction (choose a new output filename):

```sh
make review-check
make check
make package
PYTHONPATH=src .venv/bin/python -m claims_ai.human_review --output outputs/review/new-review.json
```

## Production limitations and acceptance boundary

This is an offline in-memory foundation. Synthetic host identity/clock/session delivery are assertions, not real authentication or reviewer identity proof. A same-user trusted host can replace code or memory. SHA-256 histories are unsigned; memory heads are not durable trust anchors. There is no crash recovery, authenticated journal import, durable concurrent cloud store, outbox, notifications, API/UI, operational assessment/outcome commit or real claim authority. Denied attempts do not receive accepted-action audit entries; durable denial telemetry and retention remain planned.

M8 Q-007/Q-012/Q-015/Q-029 and M12's timing-dependent retry/reproduction limitation remain unresolved. No timeouts, retries or historical expected bytes are weakened to mask them. The new modules change future M12 whole-package fingerprints/task keys by design; historical artifacts are not rewritten. Real Entra/APIM enforcement remains planned despite M14's local HTTP/static reference acceptance.

No Azure operations/spending, new agents, live model calls, commits or pushes. **Stop after M15 for review.**

Acceptance is met for a bounded assigned queue, source-linked detail, explicit synthetic human recommendation decisions, supervisor/separation boundaries, exact snapshot/CAS/duplicate guards, immutable local audit and reproduced source/wheel evidence. This does not satisfy production identity, durable outcome commit or service/UI readiness. M16/M17 remain planned.
