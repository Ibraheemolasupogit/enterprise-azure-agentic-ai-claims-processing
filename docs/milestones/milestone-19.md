# Milestone 19 — AI threat model and adversarial security testing

Status: **COMPLETE within the offline adversarial-evaluation scope**. Reproducible, bounded security evaluation with explicit findings and untested production boundaries. Verification date: **2026-11-10**. This supersedes the older roadmap's planned M19 agent-workflow deepening; no new agent or M20 implementation is included.

## Deliverables and scope

Nine modules under `src/claims_ai/adversarial/` implement typed catalog/criteria/results, source-pinned loading, in-memory synthetic authoring, actual application/review and framework/tool/MCP/identity probes, the bounded runner and CLI. New [fixtures/manifest/guide](../../data/security/adversarial/v1/README.md), [tests](../../tests/test_adversarial.py), [threat model](../architecture/ai-threat-model-and-adversarial-testing.md) and nested M19 constraints. README, risk register, security/target architecture, traceability, roadmap, MANIFEST and Makefile are updated.

All existing M10–M18 runtime source, domain/rules, earlier tests, datasets, evaluations and milestone records remain untouched. The existing uncommitted M18 implementation and dependency records are preserved. Zero dependencies, live models, identity providers, cloud resources or external attack targets are introduced. Taxonomy documentation references were consulted separately; the evaluation itself runs offline and does not fetch them.

## Attack coverage and observed results

The **88** authored development scenarios cover notes, narrative/extracts/policy content, actual SDK tool/output guards, M11 scope/result handling, genuine MCP Streamable HTTP SDK calls and parser trust, M16/API/M17 form boundaries, M15 assignments/audit/snapshots and M18 signatures/capabilities/revocation. Six positive controls ensure total denial cannot masquerade as security. Attack origin/entry, trust crossing, expected criteria, actual facts, control, execution level, residual risk and normalized evidence hash are recorded per row.

Observed evaluation: **79 PASS, 1 FAIL, 8 NOT_TESTED**, with no harness errors or socket attempts. The CLI deliberately returns **2**, retaining its report instead of calling findings success. The eight unconfigured scopes are not counted as blocked attacks. Model outputs are simulated; actual deterministic consumers run. No live-model semantic resilience, deployed gateway or browser/network security is claimed.

