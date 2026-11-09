# Milestone 14 — MCP HTTP transport and APIM governance foundation

Status: **COMPLETE within the local MCP HTTP and static APIM governance foundation scope**. The supplied real TCP report from outside the Codex sandbox matches the corrected HTTP source and records initialization, discovery and three successful typed reads. Shutdown completion has control-flow support described below; no independent closed-port or shutdown-health probe is claimed. Sandbox bind restrictions still apply inside Codex. No real Entra/APIM enforcement or deployment is claimed; M15 has not started.

## Files and APIs

- New six-module [mcp_http package](../../src/claims_ai/mcp_http/__init__.py): strict limits/identity contracts, synthetic pinned-key verifier, actual SDK HTTP boundary, static reference validation and deterministic CLI.
- New [HTTP tests](../../tests/test_mcp_http.py), [policy tests](../../tests/test_apim_reference.py), [XML policy](../../infra/apim/mcp-policy.xml), [Bicep reference](../../infra/apim/reference.bicep), [dev parameters](../../infra/apim/reference.dev.bicepparam) and [reference instructions](../../infra/apim/README.md).
- New [HTTP architecture](../architecture/mcp-http-and-gateway.md), [APIM design/prerequisites](../deployment/apim-governance-reference.md) and this record. Updated README, target/security architecture, MCP dependency record, traceability, roadmap, Makefile and MANIFEST.in.
- No M1–M13 runtime/test module, dependency pin, M4–M9 artifact or lifecycle rule is changed. No additional agent is introduced.

Actual APIs: MCP **2.2.0** `StreamableHTTPSessionManager.run/handle_request` with `json_response=True`, `stateless=True` and request-body bounds; `TransportSecuritySettings`; `streamable_http_client`; `Client(..., mode="legacy")` initialization, `list_tools`, `call_tool`; Starlette ASGI/lifespan and httpx2 ASGI transport. The supplied `max_sessions=1` is ignored by the SDK in stateless mode: it provides no session or concurrent-request cap. HTTP rate limiting and inherited serialized tool budgets remain separate controls. Protocol **2025-11-25** initializes and returns all three M11/M13 typed reads. SDK implementations are genuine. Uvicorn's implemented socket path has not been successfully executed in this sandbox. Existing framework/stdio coverage remains in the complete suite; no new model client is used.

## Security and authority

Default-deny verifier; pinned synthetic RS256 issuer/audience/subject/application/role/lifetime checks; separate host case grant; exact loopback/Host/Origin scope; no forwarded-header trust; POST JSON only; duplicate-key/batch/RPC/tool rejection; actual-byte request limits; authenticated single-process throttling; cooperative deadlines and sanitized errors. Existing M11 authorization, policy-version/date/provenance validation and M13 invocation limits are reused. Three read-only tools cannot mutate states or decide insurance outcomes. Human approval and supervisor escalation remain mandatory.

Synthetic keys/tokens exist only in memory and are excluded from JSON/logs. There is no real issuer, JWKS lookup, Entra credential, APIM token or managed identity. APIM XML proposes client JWT validation followed by separate backend MI authentication; Bicep requires both explicit gates, existing service prerequisites, HTTPS and zero-payload diagnostics. Static tests/compilation do not prove policy expressions or gateway enforcement.

## Initial verification before acceptance corrections

Environment: isolated Python 3.12.8, MCP 2.2.0, Agent Framework 1.23.0, Pydantic 2.14.2, Starlette 1.10.0, Uvicorn 0.54.0, httpx2 2.16.0, PyJWT 2.15.1, cryptography 50.0.2, pytest 8.4.2, Ruff 0.16.10, mypy 1.20.2. No new Python dependency installation.

