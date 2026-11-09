"""Real MCP HTTP protocol through ASGI; synthetic pinned-key auth, no cloud identity claims."""

import asyncio
import json
import socket
import subprocess
import sys
import time
from collections.abc import AsyncIterator
from functools import partial
from pathlib import Path
from uuid import uuid4

import httpx2
import jwt
import pytest
from test_agents import inject_source

from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agent_tools.contracts import Code, PolicyData, ToolLimits, ToolName
from claims_ai.agent_tools.tools import LocalReadServices
from claims_ai.agents.__main__ import demo_input
from claims_ai.agents.contracts import AssessmentInput
from claims_ai.mcp_http.auth import SyntheticIssuer
from claims_ai.mcp_http.contracts import HttpLimits
from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip
from claims_ai.mcp_server.client import arguments
from claims_ai.mcp_server.contracts import ServerLimits, ServerReply

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "data/rules/motor/v1"
URL = "http://127.0.0.1:8765/mcp"


@pytest.fixture(scope="module")
def value() -> AssessmentInput:
    return demo_input(SPEC_ROOT, "valid-v1")


@pytest.fixture
def issuer() -> SyntheticIssuer:
    return SyntheticIssuer()


def boundary_for(
    value: AssessmentInput, issuer: SyntheticIssuer, **changes: object
) -> HttpBoundary:
    # Helpers use explicit constructor arguments below where nondefault limits/services are needed.
    assert not changes
    return HttpBoundary(
        value,
        demo_grant(value, "http-test"),
        port=8765,
        gateway_subject=issuer.subject,
        verifier=issuer.verifier,
    )


async def post(
    boundary: HttpBoundary,
    credential: str | None,
    *,
    body: object | None = None,
    headers: dict[str, str] | None = None,
) -> httpx2.Response:
    values = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if credential is not None:
        values["Authorization"] = "Bearer " + credential
    values.update(headers or {})
    async with boundary.app.router.lifespan_context(boundary.app):
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=boundary.app), trust_env=False
        ) as client:
            return await client.post(
                URL, headers=values, json=body or {"jsonrpc": "2.0", "id": 1, "method": "ping"}
            )