**F-001 / R-008: ADV-MCP-09 FAIL.** The existing MCP consumer accepts policy text changed consistently in both text and structured content after a genuine SDK read. It validates shape/congruence without independent expected-source binding. The adjacent inconsistent-representation case is rejected, and the server rejects altered dependency data before publication. This is a declared compromised-response simulation, not a remote exploit or human/outcome bypass. [Threat-model remediation](../architecture/ai-threat-model-and-adversarial-testing.md#finding-f-001--consistently-altered-mcp-result-accepted) proposes a context/source-bound consumer; existing behavior is deliberately not patched here.

**F-002 / R-009: ancillary legacy M9 CLI FAIL, outside the 88 catalog cases.** The initial outside-directory wheel launch exposed a working-directory-dependent output exclusion: the CLI could create a new report under an adjacent reference-data tree. Exclusive creation still protects existing files. The test-created file was moved to `outputs/packages/m19/legacy-cli-wrong-cwd-generated-report.json`, restoring reference data; originals are unchanged. [The ancillary finding](../architecture/ai-threat-model-and-adversarial-testing.md#ancillary-finding-f-002--legacy-cli-data-root-safeguard-depends-on-launch-directory) records the separate reproduction, local-operator scope and proposed minimal root-binding correction without patching earlier behavior. This is not hidden by rerunning from the documented working directory.

M8's four retrieval failures remain separate and unchanged, including Q-015's command-like policy text retrieved against its authored no-answer expectation. M19 policy cases have a different containment oracle and do not turn that retrieval failure into a pass.

## Verification and evidence

| Verification | Result |
| --- | --- |
| Focused adversarial regressions | **115 passed in 17.77 seconds**: 88 parameterized runtime/catalog outcomes plus scorer, evidence, fixture, network-guard and CLI integrity tests |
| Complete source pytest | **1,090 passed in 298.06 seconds**, including all 975 earlier tests |
| Independent installed-wheel pytest | **1,090 passed in 301.99 seconds**, no warnings; isolated Python, pytest's source path replaced, and every loaded application module verified against the separate wheel installation |
| Ruff / strict mypy | Lint and formatting pass; strict mypy passes across **129 source/test Python files** |
| Dependencies | `pip check` passes; all **37** nested M19/M18/M17/M16/M13/M10 pins match; **zero new distributions** |
| Packaging/import | Offline wheel and source distribution; all **105 Python runtime modules plus `py.typed`** match source and the independent installation. All **361** nonignored source/test/document/fixture/configuration files match the source archive byte for byte. Normal installed imports succeed outside the repository using isolated Python without `PYTHONPATH` |
| Existing API/APIM contracts | Current generated M16 OpenAPI is byte-identical to the historical schema. Unchanged APIM XML/Bicep invariant checks pass in **STATIC_ONLY_NOT_APIM_ENFORCEMENT** mode |
| Reproducibility | Two source demonstrations and one independent installed-wheel demonstration produce byte-identical complete reports: **79 PASS / 1 FAIL / 8 NOT_TESTED**; each exits **2**, with no harness errors, socket attempts or observed operational outcomes |
| Preservation | All **161** reference data files, earlier runtime source, tests and milestone records match their starting bytes; **28** earlier API/UI/review/MCP/identity reports and both M8 verification reports are unchanged |

Reports: `outputs/adversarial/m19-verified-a.json`, `m19-verified-b.json` and `m19-verified-wheel.json`; common SHA-256 **`7e3faefd23333482f6fe5a7e318edf731188ab389471807ff8b85265a0354804`**. `m19-reproduction-verification.json` records byte equality. Runtime fingerprint: **`828931681f1453ef1c83e4273e3957497f75251616019003f3afc49d1c0f6d68`**. Reports contain 58 direct-runtime rows, 15 simulated-model/runtime-guard rows, seven explicitly host-injected runtime-guard rows and eight unexecuted production scopes. Six of the 79 PASS rows are positive controls; no aggregate attack-block percentage is claimed.

Artifacts and verification logs are under `outputs/packages/m19/`. Independent tests share the pinned dependency environment; historical CLI tests intentionally retain source-launch paths, while the M19 CLI is separately launched outside the repository against the independent installed package. No editable installation is relied on. The first wheel-suite launch used `/tmp` as its working directory: historical relative-fixture tests produced **1,078 passed / 2 failed / 10 setup errors**. Ten errors and the M14 failure came from missing relative fixtures; the M9 failure exposed F-002. The failed log and launch metadata are retained as `installed-wheel-wrong-cwd-*`; only the verification launch directory is corrected, without changing tests or application behavior.

Both historical M8 reports retain SHA-256 **`e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`**. The old M14 real-TCP report remains historical evidence, not fresh TCP verification of this evaluation or M18 identity changes. M19's HTTP evidence is in-process ASGI only.

F-002 was independently reproduced using temporary copies of the three M9 specification/fixture files and the installed-wheel CLI, outside the historical data tree. It again created a new sibling-data report (FAIL); direct specification-directory output and existing-file overwrite were rejected. Socket attempts and operational outcomes were zero. `outputs/adversarial/m19-legacy-cli-path-finding.json` records the attempt, expected/observed behavior, control, source hash and normalized evidence hash **`a3fd250f67bdc05fd9a9c306f1b601a783cace86a0fe5e0fb06ab109a2232bae`**. `outputs/packages/m19/package-verification.json` records package/source/installed equality, archive/report hashes and preservation checks.

Initial harness corrections preserved honest evidence: a model dump excluded source bytes, an authored policy line exceeded the existing 94-character fixture layout, and a header probe accidentally combined missing authority with a forbidden RPC body. These were setup/probe issues, not blocked attacks or product fixes. The corrected header probe uses a valid ping with spoofed identity headers and no bearer; authentication still fails. Classification rejects exact-type coercion, unexecuted PASS, unexpected setup failure and a caught network-guard exception. The consistent MCP tampering finding remains visible throughout.

## Acceptance limits

The [risk register](../business/risk-register.md) remains OPEN. F-001 needs separate review before trusting arbitrary MCP results in future advisory consumers; F-002 retains the documented repository-root launch requirement pending a separately approved legacy CLI correction. Live-model/identity/provider/browser/ingress, hostile parsers, distributed resource limits, hard CPU preemption, vector/hybrid retrieval and durable audit/recovery remain NOT_TESTED. Host/OS compromise can replace unsigned evidence/private state; hashes are not signatures or durable retention. M12 timing-dependent reproduction and M15/M17/M18 limitations remain.

**Recommendation: ACCEPT M19 within its offline evaluation scope**, with F-001/F-002 explicitly OPEN. This accepts the truthful harness and evidence, **not production security or remediation of those findings**. No Azure login/provisioning/spending, live provider/model call, autonomous claim approval/denial/payment/settlement, M20 work, staging, commits or pushes. **Stop after M19 for review.**