| Check | Actual result |
| --- | --- |
| Complete source suite | **629 passed** in 93.93 seconds: 576 baseline + 53 new parametrized cases |
| Ruff / strict mypy | Formatting and lint pass; no typing issues in all 86 source/test Python files |
| SDK HTTP protocol | Real initialization/discovery/three typed reads through HTTP ASGI; negative authorization/provenance/failure tests pass |
| APIM reference | Static invariants plus 10 XML and five Bicep security mutations tested; no APIM policy execution |
| Bicep compiler | Official 0.48.1 (cec7951cf6) compiled template and dev parameters without warnings/errors; no Azure calls |
| Packaging / installed wheel | Wheel and sdist built offline; all 68 Python modules match packaged bytes. Independent `python -I` target imports and complete suite: **629 passed** in 98.28 seconds |
| Reproduction / integrity | Two source HTTP reports and independently executed wheel report are byte-identical; all 161 tracked data files match Git blobs; 12 synthetic scenarios validate; `pip check` passes |
| Documentation | 42 Markdown files, 640 local links, 198 named test references, tables/fences/whitespace and `git diff --check` pass |
| Actual TCP socket | **BLOCKED** by OS sandbox; not counted as passed or skipped into acceptance |

HTTP negative cases cover missing/unsigned/incorrect/expired credentials, wrong gateway identity, absent host context, cross-case and wrong-version arguments, spoofed authorization headers and metadata, Host/Origin/forwarding/public-peer rejection, deterministic rate window/retry, malformed RPC and actual oversized bodies, injected text retained as untrusted, service outages, cooperative timeouts and transport errors. No rejected call receives case data or decision authority.

The initial `outputs/mcp-http/m14-verified-a.json` / `m14-verified-b.json` and independently installed wheel CLI report have SHA-256 `7a45bb661db5c6091b02de0e515b6117e1424859db6003f9f4591c6ffedc8489`. The wheel CLI runs from a separate working directory with explicit reference roots and source imports excluded. The installed-wheel full suite overrides the package path and verifies the wheel module location; new HTTP subprocess tests use the active package location. Historical CLI subtests retain their original source-selecting behavior. New source archive checks include every APIM artifact, documentation and all tracked data bytes. These package/report results describe the pre-correction snapshot; existing artifacts are preserved and no package is rebuilt for the targeted acceptance correction. Changed HTTP source fingerprints mean these historical report bytes are not claimed for corrected source.

Compiled Bicep JSON SHA-256: `98175724aa6ace78040df07fc5d767bb1f9ffbd45894eac50313311e420d0ef4`; compiled dev parameter JSON: `a19ea8daea0ac251333edbf2017f0e88c952d8a67e0ac3353c5fe8485b43b5fa`. Compiled resources are all conditional and include no APIM service creation; both gates default false. These are build artifacts, not deployment evidence.

The M13 native/framework stdio demonstration was rerun to a new preservation report and remains byte-identical, SHA-256 `19529fe8591ca374a06f70faa7637f5043560d34b3607f3c16075e0d48ed0e23`. Original M8 evaluation report SHA-256 remains `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`; all four failures remain unresolved. Earlier artifacts were not overwritten. M12's whole-package source fingerprint changes future workflow keys when modules are added or edited, as already documented; this is not a claim of historical workflow-byte identity.

## Targeted acceptance corrections

The acceptance audit found two validation gaps, now corrected without changing M13 or the APIM XML:

- `protocol_roundtrip` previously accepted well-formed MCP error replies as demonstration results. It now rejects an MCP error flag, requires successful typed data for the requested tool, and retains strict structured/text agreement and payload validation. Missing or malformed results fail through the genuine SDK schema checks or existing typed validation. Any failed expected invocation aborts before the CLI writes a report or prints success.
- The APIM static validator previously checked `Claims.Read` without checking its claim name. It now requires that value under the exact claim name `roles`. Renamed, unrelated, case-changed and empty claim names are rejected. This repairs a selected static invariant; it does not execute JWT validation or an APIM policy.

Fifteen regression cases exercise denied invocation at each of the three expected tools; seven altered real SDK HTTP responses covering error flags, absent/malformed structured results, missing tool results, malformed data, valid data for the wrong tool and mismatched text; the actual expired-server path through the CLI; and four renamed role claims. The expired-server regression confirms exit status 1, sanitized diagnostics, no success message and no output report. SDK task-group exception wrapping is retained and checked explicitly.