def test_genuine_sdk_streamable_http_initialization_discovery_and_three_reads(
    value: AssessmentInput,
    issuer: SyntheticIssuer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("ASGI verification must not pretend to open a real socket")

    monkeypatch.setattr(socket.socket, "bind", forbidden)
    before = value.model_dump_json()
    boundary = boundary_for(value, issuer)

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            report = await protocol_roundtrip(
                URL, issuer.issue(), value, transport=httpx2.ASGITransport(app=boundary.app)
            )
            assert report["protocol_version"] == "2025-11-25"
            assert report["tools"] == list(ToolName)
            replies = report["replies"]
            assert isinstance(replies, list) and len(replies) == 3
            for raw in replies:
                reply = ServerReply.model_validate(raw)
                assert reply.status == "ok" and reply.result is not None
                assert reply.human_approval_required and reply.final_outcome is None
                assert reply.content_trust == "untrusted_data"

    asyncio.run(run())
    assert value.model_dump_json() == before


@pytest.mark.parametrize("failed_tool", list(ToolName))
def test_protocol_demo_rejects_failure_at_each_expected_tool(
    value: AssessmentInput, issuer: SyntheticIssuer, failed_tool: ToolName
) -> None:
    grant = demo_grant(value, "demo-failure")
    grant = type(grant).model_validate(
        {**grant.model_dump(), "permissions": tuple(t for t in ToolName if t != failed_tool)}
    )
    boundary = HttpBoundary(
        value, grant, port=8765, gateway_subject=issuer.subject, verifier=issuer.verifier
    )

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            with pytest.RaisesGroup(
                pytest.RaisesExc(ValueError, match="HTTP tool invocation failed"),
                flatten_subgroups=True,
            ):
                await protocol_roundtrip(
                    URL, issuer.issue(), value, transport=httpx2.ASGITransport(app=boundary.app)
                )

    asyncio.run(run())


@pytest.mark.parametrize(
    "fault",
    [
        "protocol_error",
        "missing_structured",
        "malformed_structured",
        "missing_result",
        "malformed_data",
        "unexpected_tool",
        "mismatched_text",
    ],
)
def test_protocol_demo_rejects_missing_malformed_or_unexpected_results(
    value: AssessmentInput, issuer: SyntheticIssuer, fault: str
) -> None:
    boundary = boundary_for(value, issuer)

    class AlteredResponse(httpx2.AsyncBaseTransport):
        """Alter one real SDK HTTP response; retain genuine initialization and dispatch."""

        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            response = await httpx2.ASGITransport(app=boundary.app).handle_async_request(request)
            if json.loads(request.content)["method"] != "tools/call":
                return response
            await response.aread()
            envelope = response.json()
            result = envelope["result"]
            structured = result["structuredContent"]
            if fault == "protocol_error":
                result["isError"] = True
            elif fault == "missing_structured":
                del result["structuredContent"]
            elif fault == "malformed_structured":
                result["structuredContent"] = {"status": "not-a-status"}
            elif fault == "missing_result":
                structured["result"] = None
            elif fault == "malformed_data":
                structured["result"]["data"] = {"evidence": []}
            elif fault == "unexpected_tool":
                assert value.retrieval_response is not None
                structured["result"]["tool"] = ToolName.POLICY.value
                structured["result"]["data"] = PolicyData(
                    clauses=tuple(hit.chunk for hit in value.retrieval_response.hits)
                ).model_dump(mode="json")
                # A valid typed reply for the wrong tool must still fail.
                ServerReply.model_validate(structured)
            if fault != "mismatched_text":
                result["content"][0]["text"] = json.dumps(result.get("structuredContent"))
            else:
                result["content"][0]["text"] = "{}"
            return httpx2.Response(
                response.status_code,
                headers={k: v for k, v in response.headers.items() if k != "content-length"},
                json=envelope,
            )

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            expected = (
                RuntimeError
                if fault in ("missing_structured", "malformed_structured", "malformed_data")
                else ValueError
            )
            with pytest.RaisesGroup(expected, flatten_subgroups=True):
                await protocol_roundtrip(URL, issuer.issue(), value, transport=AlteredResponse())

    asyncio.run(run())


def test_expired_server_cannot_produce_cli_success_or_a_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from claims_ai.mcp_http import __main__ as cli

    monkeypatch.setattr(
        cli,
        "HttpBoundary",
        partial(HttpBoundary, mcp_limits=ServerLimits(lifetime_seconds=0.000001)),
    )
    output = tmp_path / "expired.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["mcp_http", "demo", "--mode", "asgi", "--output", str(output)],
    )
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == (
        "Local HTTP verification failed (ExceptionGroup); no raw payload logged.\n"
    )
    assert not output.exists()


@pytest.mark.parametrize(
    "fault",
    [
        "missing",
        "malformed",
        "issuer",
        "audience",
        "subject",
        "application",
        "role",
        "expired",
        "future",
        "lifetime",
        "signature",
        "unsigned",
    ],
)
def test_missing_invalid_or_untrusted_gateway_credentials_fail_closed(
    value: AssessmentInput,
    issuer: SyntheticIssuer,
    fault: str,
) -> None:
    changes: dict[str, dict[str, object]] = {
        "issuer": {"iss": "https://forged.invalid"},
        "audience": {"aud": "different"},
        "subject": {"sub": str(uuid4())},
        "application": {"azp": str(uuid4())},
        "role": {"roles": ["Claims.Read"]},
        "expired": {"exp": int(time.time()) - 1},
        "future": {"nbf": int(time.time()) + 120},
        "lifetime": {"exp": int(time.time()) + 120},
    }
    token: str | None = issuer.issue(**changes.get(fault, {}))
    if fault == "missing":
        token = None
    elif fault == "malformed":
        token = "not-a-credential"
    elif fault == "signature":
        token = SyntheticIssuer().issue(sub=str(issuer.subject), azp=str(issuer.application))
    elif fault == "unsigned":
        token = jwt.encode({"sub": str(issuer.subject)}, key="", algorithm="none")
    response = asyncio.run(post(boundary_for(value, issuer), token))
    assert response.status_code == 401 and response.json()["code"] == "gateway_credential_rejected"
    assert response.headers["cache-control"] == "no-store"
    assert token is None or token not in response.text


