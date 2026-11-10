"""Real stdio clients and synthetic host context creation for reproducible local demonstrations."""

import os
import sys
from hashlib import sha256
from pathlib import Path

from agent_framework import MCPStdioTool
from mcp import Client, StdioServerParameters, types

from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agent_tools.contracts import ALLOWLIST, ToolName
from claims_ai.agent_tools.tools import expected_data, scope_for
from claims_ai.agents.__main__ import demo_input
from claims_ai.agents.contracts import AssessmentInput, Limits
from claims_ai.agents.prepare import prepare_packet
from claims_ai.mcp_server.contracts import HostConfiguration, ServerReply


def write_demo_context(directory: Path, root: Path, name: str) -> tuple[Path, AssessmentInput]:
    """Called only by the trusted local demo host, not registered as an MCP tool."""
    value = demo_input(root, "valid-v1")
    config = HostConfiguration(
        fixture_root=root.resolve(),
        fixture_id="valid-v1",
        manifest_sha256=sha256((root / "manifest.json").read_bytes()).hexdigest(),
        grant=demo_grant(value, name),
    )
    path = directory / "host-context.json"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(config.model_dump_json())
    return path, value


def parameters(context_file: Path | None) -> StdioServerParameters:
    # Explicit import root supports both source and independently installed wheels, even with -I.
    package_root = str(Path(__file__).resolve().parents[2])
    bootstrap = (
        "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.mcp_server',run_name='__main__')"
    )
    args = ["-I", "-c", bootstrap, package_root, "serve"]
    if context_file is not None:
        args.extend(["--context-file", str(context_file)])
    return StdioServerParameters(command=sys.executable, args=args)


def arguments(value: AssessmentInput, name: ToolName) -> dict[str, object]:
    scope = scope_for(value, prepare_packet(value, Limits()))
    result: dict[str, object] = {"claim_id": scope.claim_id}
    if name != ToolName.EVIDENCE:
        result.update(
            policy_id=scope.policy_id,
            policy_version=scope.policy_version,
            incident_date=scope.incident_date.isoformat(),
            index_sha256=scope.index_sha256,
        )
    if name == ToolName.RULES:
        result["execution_key"] = scope.rule_execution_key
    return result


def checked(
    result: types.CallToolResult,
    *,
    value: AssessmentInput | None = None,
    tool: ToolName | None = None,
) -> ServerReply:
    """Only host-owned local artifacts can authorize successful returned content.

    Error envelopes carry no data and may be decoded without a snapshot. Successful
    reads require the independently loaded input and the actual requested tool;
    response-supplied context, hashes or representation agreement cannot replace them.
    """
    reply = ServerReply.model_validate(result.structured_content)
    if result.is_error != (reply.status == "error"):
        raise ValueError("protocol and application status disagree")
    if len(result.content) != 1 or not isinstance(result.content[0], types.TextContent):
        raise ValueError("expected one matching JSON text block")
    if ServerReply.model_validate_json(result.content[0].text) != reply:
        raise ValueError("structured/text result mismatch")
    if reply.status == "ok":
        if value is None or tool is None or reply.result is None:
            raise ValueError("successful MCP read requires independent trusted context")
        # Existing M6/M7/M9 replay rebuilds source clauses, ownership, provenance,
        # rule findings and retrieval from the host's artifacts, not the response.
        packet = prepare_packet(value, Limits())
        if (
            reply.result.tool != tool
            or reply.result.packet_sha256 != packet.packet_sha256
            or reply.result.data != expected_data(value, packet, tool)
        ):
            raise ValueError("MCP result does not match the trusted source snapshot")
    return reply


async def native_roundtrip(context_file: Path, value: AssessmentInput) -> dict[str, object]:
    async with Client(parameters(context_file), mode="legacy", read_timeout_seconds=5) as client:
        tools = (await client.list_tools()).tools
        if [tool.name for tool in tools] != list(ALLOWLIST):
            raise ValueError("unexpected server tool set")
        replies = [
            checked(
                await client.call_tool(name.value, arguments(value, name)), value=value, tool=name
            ).model_dump(mode="json")
            for name in ALLOWLIST
        ]
        return {
            "client": "mcp.Client",
            "initialization": "ClientSession.initialize",
            "protocol_version": client.protocol_version,
            "tools": [
                tool.model_dump(mode="json", by_alias=True, exclude_none=True) for tool in tools
            ],
            "replies": replies,
        }


def framework_parser(
    result: types.CallToolResult, *, value: AssessmentInput, tool: ToolName | None
) -> str:
    return checked(result, value=value, tool=tool).model_dump_json()


async def framework_roundtrip(context_file: Path, value: AssessmentInput) -> dict[str, object]:
    params = parameters(context_file)
    requested: ToolName | None = None

    def parse(result: types.CallToolResult) -> str:
        # This demonstration invokes tools sequentially. The host selects the
        # expected tool before each call; returned tool names cannot select it.
        return framework_parser(result, value=value, tool=requested)

    async with MCPStdioTool(
        name="northstar-local-claims",
        command=params.command,
        args=params.args,
        allowed_tools=[name.value for name in ALLOWLIST],
        load_prompts=False,
        request_timeout=5,
        parse_tool_results=parse,
        max_host_payload_size_bytes=131072,
    ) as tool:
        names = [function.name for function in tool.functions]
        if names != list(ALLOWLIST):
            raise ValueError("framework discovery broadened tool scope")
        replies = []
        for name in ALLOWLIST:
            requested = name
            result = await tool.call_tool(name.value, **arguments(value, name))
            if not isinstance(result, str):
                raise ValueError("typed framework parser must return JSON")
            reply = ServerReply.model_validate_json(result)
            if reply.status != "ok":
                raise ValueError("framework read did not succeed")
            replies.append(reply.model_dump(mode="json"))
            requested = None
        return {"client": "agent_framework.MCPStdioTool", "tools": names, "replies": replies}
