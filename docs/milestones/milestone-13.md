# Milestone 13 — Governed MCP server foundation

Status: **COMPLETE within the local stdio MCP foundation scope**. Genuine local MCP server/client execution is present; no APIM, network endpoint, model or cloud deployment exists. M14 is reserved for later APIM scope and has not started.

## Files and functionality

- New [contracts](../../src/claims_ai/mcp_server/contracts.py), [private context loading](../../src/claims_ai/mcp_server/context.py), [server callbacks](../../src/claims_ai/mcp_server/server.py), [real clients](../../src/claims_ai/mcp_server/client.py), [CLI](../../src/claims_ai/mcp_server/__main__.py) and initializer.
- New [protocol/security tests](../../tests/test_mcp_server.py), [architecture guide](../architecture/governed-mcp-server.md), [dependency/API record](../dependencies/mcp.md), [constraints](../../requirements/m13-constraints.txt), [wheel provenance](../../requirements/m13-wheel-manifest.json) and this evidence record. Updated optional dependencies, packaging, Makefile, README, architecture/security, traceability and roadmap.
- Existing M11 services, M12 orchestration, domain contracts and M4–M9 source/data/tests/results are unchanged. No additional agent or copied business rules.

Actual APIs: MCP 2.2.0 low-level `Server` callbacks, SDK `stdio_server`/`Server.run`, typed discovery/call results, `Client(StdioServerParameters, mode="legacy")`, `ClientSession.initialize`, `list_tools` and `call_tool`. Agent Framework 1.23.0 `MCPStdioTool` connects, discovers converted functions and calls all three server capabilities through its supported API. Protocol behavior and Pydantic structured outputs are real; no SDK class is replaced with a mock. There is no LLM in the M13 demonstration.

## Security and authority

Exactly three M11 reads are exposed. Tool arguments use existing strict models and results retain existing source/case/policy/rule validation. Server-side allow-list, one use per named tool, three attempts, failure latch, serialized invocation, parameter limits and cooperative execution/lifetime bounds apply independently of prompt/client claims. No state, approval/denial/payment/settlement method exists.

One host-owned private startup file binds a synthetic fixture manifest and M11 grant to one process/case. Missing/mismatched context denies all reads; metadata, client information and tool arguments cannot grant permission or replace correlation/scope. Context is loaded once. Returned document/policy data remains explicitly untrusted and provisional; human authority cannot be removed.

The trusted local launcher/OS user is the trust root. Same-user host compromise or forged startup files are outside this foundation's protection; no token issuer, signed grant, reviewer authentication or durable audit is claimed. SDK parsing before callbacks is not an adversarial resource sandbox. See the architecture guide for precise limits and M14/cloud prerequisites.

## Verification

Tested environment: isolated Python **3.12.8**, MCP / mcp-types **2.2.0**, Agent Framework **1.23.0**, msgspec **0.22.0**, tenacity **9.1.4**, Pydantic **2.14.2**, pytest **8.4.2**, Ruff **0.16.10**, mypy **1.20.2**, setuptools **82.0.1**. The minimal MCP feature required 23 new distributions, all pinned with official wheel provenance; existing M10 pins were not upgraded. No provider/CLI/umbrella extra was installed.

| Check | Actual result |
| --- | --- |
| Complete source suite | **576 passed** in 90.33 seconds: all 531 baseline tests plus 45 new parametrized MCP tests |
| Ruff / strict mypy | Formatting/lint passed; no typing issues in all 78 source/test Python files |
| Dependencies | `pip check` passed; nested M13/M10 constraints validated with an offline dry-run; all 23 new wheel hashes verified before installation |
| Corpus | 12 scenarios validated; existing exact reproduction test passes; all 161 tracked data files match Git blobs |
| Packaging | Wheel and source distribution built offline; six MCP modules match packaged bytes, exact MCP/tenacity extra metadata retained, constraints/wheel manifest/tests/docs/reference data included |
| Installed wheel | Independent temporary package target, `python -I`, verified wheel module paths and pytest source-path override: **576 passed** in 97.09 seconds |
| Independent wheel execution | Native stdio and framework clients launched the packaged server from another working directory; report matches both source executions byte for byte |
| Documentation | 38 Markdown files, 589 local links and 184 named test references checked; anchors, tables, fences, whitespace and `git diff --check` pass |