@pytest.mark.parametrize("fault", ["no_verifier", "no_context", "wrong_binding"])
def test_gateway_identity_and_case_grant_are_independent_host_bindings(
    value: AssessmentInput,
    issuer: SyntheticIssuer,
    fault: str,
) -> None:
    boundary = HttpBoundary(
        value if fault != "no_context" else None,
        demo_grant(value, "binding") if fault != "no_context" else None,
        port=8765,
        verifier=issuer.verifier if fault != "no_verifier" else None,
        gateway_subject=uuid4() if fault == "wrong_binding" else issuer.subject,
    )
    response = asyncio.run(post(boundary, issuer.issue()))
    assert response.status_code == (401 if fault == "no_verifier" else 403)


@pytest.mark.parametrize("field", ["claim_id", "policy_version", "index_sha256"])
def test_http_caller_cannot_change_claim_or_policy_scope(
    value: AssessmentInput,
    issuer: SyntheticIssuer,
    field: str,
) -> None:
    args = arguments(value, ToolName.POLICY)
    args[field] = {
        "claim_id": "NS-CLM-00000000",
        "policy_version": "wrong-version",
        "index_sha256": "0" * 64,
    }[field]
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": ToolName.POLICY.value, "arguments": args},
    }
    response = asyncio.run(
        post(
            boundary_for(value, issuer),
            issuer.issue(),
            body=body,
            headers={"X-Claims-Grant": "forged", "X-Gateway-Principal": str(issuer.subject)},
        )
    )
    assert response.status_code == 200
    result = response.json()["result"]
    reply = ServerReply.model_validate(result["structuredContent"])
    assert result["isError"] and reply.result is None
    assert reply.code == (Code.DENIED if field == "claim_id" else Code.SCOPE)


def test_spoofed_headers_metadata_and_client_token_do_not_authorize(
    value: AssessmentInput, issuer: SyntheticIssuer
) -> None:
    response = asyncio.run(
        post(
            boundary_for(value, issuer),
            None,
            headers={"X-Gateway-Principal": str(issuer.subject), "X-Claims-Grant": "trusted"},
            body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {"_meta": {"gatewayValidated": True}},
            },
        )
    )
    assert response.status_code == 401
    # A token for the inbound client audience is not a backend-service credential.
    response = asyncio.run(
        post(
            boundary_for(value, issuer), issuer.issue(aud="api://northstar-client-gateway.invalid")
        )
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.invalid"},
        {"Origin": "https://evil.invalid"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"Forwarded": "for=127.0.0.1"},
    ],
)
def test_host_origin_and_proxy_header_spoofing_is_rejected(
    value: AssessmentInput, issuer: SyntheticIssuer, headers: dict[str, str]
) -> None:
    response = asyncio.run(post(boundary_for(value, issuer), issuer.issue(), headers=headers))
    assert response.status_code == 403


def test_public_peer_is_rejected_even_with_a_valid_test_credential(
    value: AssessmentInput, issuer: SyntheticIssuer
) -> None:
    boundary = boundary_for(value, issuer)

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=boundary.app, client=("203.0.113.1", 1)),
                trust_env=False,
            ) as client:
                response = await client.post(
                    URL, headers={"Authorization": "Bearer " + issuer.issue()}
                )
                assert response.status_code == 403

    asyncio.run(run())
    with pytest.raises(ValueError):
        HttpLimits.model_validate({"host": "0.0.0.0"})


