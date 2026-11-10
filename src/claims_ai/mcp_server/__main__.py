"""Stdio-only serving and deterministic local demonstration, with safe missing-SDK failure."""

import argparse
import asyncio
import logging
import platform
import tempfile
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Governed local MCP; stdio only")
    commands = parser.add_subparsers(dest="command", required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--context-file", type=Path)
    demo = commands.add_parser("demo")
    demo.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    demo.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        from claims_ai.dataset.generator import json_bytes
        from claims_ai.mcp_server.context import load_context
        from claims_ai.mcp_server.server import GovernedMCP
    except ImportError:
        parser.exit(2, "MCP dependencies unavailable; install the pinned project mcp extra.\n")
    if args.command == "serve":
        # stdout belongs exclusively to MCP; suppress dependency log payload capture on stderr.
        for name in ("mcp", "agent_framework"):
            logger = logging.getLogger(name)
            logger.handlers = [logging.NullHandler()]
            logger.propagate = False
            logger.setLevel(logging.CRITICAL + 1)
        config, value = load_context(args.context_file)
        server = GovernedMCP(
            value, config.grant if config else None, limits=config.limits if config else None
        )
        asyncio.run(server.run_stdio())
        return
    try:
        root = args.spec_root.resolve()
        protected = [root, Path("data").resolve(), *(p for p in root.parents if p.name == "data")]
        if any(args.output.resolve().is_relative_to(path) for path in protected):
            raise ValueError("output cannot modify reference inputs")
        report = asyncio.run(offline_report(root))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(json_bytes(report))
    except Exception as error:
        parser.exit(
            1, f"Local MCP demonstration failed ({type(error).__name__}); raw payload omitted.\n"
        )
    print("Real local MCP stdio and framework client execution recorded; no model/cloud calls.")


async def offline_report(root: Path) -> dict[str, object]:
    from mcp import Client

    from claims_ai.agent_tools.contracts import ToolName
    from claims_ai.mcp_server.client import (
        arguments,
        checked,
        framework_roundtrip,
        native_roundtrip,
        parameters,
        write_demo_context,
    )

    cases = []
    for name in (
        "native",
        "framework",
        "absent-context",
        "cross-case",
        "wrong-version",
        "extra-authorization",
        "repeat-abuse",
    ):
        with tempfile.TemporaryDirectory(prefix="northstar-mcp-") as directory:
            context, value = write_demo_context(Path(directory), root, name)
            if name == "native":
                result = await native_roundtrip(context, value)
            elif name == "framework":
                result = await framework_roundtrip(context, value)
            else:
                async with Client(
                    parameters(None if name == "absent-context" else context),
                    mode="legacy",
                    read_timeout_seconds=5,
                ) as client:
                    request = arguments(value, ToolName.EVIDENCE)
                    tool = ToolName.EVIDENCE
                    if name == "cross-case":
                        request["claim_id"] = "NS-CLM-00000000"
                    elif name == "wrong-version":
                        tool = ToolName.POLICY
                        request = {**arguments(value, tool), "policy_version": "wrong-version"}
                    elif name == "extra-authorization":
                        request["grant"] = {"permissions": ["settle_claim"]}
                    replies = [
                        checked(
                            await client.call_tool(tool.value, request), value=value, tool=tool
                        ).model_dump(mode="json")
                    ]
                    if name == "repeat-abuse":
                        replies.append(
                            checked(
                                await client.call_tool(tool.value, request), value=value, tool=tool
                            ).model_dump(mode="json")
                        )
                    result = {"client": "mcp.Client", "replies": replies}
            cases.append({"scenario": name, **result})
    source = Path(__file__).parent
    return {
        "report_version": "local-mcp-run-v1",
        "transport": "stdio",
        "mcp_version": version("mcp"),
        "framework_version": version("agent-framework-core"),
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "processor_sha256": sha256(
            b"".join(
                p.name.encode() + b"\x00" + p.read_bytes() for p in sorted(source.glob("*.py"))
            )
        ).hexdigest(),
        "rules_manifest_sha256": sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "host_identity_assertions": "SIMULATED",
        "live_model_calls": 0,
        "autonomous_outcomes": 0,
        "contains_untrusted_synthetic_text": True,
        "cases": cases,
    }


if __name__ == "__main__":
    main()
