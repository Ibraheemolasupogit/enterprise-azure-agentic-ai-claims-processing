# Milestone 10 — Microsoft Agent Framework foundation

Status: **COMPLETE within the bounded offline foundation scope**. Actual Microsoft Agent Framework code is constructed/executed; the model client and scan/reviewer assertions are explicitly **SIMULATED**. No live model/cloud service or autonomous claim outcome exists. M11 has not started.

## Files and framework functionality

- New `claims_ai.agents` [contracts](../../src/claims_ai/agents/contracts.py), [host preflight](../../src/claims_ai/agents/prepare.py), [supported offline client](../../src/claims_ai/agents/offline.py), [assistant/guards](../../src/claims_ai/agents/assessment.py), [CLI](../../src/claims_ai/agents/__main__.py) and initializer.
- New [focused tests](../../tests/test_agents.py), [architecture guide](../architecture/agent-framework-foundation.md), [runtime constraints](../../requirements/m10-constraints.txt), [dependency/API record](../dependencies/agent-framework.md) and this completed evidence record. Updated README, architecture status, traceability, roadmap, Makefile, manifest, optional dependency declarations and environment-backup exclusions.
- Existing domain/lifecycle/ports and M4–M9 source/tests/data are unchanged. The user's backup environment is untouched. Discovery was initially blocked; resumed work verified the real isolated SDK and replaced that blocked status with tested integration.

Installed SDK **agent-framework-core 1.23.0** and **msgspec 0.22.0** are exercised through real `Agent`, `FunctionInvocationLayer` + `BaseChatClient._inner_get_response`, `_validate_options`, `FunctionTool`, `Message`, `Content.from_function_call`, `ChatResponse`, `Agent.run` and `AgentResponse.value`. Runtime options include a Pydantic response format, token option, sequential tool choice and disabled storage. The real SDK executes the tool roundtrip and parses structured output; it is not replaced by mocks. The [dependency record](../dependencies/agent-framework.md) links authoritative documentation, exact installed versions and the tested signatures.

The one case-bound `read_review_packet` function is read-only and accepts no model-supplied arguments. The assistant implements a constrained review/explanation foundation within the existing two-agent design, not a new coverage or supervisor authority. Every statement/status/reference must exactly match validated deterministic findings. Free-form reasoning and live model quality are not demonstrated by this scripted client.

## Safety boundaries

Host code revalidates M9 findings and M6 evidence through the unchanged rule path, verifies exact M7 response/version/citations and prepares the bounded immutable packet. Missing/invalid evidence, unsupported tasks and retrieval failures abstain before model execution. No model tool resolves policies, runs coverage rules, changes state, grants authorization, accesses files/network or settles claims.

Fixed SDK instructions are separate from user notes and untrusted JSON tool results. Tests inject commands into actual reauthored in-memory evidence/policy sources and run the real SDK. The host validates parsed scope, hashes, six findings, exact explanations/citations/evidence IDs and required reviewer; unsupported text or reviewer downgrades abstain. This is conformance/security-boundary evidence with a deterministic client, not proof that an untested live model resists injection.

Limits: two simulated client calls, one actual read-only tool body, SDK bounded sequential invocation, independent host counters, a configurable cooperative deadline and packet/output byte budgets. Fresh unmodified client configuration is mandatory; hidden tools, middleware or relaxed limits cannot expand grants. Every returned object requires human review, final outcome null and settlement authority false. Adverse/high-risk/ambiguous cases preserve supervisor handling. No operational `Assessment` or case transition is generated.

## Verification

The resumed isolated Python 3.12.8 environment uses Pydantic 2.14.2, pytest 8.4.2, Ruff 0.16.10, mypy 1.20.2 and setuptools 82.0.1. The exact runtime closure is recorded in the constraints file. `pip check` reports no broken requirements. Editable metadata installs; source CLI checks explicitly use `PYTHONPATH=src` and wheel checks must independently load the installed package.

