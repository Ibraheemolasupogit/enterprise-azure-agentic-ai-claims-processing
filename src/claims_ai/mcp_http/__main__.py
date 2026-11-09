"""Reproducible HTTP protocol demonstration; ephemeral synthetic credentials never serialized."""

import argparse
import asyncio
import logging
import platform
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

import httpx2

from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agents.__main__ import demo_input
from claims_ai.dataset.generator import json_bytes
from claims_ai.mcp_http.auth import SyntheticIssuer
from claims_ai.mcp_http.contracts import HttpLimits
from claims_ai.mcp_http.policy_validation import validate_reference
from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip, running


async def offline_report(root: Path, reference: Path, *, mode: str) -> dict[str, object]:
    value = demo_input(root, "valid-v1")
    grant = demo_grant(value, "m14-http")
    issuer = SyntheticIssuer()

    def factory(port: int) -> HttpBoundary:
        return HttpBoundary(
            value,
            grant,
            port=port,
            gateway_subject=issuer.subject,
            verifier=issuer.verifier,
            limits=HttpLimits(),
        )

    if mode == "loopback":
        async with running(factory) as url:
            result = await protocol_roundtrip(url, issuer.issue(), value)
    elif mode == "asgi":
        boundary = factory(8765)
        async with boundary.app.router.lifespan_context(boundary.app):
            result = await protocol_roundtrip(
                "http://127.0.0.1:8765/mcp",
                issuer.issue(),
                value,
                transport=httpx2.ASGITransport(app=boundary.app),
            )
    else:
        raise ValueError("unsupported execution surface")
    source = Path(__file__).parent
    return {
        "report_version": "mcp-http-foundation-v1",
        "transport": "SDK_STREAMABLE_HTTP_STATELESS_JSON",
        "execution_surface": "LOOPBACK_SOCKET" if mode == "loopback" else "IN_PROCESS_ASGI_HTTP",
        "identity_mode": "EPHEMERAL_SYNTHETIC_RS256_NOT_ENTRA",
        "apim_enforcement": "NOT_EXECUTED",
        "mcp_version": version("mcp"),
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "processor_sha256": sha256(
            b"".join(
                p.name.encode() + b"\x00" + p.read_bytes() for p in sorted(source.glob("*.py"))
            )
        ).hexdigest(),
        "reference_validation": validate_reference(reference),
        "live_model_calls": 0,
        "autonomous_outcomes": 0,
        "azure_operations": 0,
        "result": result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Local MCP HTTP; no real identity provider or APIM"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--mode", choices=("asgi", "loopback"), default="asgi")
    demo.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    demo.add_argument("--reference-root", type=Path, default=Path("infra/apim"))
    demo.add_argument("--output", type=Path, required=True)
    validate = commands.add_parser("validate-policy")
    validate.add_argument("--reference-root", type=Path, default=Path("infra/apim"))
    args = parser.parse_args()
    for name in ("mcp", "uvicorn", "httpx2", "agent_framework"):
        logger = logging.getLogger(name)
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False
        logger.setLevel(logging.CRITICAL + 1)
    try:
        if args.command == "validate-policy":
            print(json_bytes(validate_reference(args.reference_root)).decode(), end="")
            return
        root, reference = args.spec_root.resolve(), args.reference_root.resolve()
        protected = [
            root,
            reference,
            Path("data").resolve(),
            *(p for p in root.parents if p.name == "data"),
        ]
        if any(args.output.resolve().is_relative_to(p) for p in protected):
            raise ValueError("output cannot modify reference artifacts")
        report = asyncio.run(offline_report(root, reference, mode=args.mode))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(json_bytes(report))
    except Exception as error:
        parser.exit(
            1,
            f"Local HTTP verification failed ({type(error).__name__}); no raw payload logged.\n",
        )
    print(
        "Real MCP HTTP protocol recorded; synthetic local identity; no live APIM/Entra enforcement."
    )


if __name__ == "__main__":
    main()