Correction validation:

| Check | Actual result |
| --- | --- |
| Focused M14 suite | **68 passed** in 4.88 seconds: 53 existing + 15 regression cases |
| Complete source suite | **644 passed** in 97.21 seconds: all 629 prior cases + 15 regressions |
| Ruff / strict mypy | Formatting/lint pass; no typing issues in all 86 source/test Python files |
| APIM policy command | `validate-policy --reference-root infra/apim` passes with `STATIC_ONLY_NOT_APIM_ENFORCEMENT`; existing XML/Bicep preserved |
| Dependencies | `pip --no-cache-dir check`: no broken requirements; no installation or dependency changes |

The full suite includes unchanged M13 stdio/framework tests and M12 workflow tests. No localhost TCP verification, package rebuild or APIM runtime execution is claimed by this correction validation.

The read-only audit independently reproduced `PermissionError` (errno 1) with a bare loopback socket before any application code ran. That environmental restriction remains inside Codex. The externally supplied TCP report reviewed below closes the protocol-execution gap without changing sandbox permissions.

M12's existing timing-dependent reproducibility limitation also remains: real cooperative stage deadlines can record a retry in one run but not another, producing different history bytes despite the same safe final state. The stage/run budgets, retry accounting and exact-byte reproduction test are unchanged. A passing suite does not establish that this timing sensitivity is fixed; see [M13's recorded incident](milestone-13.md).

## Final loopback and package verification

The existing `outputs/mcp-http/m14-loopback-verification.json`, supplied from a permitted terminal outside the Codex sandbox, was inspected without rewriting it. SHA-256: `5f373df8044bda5b42031914c3287955e8d0e186d3e1055d2a3ef6ebfc9d6bfb`. Its HTTP processor fingerprint is `7a36b86bd2f981bebd63d69a85c26dd19a727b9a00a358d7764518c6e1954f1a`, matching all six current corrected HTTP modules; its policy/Bicep hashes match current references.

- `execution_surface=LOOPBACK_SOCKET`, transport `SDK_STREAMABLE_HTTP_STATELESS_JSON`, MCP 2.2.0 and negotiated protocol `2025-11-25` identify actual TCP protocol execution rather than ASGI-only evidence.
- Discovery lists exactly the three governed tools. All three replies validate as `ServerReply`, have successful matching tool identities and typed `EvidenceData`/`PolicyData`/`RuleData`, and retain one matching correlation identifier, untrusted/provisional labels, required human approval, no final outcome and no settlement authority.
- `identity_mode=EPHEMERAL_SYNTHETIC_RS256_NOT_ENTRA`; `apim_enforcement=NOT_EXECUTED`; model calls, autonomous outcomes and Azure operations are all zero. The report contains no private key or bearer credential. This records synthetic local identity, not live Entra validation.

Shutdown evidence is limited and explicit. The report has no dedicated shutdown fields or accompanying post-run port/process observation. In the matching source, `offline_report` constructs its result only after exiting `running`; that context requests exit, awaits the Uvicorn server task with a five-second limit and closes the listener in `finally`. The inspected Uvicorn version normally closes listeners/connections and awaits lifespan shutdown before that task returns. A report produced by this path therefore supports completed awaited teardown without a propagated failure. It does not independently prove absence of lifespan warnings, forced connection cleanup, or a later closed-port probe; no such clean-shutdown verification is asserted.

Editable import diagnosis reproduced `ModuleNotFoundError` from a fresh interpreter outside the repository with `PYTHONPATH` removed, both normally and with `-I`. Both editable `.pth` files contain the correct source path but carry macOS `UF_HIDDEN`; this Python's `site.addpackage` explicitly skips files with that flag. The verified cause is environment-level editable-path discovery, not missing package modules or incorrect setuptools discovery. The repair uses a current non-editable project wheel offline with `--no-deps`; no packaging configuration, dependency or HTTP/security implementation change is required. A fresh-interpreter regression in [test_packaging.py](../../tests/test_packaging.py) covers normal installed imports without pytest's source path or bootstrap injection.

