"""Genuine SDK Streamable HTTP behind a fail-closed loopback ASGI boundary."""

import asyncio
import json
import math
import socket
import time
from collections import deque
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from uuid import UUID

import httpx2
import uvicorn
from mcp import Client
from mcp.client.streamable_http import streamable_http_client
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.types import Message, Receive, Scope, Send

from claims_ai.agent_tools.contracts import ALLOWLIST, ToolGrant
from claims_ai.agent_tools.tools import ReadServices, authorize
from claims_ai.agents.contracts import AssessmentInput
from claims_ai.mcp_http.auth import DenyAll, GatewayVerifier
from claims_ai.mcp_http.contracts import METHODS, HttpLimits
from claims_ai.mcp_server.contracts import ServerLimits
from claims_ai.mcp_server.server import GovernedMCP


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


class HttpBoundary:
    def __init__(
        self,
        value: AssessmentInput | None = None,
        grant: ToolGrant | None = None,
        *,
        port: int,
        gateway_subject: UUID | None = None,
        verifier: GatewayVerifier | None = None,
        limits: HttpLimits | None = None,
        services: ReadServices | None = None,
        mcp_limits: ServerLimits | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limits = HttpLimits.model_validate(limits or HttpLimits())
        if not 1 <= port <= 65535:
            raise ValueError("a concrete loopback port is required")
        self.authority = f"127.0.0.1:{port}"
        self.port = port
        self.verifier, self.gateway_subject = verifier or DenyAll(), gateway_subject
        self.context_valid = value is not None and grant is not None and authorize(value, grant)
        governed = GovernedMCP(value, grant, limits=mcp_limits, services=services)
        self.manager = StreamableHTTPSessionManager(
            governed.server,
            json_response=True,
            stateless=True,
            max_request_body_size=self.limits.max_request_bytes,
            max_sessions=1,
            security_settings=TransportSecuritySettings(
                enable_dns_rebinding_protection=True,
                allowed_hosts=[self.authority],
                allowed_origins=[f"http://{self.authority}"],
            ),
        )
        self._clock = clock
        self._window: deque[float] = deque()
        self._lock = asyncio.Lock()

        @asynccontextmanager
        async def lifespan(app: Starlette) -> AsyncIterator[None]:
            async with self.manager.run():
                yield

        self.app = Starlette(routes=[Route("/mcp", endpoint=self)], lifespan=lifespan, debug=False)

    async def reject(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        status: int,
        code: str,
        *,
        retry: int | None = None,
    ) -> None:
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        if status == 401:
            headers["WWW-Authenticate"] = 'Bearer realm="synthetic-loopback-backend"'
        if retry is not None:
            headers["Retry-After"] = str(retry)
        await JSONResponse({"status": "error", "code": code}, status_code=status, headers=headers)(
            scope, receive, send
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return
        headers = scope["headers"]
        values = {key: value for key, value in headers}
        hosts = [value for key, value in headers if key == b"host"]
        client, server = scope.get("client"), scope.get("server")
        if (
            not client
            or client[0] != "127.0.0.1"
            or not server
            or server != ("127.0.0.1", self.port)
            or hosts != [self.authority.encode()]
            or scope.get("query_string")
            or values.get(b"origin", f"http://{self.authority}".encode())
            != f"http://{self.authority}".encode()
            or any(key.startswith(b"x-forwarded-") or key == b"forwarded" for key, _ in headers)
        ):
            await self.reject(scope, receive, send, 403, "loopback_or_origin_rejected")
            return
        credentials = [value for key, value in headers if key == b"authorization"]
        credential = credentials[0] if len(credentials) == 1 else b""
        identity = None
        if credential.startswith(b"Bearer ") and len(credential) <= 8192:
            try:
                identity = self.verifier.verify(credential[7:].decode("ascii"))
            except Exception:
                identity = None
        if identity is None:
            await self.reject(scope, receive, send, 401, "gateway_credential_rejected")
            return
        if identity.subject != self.gateway_subject or not self.context_valid:
            await self.reject(scope, receive, send, 403, "trusted_binding_rejected")
            return
        if scope["method"] != "POST":
            await self.reject(scope, receive, send, 405, "post_only_stateless_profile")
            return
        if (
            values.get(b"content-type", b"").split(b";", 1)[0].lower() != b"application/json"
            or b"content-encoding" in values
        ):
            await self.reject(scope, receive, send, 415, "json_uncompressed_required")
            return
        async with self._lock:
            now = self._clock()
            while self._window and self._window[0] <= now - self.limits.window_seconds:
                self._window.popleft()
            if len(self._window) >= self.limits.requests_per_window:
                retry = max(1, math.ceil(self._window[0] + self.limits.window_seconds - now))
                await self.reject(scope, receive, send, 429, "local_rate_limit", retry=retry)
                return
            self._window.append(now)
        response_started = False
        try:
            async with asyncio.timeout(self.limits.request_timeout_seconds):
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] != "http.request":
                        raise ValueError("client disconnected")
                    body.extend(message.get("body", b""))
                    if len(body) > self.limits.max_request_bytes:
                        await self.reject(scope, receive, send, 413, "request_too_large")
                        return
                    if not message.get("more_body", False):
                        break
                try:
                    envelope = json.loads(body, object_pairs_hook=unique_object)
                    if not isinstance(envelope, dict) or envelope.get("jsonrpc") != "2.0":
                        raise ValueError("object JSON-RPC required")
                    method = envelope.get("method")
                    if method not in METHODS:
                        raise ValueError("method not allowed")
                    if method == "tools/call":
                        params = envelope.get("params")
                        if not isinstance(params, dict) or params.get("name") not in ALLOWLIST:
                            raise ValueError("tool not allowed")
                except (ValueError, TypeError):
                    await self.reject(scope, receive, send, 400, "rpc_scope_rejected")
                    return

                consumed = False

                async def replay() -> Message:
                    nonlocal consumed
                    if not consumed:
                        consumed = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                async def safe_send(message: Message) -> None:
                    nonlocal response_started
                    if message["type"] == "http.response.start":
                        response_started = True
                        message = {
                            **message,
                            "headers": [
                                *message.get("headers", []),
                                (b"cache-control", b"no-store"),
                                (b"x-content-type-options", b"nosniff"),
                            ],
                        }
                    await send(message)

                await self.manager.handle_request(scope, replay, safe_send)
        except TimeoutError:
            if not response_started:
                await self.reject(scope, receive, send, 504, "cooperative_request_timeout")
        except Exception:
            if not response_started:
                await self.reject(scope, receive, send, 503, "backend_unavailable")


@asynccontextmanager
async def running(boundary_factory: Callable[[int], HttpBoundary]) -> AsyncIterator[str]:
    """Actual loopback socket; no external bind address or proxy-header trust option."""
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    listener.listen(64)
    listener.setblocking(False)
    port = listener.getsockname()[1]
    boundary = boundary_factory(port)
    config = uvicorn.Config(
        boundary.app,
        host="127.0.0.1",
        port=port,
        lifespan="on",
        proxy_headers=False,
        forwarded_allow_ips="",
        access_log=False,
        log_config=None,
        log_level="critical",
        server_header=False,
        date_header=False,
    )
    server = uvicorn.Server(config)
    task = asyncio.create_task(server.serve(sockets=[listener]))
    try:
        async with asyncio.timeout(5):
            while not server.started:
                if task.done():
                    await task
                    raise RuntimeError("loopback server did not start")
                await asyncio.sleep(0.01)
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        server.should_exit = True
        try:
            await asyncio.wait_for(task, timeout=5)
        finally:
            listener.close()


async def protocol_roundtrip(
    url: str,
    credential: str,
    value: AssessmentInput,
    *,
    transport: httpx2.AsyncBaseTransport | None = None,
) -> dict[str, object]:
    from claims_ai.mcp_server.client import arguments, checked

    async with httpx2.AsyncClient(
        headers={"Authorization": "Bearer " + credential},
        trust_env=False,
        timeout=5,
        transport=transport,
    ) as http:
        stream = streamable_http_client(url, http_client=http, terminate_on_close=False)
        async with Client(stream, mode="legacy", read_timeout_seconds=5) as client:
            tools = (await client.list_tools()).tools
            if [tool.name for tool in tools] != list(ALLOWLIST):
                raise ValueError("unexpected HTTP tool set")
            replies = []
            for name in ALLOWLIST:
                result = await client.call_tool(name.value, arguments(value, name))
                if result.is_error:
                    raise ValueError("HTTP tool invocation failed")
                reply = checked(result, value=value, tool=name)
                if reply.status != "ok" or reply.result is None or reply.result.tool != name:
                    raise ValueError("unexpected HTTP tool result")
                replies.append(reply.model_dump(mode="json"))
            return {
                "protocol_version": client.protocol_version,
                "tools": [t.name for t in tools],
                "replies": replies,
            }
