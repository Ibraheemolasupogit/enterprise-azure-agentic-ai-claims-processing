"""Actual-byte ASGI guards before FastAPI parsing; no proxy trust or payload logging."""

import asyncio
import json
import logging
import threading
from typing import NoReturn
from uuid import UUID, uuid4

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claims_ai.api.auth import Authenticator
from claims_ai.api.contracts import ApiCode, ApiError, ApiLimits, ErrorResponse
from claims_ai.human_review.contracts import PrincipalKind
from claims_ai.logging import LogEvent, correlation_scope, log_event

PUBLIC_PATHS = frozenset({"/health/live", "/health/ready", "/openapi.json"})


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON member")
        result[key] = value
    return result


def invalid_constant(value: str) -> NoReturn:
    raise ValueError("non-finite JSON number")


def error_response(status: int, code: ApiCode, correlation_id: UUID) -> JSONResponse:
    headers = {
        "Cache-Control": "no-store",
        "X-Content-Type-Options": "nosniff",
        "X-Correlation-ID": str(correlation_id),
    }
    if status == 401:
        headers["WWW-Authenticate"] = 'Bearer realm="synthetic-host-not-entra"'
    if status == 429:
        headers["Retry-After"] = "1"
    return JSONResponse(
        ErrorResponse(code=code, request_correlation_id=correlation_id).model_dump(mode="json"),
        status_code=status,
        headers=headers,
    )


