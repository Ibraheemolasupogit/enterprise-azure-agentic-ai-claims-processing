# Milestone 11 — Governed agent tools and contract testing

Status: **COMPLETE within the bounded offline internal-tool scope**. This is the user-authorized internal-tool milestone, superseding the roadmap's earlier planned M11 ingestion service. Service ingestion is deferred to M12; authority decisions and the two-agent target design are unchanged. No M12 implementation is included.

## Files and actual functionality

- Added [contracts](../../src/claims_ai/agent_tools/contracts.py), [governed tools/local services](../../src/claims_ai/agent_tools/tools.py), [framework execution profile/offline client](../../src/claims_ai/agent_tools/execution.py), [CLI](../../src/claims_ai/agent_tools/__main__.py) and package initializer.
- Added [contract/security tests](../../tests/test_agent_tools.py), [architecture guide](../architecture/governed-agent-tools.md) and this evidence record. Updated README, target/framework/security architecture status, traceability, roadmap, dependency API notes and Makefile.
- No dependency, domain-contract, M4–M9 implementation/test/data or M10 runtime change. No additional agent, service client, cloud resource or autonomous outcome.

The installed `agent-framework-core==1.23.0` / `msgspec==0.22.0` pins remain unchanged. Real `FunctionTool` uses typed `input_model`, `func`, invocation/exception caps and `invoke(arguments=..., skip_parsing=True)`. Real `Agent.run`, `FunctionInvocationLayer` / `BaseChatClient._inner_get_response`, `Content.from_function_call`, tool-result messages and `AgentResponse.value` execute offline. The supported custom client supplies scripted **SIMULATED** chat responses; it does not replace framework classes or invoke tools itself.

## Contracts and controls

Three read-only tools expose verified evidence, exact-version M7 clauses and pre-existing provisional M9 findings. The [design guide](../architecture/governed-agent-tools.md) defines arguments, minimal result fields, deadlines and trust assumptions. Policy/version/date/index and rule execution key must match trusted host scope; model arguments never select a new case, principal, permission, query or rule parameter.

An immutable `ToolGrant` binds one principal assertion, case fingerprint, correlation ID and read permissions. The governed entry point denies insufficient/cross-case/stale grants before preflight/backend reads. Every tool checks authorization again and compares the service result with canonical verified data. Local services replay existing M6/M9 provenance or M7 retrieval paths; modified evidence/citations/findings are not released. Grants are trusted synthetic assertions, not implemented Entra authentication or signed authorization tokens.

One use of each of three named tools, three independent host attempt slots, four simulated responses, cooperative run/read deadlines and byte budgets bound execution. Unknown/extra tools, malformed arguments, repeats and altered client configuration fail safely. Correlated service errors omit raw payloads/exception text; failure latches stop later reads. Document/policy instructions remain untrusted JSON data and fixed SDK instructions remain separate.

Final drafts reuse M10's schema/provenance validator. Human approval is always required; adverse/high-risk/ambiguous findings preserve supervisor handling. No case state, approved coverage, payment or settlement authority is added.

## Verification

Tested environment: isolated Python **3.12.8**, Agent Framework **1.23.0**, msgspec **0.22.0**, Pydantic **2.14.2**, pytest **8.4.2**, Ruff **0.16.10**, mypy **1.20.2**, setuptools **82.0.1**. Dependency pins remain those recorded in M10; `pip check` reports no broken requirements. No dependency was installed/upgraded for M11; only the project wheel was installed into a temporary verification target.

| Check | Actual result |
| --- | --- |
| Complete source suite | **478 passed** in 22.88 seconds: all 422 baseline tests plus 56 new parametrized contract/security tests; duration is a local check, not a performance benchmark |
| Ruff | All 65 Python files formatted; lint passed |
| Strict mypy | No issues in 65 source/test files |
| Dataset validation | 12 synthetic scenarios validated; existing exact-reproduction test passes |
| Packaging | Offline wheel and source archive builds passed; all five new modules match wheel/source bytes, optional framework metadata retained, source archive includes tests/docs/constraints and all 161 tracked data files |
| Installed wheel | Installed only the project wheel without dependencies/downloads into a temporary target; `python -I` verified wheel import paths, overrode pytest's source path and ran **478 passing tests** in 22.92 seconds |
| Independent installed CLI | Executed from a temporary working directory with explicit specification root and isolated wheel imports; output matches both source runs byte for byte |
| Documentation | 33 Markdown files, 495 local links and 143 named test references checked; anchors, tables, fences, whitespace and `git diff --check` pass |
| Preservation | All 161 tracked reference data files match Git blobs; no prior source/test file modified; original M4–M9 outputs and M10 runtime profile retained |

