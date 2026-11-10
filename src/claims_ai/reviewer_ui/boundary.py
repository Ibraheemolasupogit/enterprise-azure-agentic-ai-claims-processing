"""Loopback browser profile, actual-byte form budgets and fixed safe response headers."""

import asyncio
from collections import Counter
from threading import Lock
from urllib.parse import parse_qsl

from starlette.responses import HTMLResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from claims_ai.reviewer_ui.client import UiError
from claims_ai.reviewer_ui.views import STYLE_HASH, error

COOKIE = "northstar_reviewer"


def safe_error(status: int) -> HTMLResponse:
    response = HTMLResponse(error(status), status_code=status)
    if status == 401:
        response.delete_cookie(COOKIE, path="/", httponly=True, samesite="strict")
    return response


class BrowserBoundary:
    def __init__(self, app: ASGIApp, *, port: int = 8767) -> None:
        self.app, self.authority = app, f"127.0.0.1:{port}"
        self._inflight = 0
        self._lock = Lock()

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def guarded_send(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend(
                    (key.encode(), value.encode())
                    for key, value in {
                        "cache-control": "no-store",
                        "x-content-type-options": "nosniff",
                        "referrer-policy": "no-referrer",
                        "permissions-policy": "camera=(), microphone=(), geolocation=()",
                        "content-security-policy": (
                            "default-src 'none'; script-src 'none'; style-src 'sha256-"
                            + STYLE_HASH
                            + "'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
                        ),
                    }.items()
                )
                message = {**message, "headers": headers}
            await send(message)

        active = False
        buffered: list[Message] = []
        response_bytes = 0
        overflow = False

        async def capture(message: Message) -> None:
            nonlocal response_bytes, overflow
            response_bytes += len(message.get("body", b""))
            if response_bytes > 2097152:
                overflow = True
                buffered.clear()
            if not overflow:
                buffered.append(message)

        try:
            try:
                headers = [
                    (k.decode("latin1").lower(), v.decode("latin1")) for k, v in scope["headers"]
                ]
                counts = Counter(k for k, _ in headers)
                values = dict(headers)
                peer = scope.get("client")
                server = scope.get("server")
                if (
                    not peer
                    or peer[0] != "127.0.0.1"
                    or not server
                    or server[0] != "127.0.0.1"
                    or str(server[1]) != self.authority.split(":")[1]
                    or scope.get("scheme") != "http"
                    or values.get("host") != self.authority
                    or scope.get("query_string")
                    or len(headers) > 64
                    or sum(len(k) + len(v) for k, v in headers) > 16384
                    or any(
                        n > 1
                        for k, n in counts.items()
                        if k in {"host", "cookie", "origin", "content-type", "content-length"}
                    )
                    or any(
                        k.startswith(
                            (
                                "forwarded",
                                "x-forwarded",
                                "x-role",
                                "x-case",
                                "x-user",
                                "x-identity",
                                "x-grant",
                            )
                        )
                        or k == "authorization"
                        for k in values
                    )
                ):
                    raise UiError(403)
                method = scope["method"]
                origin = values.get("origin")
                if origin is not None and origin != "http://" + self.authority:
                    raise UiError(403)
                if method not in {"GET", "POST"}:
                    raise UiError(400)
                if method == "POST" and origin != "http://" + self.authority:
                    raise UiError(403)
                if method == "POST" and (
                    values.get("content-type", "").lower() != "application/x-www-form-urlencoded"
                    or "content-encoding" in values
                ):
                    raise UiError(415)
                with self._lock:
                    if self._inflight >= 8:
                        raise UiError(429)
                    self._inflight += 1
                    active = True
                body = bytearray()
                try:
                    async with asyncio.timeout(3):
                        while True:
                            message = await receive()
                            if message["type"] != "http.request":
                                raise UiError(400)
                            body.extend(message.get("body", b""))
                            if len(body) > 8192:
                                raise UiError(413)
                            if not message.get("more_body", False):
                                break
                except TimeoutError:
                    raise UiError(400) from None
                if method == "GET" and body:
                    raise UiError(400)
                fields: dict[str, tuple[str, ...]] = {}
                if method == "POST":
                    try:
                        pairs = parse_qsl(
                            body.decode("utf-8", errors="strict"),
                            keep_blank_values=True,
                            strict_parsing=True,
                            max_num_fields=32,
                            encoding="utf-8",
                            errors="strict",
                        )
                    except (ValueError, UnicodeError):
                        raise UiError(422) from None
                    for key, value in pairs:
                        if len(key) > 32 or len(value) > 2000:
                            raise UiError(422)
                        if key in fields and key not in {"evidence", "requested_evidence"}:
                            raise UiError(422)
                        fields[key] = (*fields.get(key, ()), value)
                scope.setdefault("state", {})["ui_fields"] = fields
                await self.app(scope, receive, capture)
                if overflow:
                    raise UiError(503)
            except UiError as failure:
                buffered.clear()
                overflow = False
                response_bytes = 0
                await safe_error(failure.status)(scope, receive, capture)
            except Exception:
                buffered.clear()
                overflow = False
                response_bytes = 0
                await safe_error(503)(scope, receive, capture)
            for message in buffered:
                await guarded_send(message)
        finally:
            if active:
                with self._lock:
                    self._inflight -= 1
