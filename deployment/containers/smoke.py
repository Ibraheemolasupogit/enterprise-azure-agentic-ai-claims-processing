"""Real offline ASGI/SDK checks, not a cloud server, TCP test or quality evaluation."""

import argparse
import asyncio
import json
from datetime import UTC, datetime
from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agents.__main__ import demo_input
from claims_ai.api.app import create_app
from claims_ai.mcp_http.auth import SyntheticIssuer
from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.client import ApiClient
from claims_ai.reviewer_ui.sessions import Sessions


async def mcp_check(root: Path) -> int:
    value = demo_input(root, "valid-v1")
    grant = demo_grant(value, "m23-offline-container-smoke")
    issuer = SyntheticIssuer()
    boundary = HttpBoundary(
        value, grant, port=8765, gateway_subject=issuer.subject, verifier=issuer.verifier
    )
    async with boundary.app.router.lifespan_context(boundary.app):
        result = await protocol_roundtrip(
            "http://127.0.0.1:8765/mcp",
            issuer.issue(),
            value,
            transport=httpx2.ASGITransport(app=boundary.app),
        )
        async with httpx2.AsyncClient(transport=httpx2.ASGITransport(app=boundary.app)) as client:
            denied = await client.post("http://127.0.0.1:8765/mcp", json={})
    tools = result["tools"]
    if not isinstance(tools, list) or len(tools) != 3 or denied.status_code != 401:
        raise ValueError("offline MCP smoke failed")
    return len(tools)


def run(root: Path) -> dict[str, object]:
    with TestClient(
        create_app(), base_url="http://127.0.0.1:8766", client=("127.0.0.1", 51000)
    ) as backend:
        live = backend.get("/health/live")
        ready = backend.get("/health/ready")
        denied = backend.get("/api/v1/reviews")
        if live.status_code != 200 or ready.status_code != 503 or denied.status_code != 401:
            raise ValueError("offline API defaults failed")
        sessions = Sessions(clock=lambda: datetime(2027, 2, 1, tzinfo=UTC))
        with TestClient(
            create_ui(ApiClient(backend), sessions),
            base_url="http://127.0.0.1:8767",
            client=("127.0.0.1", 51001),
        ) as browser:
            login = browser.get("/login")
            if login.status_code != 200 or browser.get("/").status_code != 401:
                raise ValueError("offline UI defaults failed")
    return {
        "format": "m23-local-smoke-v1",
        "surface": "IN_PROCESS_ASGI_NOT_TCP_NOT_AZURE",
        "api_live": live.status_code,
        "api_ready": ready.status_code,
        "api_missing_identity": denied.status_code,
        "ui_anonymous_only": True,
        "mcp_tools": asyncio.run(mcp_check(root)),
        "model_calls": 0,
        "cloud_calls": 0,
        "autonomous_outcomes": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-root", type=Path, default=Path("/app/fixtures"))
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.fixture_root), sort_keys=True))
    except Exception:
        raise SystemExit("offline smoke unavailable; details redacted") from None


if __name__ == "__main__":
    main()
