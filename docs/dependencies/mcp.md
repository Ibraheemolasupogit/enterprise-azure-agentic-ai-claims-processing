# MCP SDK compatibility and dependency record

Status: real SDK **installed and exercised locally**, not a protocol stub. Python 3.12.8 remains isolated from system site-packages; existing M10 dependency pins are unchanged.

## Verified sources and APIs

- Official [MCP 2.2.0 release metadata](https://pypi.org/pypi/mcp/2.2.0/json): Python >=3.10, stable v2 API, exact `mcp-types==2.2.0`, Pydantic >=2.12. The existing Pydantic 2.14.2 satisfies it.
- Microsoft's [Agent Framework 1.23.0 package manifest](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/pyproject.toml) and installed metadata declare `mcp>=2.2.0,<3` and `tenacity>=9.1.4,<9.2.0` in the broad optional extra. Only the needed MCP packages are selected; `[all]` and MCP CLI extras are unnecessary.
- The pinned [low-level server source](https://github.com/modelcontextprotocol/python-sdk/blob/v2.2.0/src/mcp/server/lowlevel/server.py), [official client documentation](https://py.sdk.modelcontextprotocol.io/client/) and installed Python signatures/source were checked before implementation. v1 `FastMCP` examples were not substituted for v2 APIs.

Actual exercised APIs: `mcp.server.Server(on_list_tools=..., on_call_tool=...)`, `ServerRequestContext`, `Server.create_initialization_options`, `mcp.server.stdio.stdio_server`, `Server.run`, real `Tool`/`ListToolsResult`/`CallToolRequestParams`/`CallToolResult` types, `Client`, `StdioServerParameters`, `ClientSession.initialize`, `list_tools`, `call_tool`, plus `agent_framework.MCPStdioTool` context lifecycle, `functions`, `allowed_tools`, `call_tool` and `parse_tool_results`. Native legacy initialization negotiates protocol 2025-11-25; framework connection uses its actual supported automatic path. No live model client or sampling configuration is supplied.

The framework's automatic MCP capability-list recovery actually imports `tenacity`; the first integration attempt exposed that missing optional dependency. Pinning 9.1.4 within its declared range resolved the failure. The server itself does not need a custom SDK, fake client or replacement classes.

## Exact tested additions

[m13-constraints.txt](../../requirements/m13-constraints.txt) retains [M10 pins](../../requirements/m10-constraints.txt) and records all **23 new distributions**. The direct project MCP extra adds `mcp==2.2.0` and `tenacity==9.1.4` alongside the existing framework/msgspec pins. The plain MCP distribution requires HTTP/authentication packages even for stdio; their installation does not mean a listener, JWT authentication, TLS integration or cloud connection is implemented.

| Distribution | Tested version |
| --- | --- |
| mcp / mcp-types | 2.2.0 / 2.2.0 |
| tenacity | 9.1.4 |
| anyio | 4.15.1 |
| httpx2 / httpcore2 | 2.16.0 / 2.16.0 |
| jsonschema / jsonschema-specifications | 4.26.0 / 2025.9.1 |
| attrs / referencing / rpds-py | 26.1.0 / 0.37.0 / 2026.9.1 |
| pyjwt / cryptography | 2.15.1 / 50.0.2 |
| cffi / pycparser | 2.1.1 / 3.12 |
| python-multipart | 0.0.32 |
| sse-starlette / starlette | 3.6.0 / 1.10.0 |
| uvicorn / click | 0.54.0 / 8.5.0 |
| h11 / idna / truststore | 0.16.0 / 3.20 / 0.10.5 |

Pip could not resolve public PyPI from this execution environment. Approved direct `curl` downloads obtained official release JSON and wheel files into a temporary wheelhouse. Every new wheel's SHA-256 was checked against official PyPI metadata **before installation**, then pip resolved/installed offline with M10 constraints. No existing pinned distribution was upgraded. [Wheel provenance manifest](../../requirements/m13-wheel-manifest.json) records the 23 filenames, URLs and hashes; no wheel/vendor SDK is committed. The binary wheel selection is Python 3.12/macOS arm64; another platform needs compatible wheels and separate verification.

`pip check`, strict typing and package/protocol tests are recorded in [M13 evidence](../milestones/milestone-13.md). Strict mypy remains enabled globally; one precise test-only `import-untyped` suppression covers jsonschema's absent type stubs, avoiding an otherwise unnecessary stub dependency. There is no runtime typing exemption for project logic.

MCP tests include a subprocess with site-packages unavailable to verify a fixed, payload-free missing-dependency failure. Network package acquisition was solely SDK setup; server/client demonstrations and tests make no model/Azure calls or network-service requests.