Historical CLI subtests explicitly select source; the full installed-wheel suite runs from the repository root for existing relative fixtures. The new M11 CLI subtest selects the active package location, so it also uses wheel code during wheel testing. The independent isolated CLI validates the installed entry point without source imports.

Negative checks pass for unauthorized/stale/partial grants before service reads, per-tool missing permissions, cross-case requests, wrong policy/version/date/index/execution key, malformed arguments through both host and real SDK, unknown/repeated/flooded calls, hidden tools/middleware/relaxed client limits, corrupted provenance/citations/findings, retrieval outage, three service-failure positions, deadlines, response limits, source-document/policy instruction injection, unsupported final conclusions and supervisor downgrades. Missing/conflicting/quarantined/unverified evidence blocks execution. No negative test releases a final draft or gains decision authority.

Two fresh source runs, `outputs/agent-tools/m11-verified-a.json` and `m11-verified-b.json`, plus the independent wheel CLI, produce the same `governed-tools-run-v1` report. SHA-256: `388a0c3a03d4c5a730a7ba4432acc832ee470e4e35b1fc4b7a975e6aa9f47f57`. Files under `outputs/` are ignored local evidence; the documented command regenerates them with a new filename.

| Synthetic demonstration | Result | Simulated client responses | Tool replies: success / safe error |
| --- | --- | --- | --- |
| Normal | Human-review draft | 4 | 3 / 0 |
| Adverse | Supervisor escalation | 4 | 3 / 0 |
| Missing evidence | Preflight abstention | 0 | 0 / 0 |
| Unauthorized grant | Preflight access denial | 0 | 0 / 0 |
| Cross-case argument | Access-denied abstention | 2 | 0 / 1 |
| Wrong version | Scope-mismatch abstention | 3 | 1 / 1 |
| Malformed arguments | Sanitized SDK failure/abstention | 2 | 0 / 0 |
| Forbidden tool | Sanitized SDK failure/abstention | 1 | 0 / 0 |
| Injected note | Bounded human-review draft | 4 | 3 / 0 |
| Retrieval outage | Service-unavailable abstention | 3 | 1 / 1 |

Totals: **eight actual framework runs**, 23 simulated client responses, 11 successful read replies and three safe error replies; two errors are rejected before backend access, one represents the simulated policy outage. Malformed/unknown calls are rejected by the SDK before the function body. These are safety-demonstration observations, not retrieval/model quality or latency measurements. All ten cases have zero autonomous outcomes and zero live model calls.

The unchanged M10 CLI was rerun as `outputs/agents/m11-preservation.json` and matches its original report byte for byte (SHA-256 `74aad58a9a47340f3f16a926fcd60ce8d5644511a407db19364f6aaa367a53ca`). Original M8 report SHA-256 remains `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`, with all four failures retained.

## Limitations and acceptance

The offline demonstration proves real SDK mechanics and deterministic host boundaries with a scripted client. It does not establish live model reasoning/injection resistance, calibrated confidence, real token/cost usage, cloud identity/RBAC, persistent audit, production policy approval or production readiness. Grants require a future authenticated caller, expiry/revocation and service integration. Timeouts cannot preempt blocking/cancellation-resistant code. Model conclusions are constrained to exact deterministic findings rather than free-form explanations.

Acceptance is met for actual SDK invocation, three service-backed typed reads, case-bound host authorization, bounded safe failures, human/supervisor controls and reproducible source/package evidence. This acceptance does not authorize deployment or operational claims processing.

M8's four lexical failures Q-007/Q-012/Q-015/Q-029 remain unresolved. Reference artifacts are preserved. No MCP/APIM, UI, Azure/model calls, spending, commits or pushes. **Stop after M11.**