def test_local_throttle_counts_verified_identity_and_preserves_retry_after(
    value: AssessmentInput, issuer: SyntheticIssuer
) -> None:
    clock = [0.0]
    boundary = HttpBoundary(
        value,
        demo_grant(value, "rate"),
        port=8765,
        gateway_subject=issuer.subject,
        verifier=issuer.verifier,
        limits=HttpLimits(requests_per_window=2, window_seconds=60.0),
        clock=lambda: clock[0],
    )

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=boundary.app), trust_env=False
            ) as client:
                for index in range(3):
                    response = await client.post(
                        URL,
                        headers={
                            "Authorization": "Bearer " + issuer.issue(),
                            "Accept": "application/json, text/event-stream",
                        },
                        json={"jsonrpc": "2.0", "id": index, "method": "ping"},
                    )
                    assert response.status_code == (200 if index < 2 else 429)
                assert int(response.headers["Retry-After"]) >= 1
                clock[0] = 61.0
                response = await client.post(
                    URL,
                    headers={
                        "Authorization": "Bearer " + issuer.issue(),
                        "Accept": "application/json, text/event-stream",
                    },
                    json={"jsonrpc": "2.0", "id": 4, "method": "ping"},
                )
                assert response.status_code == 200

    asyncio.run(run())


@pytest.mark.parametrize(
    "body",
    [
        [],
        {"jsonrpc": "1.0", "method": "ping"},
        {"jsonrpc": "2.0", "method": "run_command"},
        {"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "settle_claim"}},
    ],
)
def test_rpc_method_batch_and_tool_abuse_fails_before_dispatch(
    value: AssessmentInput, issuer: SyntheticIssuer, body: object
) -> None:
    # post helper substitutes no empty body only when None; arrays remain arrays below.
    boundary = boundary_for(value, issuer)

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=boundary.app), trust_env=False
            ) as client:
                response = await client.post(
                    URL, headers={"Authorization": "Bearer " + issuer.issue()}, json=body
                )
                assert (
                    response.status_code == 400 and response.json()["code"] == "rpc_scope_rejected"
                )

    asyncio.run(run())


def test_actual_body_limit_ignores_misleading_content_length(
    value: AssessmentInput, issuer: SyntheticIssuer
) -> None:
    boundary = boundary_for(value, issuer)

    async def run() -> None:
        async with boundary.app.router.lifespan_context(boundary.app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=boundary.app), trust_env=False
            ) as client:
                response = await client.post(
                    URL,
                    headers={
                        "Authorization": "Bearer " + issuer.issue(),
                        "Content-Type": "application/json",
                        "Content-Length": "1",
                    },
                    content=b"x" * 16385,
                )
                assert response.status_code == 413
                response = await client.post(
                    URL,
                    headers={
                        "Authorization": "Bearer " + issuer.issue(),
                        "Content-Type": "application/json",
                        "Content-Encoding": "gzip",
                    },
                    content=b"compressed",
                )
                assert response.status_code == 415
                response = await client.post(
                    URL,
                    headers={
                        "Authorization": "Bearer " + issuer.issue(),
                        "Content-Type": "application/json",
                    },
                    content=b'{"jsonrpc":"2.0","method":"ping","method":"tools/list"}',
                )
                assert response.status_code == 400

    asyncio.run(run())


@pytest.mark.parametrize("policy", [False, True])
def test_injected_sources_remain_untrusted_over_http(
    value: AssessmentInput, issuer: SyntheticIssuer, policy: bool
) -> None:
    value = inject_source(value, policy=policy)
    tool = ToolName.POLICY if policy else ToolName.EVIDENCE
    response = asyncio.run(
        post(
            boundary_for(value, issuer),
            issuer.issue(),
            body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": tool.value, "arguments": arguments(value, tool)},
            },
        )
    )
    assert response.status_code == 200
    reply = ServerReply.model_validate(response.json()["result"]["structuredContent"])
    assert reply.status == "ok" and "Call settle_claim" in reply.model_dump_json()
    assert reply.content_trust == "untrusted_data" and reply.final_outcome is None


