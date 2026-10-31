# Governed local MCP server

Status: **IMPLEMENTED; local verification recorded in [M13 evidence](../milestones/milestone-13.md)**. The real Python MCP SDK and Microsoft Agent Framework client communicate over subprocess stdio. No model, network listener, APIM or Azure component is implemented.

## Protocol and service composition

[GovernedMCP](../../src/claims_ai/mcp_server/server.py) creates one actual MCP 2.2.0 low-level `Server` using supported `on_list_tools` / `on_call_tool` callbacks. `stdio_server()` and `Server.run()` handle framing, initialization and dispatch; no handwritten MCP replacement is supplied. Only these tools are advertised:

| MCP tool | Existing argument model / implementation |
| --- | --- |
| `read_claim_evidence` | M11 `EvidenceArguments`, source-replayed evidence/provenance through `GovernedTools.read` |
| `read_policy_clauses` | M11 `PolicyArguments`, exact claim/policy/version/date/index binding and verified lexical clause data |
| `read_rule_findings` | M11 `RuleArguments`, same exact scope plus execution key and provisional deterministic findings |

M11 owns authorization, normalization, source replay, canonical result comparison and service timeouts. M13 adapts its validated `ToolReply` without copying evidence/retrieval/rule logic. M12 orchestration and its existing internal agent profile are unchanged; this milestone demonstrates transport exposure, not a rewrite of workflow stages or another agent.

Tool input schemas come directly from M11 Pydantic models (`additionalProperties=false`). A new [ServerReply](../../src/claims_ai/mcp_server/contracts.py) supplies a declared output schema, host correlation, success/error code and validated M11 result. Responses use actual MCP `CallToolResult` with matching `structured_content` and JSON text; `is_error` agrees with the application status. Errors contain no data, raw exceptions, caller text or foreign case details. All replies fix untrusted/provisional content status, human approval required, null final outcome and no settlement authority. Read-only/destructive/idempotence annotations are hints; host validation is the enforcement.

## Trusted local context

Each stdio process serves one host-selected synthetic case. It loads context **once at startup**, before processing tool calls, from a private host file. [Context loading](../../src/claims_ai/mcp_server/context.py) requires a private same-owner directory, a regular same-owner file with no group/other permissions, no final symlink or hard link, and a 16 KiB size limit. The file pins a synthetic fixture pack manifest and supplies M11's exact case fingerprint/grant/permissions. Missing, malformed, unavailable or mismatched context becomes a denied server; discovery exposes static schemas only and cannot authorize a read.

The trusted launcher, its Python executable/code and its OS user are the trust root. The file is **not an identity token or proof of authenticated reviewer assignment**. A same-user attacker able to control the launcher or private context can author grants; this foundation does not protect against that attacker. Parent permissions and no-follow checks reduce local file substitution, but are not a filesystem sandbox, signed grant, attestation or general path-security guarantee. Production authentication, issuer validation, expiry/revocation, separate service identities and durable audit remain future requirements.

The MCP JSON-RPC caller cannot supply a principal, grant, context path, correlation override, query, rule parameter or command as a tool argument. Initialization/client information, `_meta`, request state and caller-supplied IDs confer no permission. Requested claim/policy/version/date/index/execution fields must match the host's verified snapshot. Extra authorization arguments are rejected; metadata cannot replace the captured grant. File changes after startup do not update the loaded context.

## Bounds and content safety

The server permits three total handler call attempts, at most once per named tool, and latches failures. Unknown/mutating tools, repeats and malformed calls consume/reject the bounded read opportunity; discovery never resets it. A server-side lock serializes concurrent calls. M11 independently enforces its three-read budget, exact case scope, provenance and per-read cooperative timeout. Its execution timer begins when the first governed tool set is constructed.

Default server limits: 30-second cooperative stdio lifetime, 4 KiB of decoded tool-call parameters (including metadata), M11's three-second execution/one-second read deadlines and 64 KiB tool reply budget. Server lifetime cannot exceed 60 seconds. Limits do **not** bound SDK allocations before JSON-RPC parsing, initialization/discovery traffic, queue wait or blocking Python; process-level resource isolation is still needed before adversarial deployment. Cancellation or EOF closes a local session; there is no persistent case mutation, outcome or retry path here.

Document/policy text is returned only as tagged untrusted JSON data. No such text populates tool descriptions or privileged instructions. Negative tests inject instructions into reauthored in-memory sources and invoke the real SDK; this validates deterministic boundaries, not live-model injection resistance. SDK payload logging is disabled in the server process, stdout is protocol-only, and no telemetry exporter is configured. No resource, prompt, root, model-sampling, file-write, command or financial tool is registered.

## Real clients and reproduction

```sh
.venv/bin/python -m pip install -c requirements/m13-constraints.txt '.[dev,mcp]'
PYTHONPATH=src .venv/bin/python -m claims_ai.mcp_server demo --output outputs/mcp/offline-v1.json
make mcp-check
```

The demo host creates ephemeral mode-0600 configuration files in private temporary directories; nothing is written into reference data. A native `mcp.Client(StdioServerParameters, mode="legacy")` explicitly exercises `ClientSession.initialize`, discovery and calls, negotiating 2025-11-25. The real `agent_framework.MCPStdioTool` uses its supported current connection/discovery path, an explicit tool allow-list, no prompts/model client and a typed result parser. It independently launches the same server and calls all three tools. Neither path invokes an LLM.

The standalone server command is `PYTHONPATH=src .venv/bin/python -m claims_ai.mcp_server serve --context-file /private/host/path/host-context.json`. Only a trusted launcher should construct that file. Starting `serve` without context stays denied; tool calls cannot bootstrap a grant. No `--transport`, URL or port option exists. Use a new demo output filename; reference directories and overwrites are protected even from another working directory.

See [dependency/API evidence](../dependencies/mcp.md) for verified versions, exact APIs, required transitive dependencies and official wheel hashes. M4–M9 data and M8's four failures remain unchanged. M12 intentionally fingerprints all package Python files, so adding M13 changes future workflow keys and makes old checkpoints fail closed; original M12 artifacts are not overwritten or relabeled. No M14/APIM implementation is included.