| Check | Actual result |
| --- | --- |
| Complete source pytest suite | **422 passed**, including all 385 baseline tests plus 37 new parametrized agent tests |
| Ruff formatting/lint | Passed; 59 Python files formatted, no lint findings |
| Strict mypy | Passed; 59 source/test files, no issues |
| Runtime dependencies | `pip check`: no broken requirements; SDK/core and msgspec versions verified from installed metadata |
| Dataset check and reproduction | 12 scenarios validated; existing byte-for-byte corpus reproduction test passes |
| Packaging | Wheel and source distribution built offline using installed setuptools; six agent modules match source bytes, wheel declares exact agents extras, source archive includes constraints/tests/docs |
| Installed wheel | Project wheel installed without dependencies/downloads into a temporary target; `python -I` verified package paths and ran **422 passing tests** with pytest's source-path setting overridden to that target |
| Independent wheel CLI | Run from a temporary directory with explicit specification path and isolated wheel imports; byte-identical to both source CLI reports |
| Documentation | 31 Markdown files, 451 local links and 124 named test references checked; anchors, tables, fences, whitespace and `git diff --check` pass |
| Preservation | All 161 tracked data files match Git blobs; no prior source/test file changed; original M4–M9 results retained |

Installed-wheel suite tests run from the repository root because historical tests read relative fixture paths; CLI subtests explicitly select source as before. The independently isolated wheel CLI separately verifies packaged entry-point execution without source imports. The first relocated suite attempt failed on working-directory assumptions and produced one extra provisional report in the corpus; that test-created untracked file was removed, corpus integrity rechecked and the full wheel suite rerun successfully. No curated fixture was overwritten or relabeled. The pre-existing M9 CLI's broad `data/` output protection is working-directory-relative; run documented commands from the repository root. Generalizing that older guard is outside M10 and remains a hardening item.

Two fresh source runs, `outputs/agents/m10-final-a.json` and `m10-final-b.json`, and the isolated wheel CLI produce the same `agent-foundation-run-v1` JSON. SHA-256: `74aad58a9a47340f3f16a926fcd60ce8d5644511a407db19364f6aaa367a53ca`. These ignored local artifacts can be regenerated with the documented command; the repository evidence is this record, not a claim of live model performance.

| Synthetic demo case | Actual host/framework result | Simulated client calls / actual tool bodies |
| --- | --- | --- |
| Normal | Draft for human review | 2 / 1 |
| Adverse | Supervisor escalation | 2 / 1 |
| Missing evidence | Preflight supervisor abstention | 0 / 0 |
| Injected note | Bounded draft, untrusted note separate from instructions | 2 / 1 |
| Unsupported task | Preflight supervisor abstention | 0 / 0 |
| Forbidden tool | SDK/tool failure, supervisor abstention | 1 / 0 |

There are four real framework runs, seven scripted client responses and three read-only tool executions across the six cases; zero live model calls and zero autonomous outcomes. SDK construction, dispatch and Pydantic parsing are real. No model-performance, real token billing, live provider or operational identity result is claimed.

New M5–M9 regression reports in `outputs/*/m10-environment-regression.json` preserve semantic contents. Compared with original reports, only `pydantic_version` changes (2.11.7 → 2.14.2), plus M5's correctly rederived `run_id`, which hashes runtime metadata. This is explicitly not historical byte identity across environments. The original M8 report remains SHA-256 `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`, including failures Q-007/Q-012/Q-015/Q-029.

## Limitations and acceptance

The offline client is scripted and is the only permitted client type. No live Foundry/OpenAI integration, streaming, free-form policy interpretation, evidence reconciliation agent, authenticated case access, distributed telemetry, session reuse, durable workflow or approved policy release is implemented. Async timeouts are cooperative; blocking/cancellation-resistant providers need isolation before integration. Provisional policy text and human assertions remain unapproved and synthetic. Agent necessity/benefit still needs comparison against a deterministic packet formatter and independently adjudicated model evaluation.

M8 failures Q-007/Q-012/Q-015/Q-029 remain unresolved. M4–M9 data and original outputs are preserved; environment metadata differences in new regression reports are disclosed rather than overwritten or hidden.

Acceptance is met for genuine framework construction/execution, supported offline extension, one bounded tool, typed advisory output, deterministic host safety controls and reproducible offline/package evidence. It does not approve an insurer policy, claim outcome or live agent deployment. No Azure/model calls or spending, MCP/APIM, UI/deployment, commits or pushes occurred. **Stop after M10; do not implement M11.**