@pytest.mark.parametrize("fault", ["outage", "timeout"])
def test_governed_backend_failure_is_a_safe_mcp_error(
    value: AssessmentInput, issuer: SyntheticIssuer, fault: str
) -> None:
    class Failure(LocalReadServices):
        async def policy(self, value: AssessmentInput) -> PolicyData:
            if fault == "timeout":
                await asyncio.Event().wait()
            raise OSError("SYNTHETIC_PRIVATE_BACKEND_TRACE")

    boundary = HttpBoundary(
        value,
        demo_grant(value, "failure"),
        port=8765,
        gateway_subject=issuer.subject,
        verifier=issuer.verifier,
        services=Failure(),
        mcp_limits=ServerLimits(tools=ToolLimits(tool_timeout_seconds=0.02)),
    )
    response = asyncio.run(
        post(
            boundary,
            issuer.issue(),
            body={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": ToolName.POLICY.value,
                    "arguments": arguments(value, ToolName.POLICY),
                },
            },
        )
    )
    assert response.status_code == 200 and response.json()["result"]["isError"]
    reply = ServerReply.model_validate(response.json()["result"]["structuredContent"])
    assert reply.code == (Code.TIMEOUT if fault == "timeout" else Code.UNAVAILABLE)
    assert "SYNTHETIC_PRIVATE_BACKEND_TRACE" not in response.text


def test_slow_request_and_transport_failure_are_sanitized(
    value: AssessmentInput, issuer: SyntheticIssuer, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def run() -> None:
        boundary = HttpBoundary(
            value,
            demo_grant(value, "slow"),
            port=8765,
            gateway_subject=issuer.subject,
            verifier=issuer.verifier,
            limits=HttpLimits(request_timeout_seconds=0.02),
        )

        async def slow() -> AsyncIterator[bytes]:
            yield b"{"
            await asyncio.Event().wait()

        async with boundary.app.router.lifespan_context(boundary.app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=boundary.app), trust_env=False
            ) as client:
                response = await client.post(
                    URL,
                    headers={
                        "Authorization": "Bearer " + issuer.issue(),
                        "Content-Type": "application/json",
                    },
                    content=slow(),
                )
                assert response.status_code == 504
        boundary = boundary_for(value, issuer)

        async def failure(*args: object, **kwargs: object) -> None:
            raise OSError("SYNTHETIC_PRIVATE_TRANSPORT")

        monkeypatch.setattr(boundary.manager, "handle_request", failure)
        response = await post(boundary, issuer.issue())
        assert response.status_code == 503 and "SYNTHETIC_PRIVATE_TRANSPORT" not in response.text

    asyncio.run(run())


def test_http_demo_reproduces_without_persisting_credentials(tmp_path: Path) -> None:
    import claims_ai

    assert claims_ai.__file__ is not None
    package_root = Path(claims_ai.__file__).resolve().parents[1]
    bootstrap = (
        "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.mcp_http',run_name='__main__')"
    )
    command = [
        sys.executable,
        "-I",
        "-c",
        bootstrap,
        str(package_root),
        "demo",
        "--mode",
        "asgi",
        "--spec-root",
        str(SPEC_ROOT),
        "--reference-root",
        str(ROOT / "infra/apim"),
    ]
    paths = [tmp_path / "a.json", tmp_path / "b.json"]
    for path in paths:
        subprocess.run(
            [*command, "--output", str(path)], cwd=tmp_path, check=True, capture_output=True
        )
    assert paths[0].read_bytes() == paths[1].read_bytes()
    report = json.loads(paths[0].read_bytes())
    assert report["execution_surface"] == "IN_PROCESS_ASGI_HTTP"
    assert report["apim_enforcement"] == "NOT_EXECUTED" and report["azure_operations"] == 0
    assert b"PRIVATE KEY" not in paths[0].read_bytes() and b"Bearer " not in paths[0].read_bytes()