Final verification:

| Check | Actual result |
| --- | --- |
| Focused source tests | **69 passed** in 5.24 seconds: 68 M14 cases plus the installed-import regression |
| Independent installed-wheel full suite | **645 passed** in 100.07 seconds, package origin asserted in a separate package-only installation and pytest source-path injection overridden |
| Ruff / strict mypy | Formatting/lint pass; no typing issues in all 87 source/test Python files |
| Normal imports | Fresh normal and `-I` interpreters from `/tmp`, without `PYTHONPATH`, import the repaired non-editable installation; the regression failed before repair and passes afterward |
| Wheel | Built offline without dependencies at `outputs/packages/m14-final/northstar_claims_ai-0.1.0-py3-none-any.whl`; all 68 Python modules and `py.typed` match source and installed bytes |
| Source archive | Built offline at `outputs/packages/m14-final/northstar_claims_ai-0.1.0.tar.gz`; source, tests, documentation, constraints, APIM references and all 161 tracked data files verified against current file bytes |
| Policy / dependencies | Installed policy command passes with static-only labeling; `pip check` passes and all 35 M13/M10 runtime pins match |

Wheel SHA-256: `1e480b90640d4b5ac8f7a585a622e22cb0e3aefb0cb49d29c443f58a53ae8287`. The final artifacts preserve the earlier packages/reports in their original locations. No package-discovery configuration or runtime code changed during finalisation.

The first full-suite attempt imported the wheel directly from the working environment's shared site-packages and produced **644 passes and one M13 dependency-absence test failure**. That test explicitly inserts the package parent while using `-S`; with a shared parent, it also exposes installed SDK dependencies and defeats its own absence setup. The final independent wheel installation uses a package-only target, restoring that test boundary without editing M13; all 645 tests then pass. Historical CLI subtests that explicitly select source retain that behavior. The new normal-import regression separately verifies the working environment's repaired installation, whose module bytes match the independent wheel.

Reproduction commands (use new output filenames):

```sh
make check
make apim-static-check
make apim-compile BICEP=/path/to/verified/bicep
make package
PYTHONPATH=src .venv/bin/python -m claims_ai.mcp_http demo --mode asgi --output outputs/mcp-http/review-asgi.json
# Run only in a terminal that permits loopback sockets:
PYTHONPATH=src .venv/bin/python -m claims_ai.mcp_http demo --mode loopback --output outputs/mcp-http/m14-loopback.json
```

The ASGI report labels `IN_PROCESS_ASGI_HTTP`, `EPHEMERAL_SYNTHETIC_RS256_NOT_ENTRA` and `NOT_EXECUTED` APIM enforcement. A successful socket run must instead label `LOOPBACK_SOCKET`; never relabel an ASGI result. Outputs are ignored local evidence, not durable audit.

## Remaining risks and acceptance

The real TCP protocol requirement is satisfied by the source-matched supplied report. Acceptance applies to the bounded local foundation with the shutdown-evidence limits above. Production TLS/private networking, real Entra validation/rotation, MI roles, trusted assignment/grant issuance/revocation, distributed budgets/audit and APIM C# runtime tests remain future work. Local plaintext HTTP is limited to loopback; same-user code/host compromise and cooperative cancellation are residual limits. No production hosting configuration is provided.

[Deployment prerequisites](../deployment/apim-governance-reference.md) distinguish documented tier/network features from proposed regions, unqueried capacity/quotas and unpriced cost assumptions. No numeric cloud estimate, availability guarantee or residency/compliance assertion is invented. M8 Q-007/Q-012/Q-015/Q-029 remain unresolved; no original artifacts are rewritten. No Azure login/resources/spending, live model calls, autonomous decisions, commits or pushes. **Stop after M14 for review.**
