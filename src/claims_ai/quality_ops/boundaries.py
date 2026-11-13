"""Opt-in ASGI tracing metadata; all original HTTP/authentication guards still execute."""

from uuid import UUID, uuid4

import httpx2
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claims_ai.quality_ops.telemetry import Telemetry, propagation_headers


def propagate_request(request: httpx2.Request) -> None:
    """Explicit local transport hook; forward tracing metadata only, never authority."""
    request.headers.update(propagation_headers())


class ObservedASGI:
    def __init__(self, app: ASGIApp, telemetry: Telemetry, *, boundary: str = "api.request"):
        if boundary not in {"api.request", "mcp.request", "review.action"}:
            raise ValueError("invalid ASGI boundary")
        self.app, self.telemetry, self.boundary = app, telemetry, boundary

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = scope.get("headers", [])
        parent: dict[str, str] = {}
        correlation = uuid4()
        if len(headers) <= 64:
            trace_values = [v for k, v in headers if k == b"traceparent"]
            if len(trace_values) == 1 and len(trace_values[0]) == 55:
                parent["traceparent"] = trace_values[0].decode("ascii", errors="replace")
            correlations = [v for k, v in headers if k == b"x-correlation-id"]
            if len(correlations) == 1 and len(correlations[0]) == 36:
                try:
                    correlation = UUID(correlations[0].decode("ascii"))
                except (ValueError, UnicodeError):
                    pass
        with self.telemetry.boundary(self.boundary, correlation, parent=parent) as status:

            async def observed_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    code = message["status"]
                    status.result = (
                        "denied" if code in {401, 403} else "failed" if code >= 500 else "ok"
                    )
                await send(message)

            await self.app(scope, receive, observed_send)