class ApiBoundary:
    def __init__(
        self,
        app: ASGIApp,
        *,
        authenticator: Authenticator,
        limits: ApiLimits,
        logger: logging.Logger,
    ) -> None:
        self.app, self.authenticator, self.limits, self.logger = app, authenticator, limits, logger
        self._active = 0
        self._lock = threading.Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        correlation_id = uuid4()
        admitted = False
        response_sent = False
        status = 500
        try:
            headers = scope["headers"]
            values = dict(headers)
            protected_headers = {
                b"host",
                b"authorization",
                b"origin",
                b"content-type",
                b"content-length",
                b"idempotency-key",
                b"if-match",
                b"if-none-match",
                b"x-correlation-id",
            }
            if len(headers) > 64 or sum(len(k) + len(v) for k, v in headers) > 16384:
                raise ApiError(400, ApiCode.BODY)
            if any(sum(k == key for k, _ in headers) > 1 for key in protected_headers):
                raise ApiError(400, ApiCode.BODY)
            if b"x-correlation-id" in values:
                try:
                    correlation_id = UUID(values[b"x-correlation-id"].decode("ascii"))
                except (UnicodeError, ValueError):
                    raise ApiError(400, ApiCode.INVALID) from None
            scope.setdefault("state", {})["request_correlation_id"] = correlation_id
            if scope.get("query_string") and scope["path"] != "/api/v1/reviews":
                raise ApiError(400, ApiCode.INVALID)
            authority = f"127.0.0.1:{self.limits.port}"
            client = scope.get("client")
            server = scope.get("server")
            if (
                not client
                or client[0] != "127.0.0.1"
                or not server
                or tuple(server) != ("127.0.0.1", self.limits.port)
                or scope.get("scheme") != "http"
                or values.get(b"host") != authority.encode()
                or values.get(b"origin", ("http://" + authority).encode())
                != ("http://" + authority).encode()
                or any(
                    k == b"forwarded"
                    or k.startswith(b"x-forwarded-")
                    or k
                    in {
                        b"x-role",
                        b"x-principal-id",
                        b"x-reviewer-id",
                        b"x-claims-grant",
                        b"x-gateway-principal",
                        b"x-claim-id",
                        b"x-policy-version",
                    }
                    for k, _ in headers
                )
            ):
                raise ApiError(403, ApiCode.ORIGIN)
            if scope["path"] not in PUBLIC_PATHS:
                authorization = values.get(b"authorization", b"")
                identity = None
                if authorization.startswith(b"Bearer ") and len(authorization) <= 256:
                    try:
                        with correlation_scope(correlation_id):
                            identity = self.authenticator.verify(authorization[7:].decode("ascii"))
                    except Exception:
                        identity = None
                if identity is None:
                    raise ApiError(401, ApiCode.AUTH)
                if identity.scope.principal.kind not in {PrincipalKind.HUMAN, PrincipalKind.HOST}:
                    raise ApiError(403, ApiCode.DENIED)
                scope["state"]["api_access"] = identity
            with self._lock:
                if self._active >= self.limits.max_inflight:
                    raise ApiError(429, ApiCode.BUSY)
                self._active += 1
                admitted = True
            if b"content-encoding" in values:
                raise ApiError(415, ApiCode.MEDIA)
            if (
                scope["method"] == "POST"
                and values.get(b"content-type", b"").split(b";", 1)[0].lower()
                != b"application/json"
            ):
                raise ApiError(415, ApiCode.MEDIA)
            body = bytearray()
            try:
                async with asyncio.timeout(self.limits.body_timeout_seconds):
                    while True:
                        message = await receive()
                        if message["type"] != "http.request":
                            raise ApiError(400, ApiCode.BODY)
                        body.extend(message.get("body", b""))
                        if len(body) > self.limits.max_request_bytes:
                            raise ApiError(413, ApiCode.SIZE)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                raise ApiError(408, ApiCode.BODY) from None
            if scope["method"] == "GET" and body:
                raise ApiError(400, ApiCode.BODY)
            if scope["method"] == "POST":
                try:
                    parsed = json.loads(
                        body, object_pairs_hook=unique_object, parse_constant=invalid_constant
                    )
                    if not isinstance(parsed, dict):
                        raise ValueError("JSON object required")
                except (ValueError, RecursionError):
                    raise ApiError(400, ApiCode.BODY) from None
            consumed = False
            response_start: Message | None = None
            response_body = bytearray()
            overflow = False

            async def replay() -> Message:
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()

            async def capture(message: Message) -> None:
                nonlocal response_start, overflow
                if message["type"] == "http.response.start":
                    response_start = message
                elif message["type"] == "http.response.body":
                    chunk = message.get("body", b"")
                    if len(response_body) + len(chunk) > self.limits.max_response_bytes:
                        overflow = True
                        response_body.clear()
                    elif not overflow:
                        response_body.extend(chunk)

            with correlation_scope(correlation_id):
                await self.app(scope, replay, capture)
            if overflow:
                raise ApiError(503, ApiCode.RESPONSE)
            if response_start is None:
                raise ApiError(500, ApiCode.INTERNAL)
            status = response_start["status"]
            response_start["headers"] = [
                (k, v)
                for k, v in response_start.get("headers", [])
                if k not in {b"cache-control", b"x-content-type-options", b"x-correlation-id"}
            ] + [
                (b"cache-control", b"no-store"),
                (b"x-content-type-options", b"nosniff"),
                (b"x-correlation-id", str(correlation_id).encode()),
            ]
            response_sent = True
            await send(response_start)
            await send(
                {"type": "http.response.body", "body": bytes(response_body), "more_body": False}
            )
        except ApiError as error:
            status = error.status
            if not response_sent:
                await error_response(status, error.code, correlation_id)(scope, receive, send)
        except Exception:
            status = 500
            if not response_sent:
                await error_response(status, ApiCode.INTERNAL, correlation_id)(scope, receive, send)
        finally:
            if admitted:
                with self._lock:
                    self._active -= 1
            with correlation_scope(correlation_id):
                log_event(
                    self.logger,
                    LogEvent.API_REQUEST,
                    fields={
                        "status": "ok"
                        if status < 400
                        else "failed"
                        if status >= 500
                        else "denied"
                        if status in {401, 403, 404}
                        else "invalid",
                    },
                )