Historical CLI subtests still explicitly select source where originally designed; the isolated full suite imports the wheel through an overridden package path. New M13 subprocess tests choose the active package location, so they exercise wheel code during wheel verification. Independent wheel CLI execution separately excludes source imports.

The first full wheel attempt had **575 passing tests and one existing M12 byte-reproduction failure**: an evidence stage exceeded its real cooperative deadline once, recorded a retry, and then reached the same successful human-review state as the no-retry run. No policy/data/outcome differed. A quiet full rerun passed all 576 without changing M12 code, timeouts or expected records. Timing-dependent retry histories are a residual reproducibility limitation; they are not erased or represented as identical. An earlier prototype MCP comparison also detected an intentional source edit made during that run; only its processor fingerprint changed. Final frozen-source comparisons are identical.

Real negative tests cover absent/stale/cross-case host grants before service access, per-tool permissions, six requested scope fields, forged request metadata/client information, malformed/extra arguments, unknown/mutating tools, concurrent repeats, bad provenance, unavailable policy service, cooperative timeouts/expiry, parameter size, injected document/policy instructions, absent/malformed/mismatched startup files, private directory/file permissions, symlink/hardlink/size rejection, missing fixture dependencies and missing SDK/site-packages. All rejected calls return no case data; no tested path gains decision authority. SDK-level in-process tests use real protocol streams; subprocess tests additionally exercise real stdio framing/initialization/teardown.

Two fresh source reports, `outputs/mcp/m13-verified-a.json` and `m13-verified-b.json`, and the independent wheel report produce identical `local-mcp-run-v1` JSON. SHA-256: `19529fe8591ca374a06f70faa7637f5043560d34b3607f3c16075e0d48ed0e23`. These ignored local artifacts are reproducible with a new output filename; they are not durable audit storage.

| Demo case / genuine stdio process | Actual protocol result |
| --- | --- |
| Native MCP SDK | Explicit `ClientSession.initialize`, protocol 2025-11-25, discovery and three successful typed reads |
| Framework MCP client | Real `MCPStdioTool` connection/discovery and three successful typed reads; no chat/model client |
| Absent trusted context | Safe error, no result data |
| Cross-case request | Access denied, no result data |
| Wrong policy version | Scope mismatch, no result data |
| Extra authorization argument | Strict input rejection, no result data |
| Repeated tool | First read succeeds; repeat denied by the server's failure/call boundary |

Totals: seven real subprocess sessions, 12 tool-call requests, seven successful read replies and five safe error replies. Native sessions explicitly initialize; framework uses its supported automatic connection path. There are **zero model calls and zero autonomous outcomes**, not simulated model performance. All host/scan/reviewer/fixture assertions remain synthetic.

No prior runtime or test file changed. The original M10 and M11 reports were rerun to separate preservation outputs and remain byte-identical (SHA-256 respectively `74aad58a9a47340f3f16a926fcd60ce8d5644511a407db19364f6aaa367a53ca` and `388a0c3a03d4c5a730a7ba4432acc832ee470e4e35b1fc4b7a975e6aa9f47f57`). Original M8 report SHA-256 remains `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`; all four failures remain unresolved. Original M12 artifacts remain untouched; new source-bound workflow keys intentionally differ.

## Limitations and acceptance

This is local, trusted-host, synthetic-only stdio. Private files are not authentication tokens. Separate identities, authenticated network authorization, signing/revocation, strict process resource isolation, persistent audit and gateway protection remain planned. Cooperative timeouts cannot preempt blocking code. Scope/budget enforcement applies to decoded tool callbacks; SDK framing/initialization allocations are not bounded by the argument limit.

Acceptance is met for a genuine executable stdio server, reused governed reads, typed safe outputs, case-bound host context, bounded calls, real native/framework communication and reproducible package evidence. This does not approve a network service, production identity boundary or operational claims processing.

No APIM/M14 implementation, live model/Foundry/Azure calls, autonomous insurance outcomes, spending, commits or pushes. M8 failures Q-007/Q-012/Q-015/Q-029 remain unresolved. M12's existing whole-package source fingerprint changes when new M13 modules are added; future keys/checkpoints therefore change as designed, while original artifacts remain untouched. **Stop after M13.**
