"""Server-rendered browser application; all reads and actions use the existing M16 API."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI, Path, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.responses import HTMLResponse, RedirectResponse

from claims_ai.reviewer_ui import views
from claims_ai.reviewer_ui.boundary import COOKIE, BrowserBoundary, safe_error
from claims_ai.reviewer_ui.client import ApiClient, UiError
from claims_ai.reviewer_ui.sessions import Sessions


def create_ui(api: ApiClient, sessions: Sessions, *, port: int = 8767) -> FastAPI:
    if port not in range(1024, 65536):
        raise ValueError("local UI port outside allowed range")
    started = False

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        nonlocal started
        started = True
        try:
            yield
        finally:
            started = False

    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)

    def cookie(request: Request) -> str:
        if not started:
            raise UiError(503)
        return request.cookies.get(COOKIE, "")

    def fields(request: Request, allowed: set[str]) -> dict[str, tuple[str, ...]]:
        data: dict[str, tuple[str, ...]] = request.state.ui_fields
        if not data.keys() <= allowed:
            raise UiError(422)
        return data

    @app.exception_handler(UiError)
    def ui_error(request: Request, failure: Exception) -> HTMLResponse:
        assert isinstance(failure, UiError)
        return safe_error(failure.status)

    @app.exception_handler(RequestValidationError)
    @app.exception_handler(HTTPException)
    def validation(request: Request, failure: Exception) -> HTMLResponse:
        return safe_error(404)

    @app.exception_handler(Exception)
    def internal(request: Request, failure: Exception) -> HTMLResponse:
        return safe_error(503)

    @app.get("/login", response_class=HTMLResponse)
    def login_page(request: Request) -> HTMLResponse:
        cookie(request)
        token, session = sessions.anonymous()
        response = HTMLResponse(views.login(session))
        response.set_cookie(COOKIE, token, max_age=300, httponly=True, samesite="strict", path="/")
        return response

    @app.post("/login")
    def login(request: Request) -> RedirectResponse:
        data = fields(request, {"csrf", "code"})
        token, session = sessions.login(
            cookie(request), data.get("csrf", ("",))[0], data.get("code", ("",))[0]
        )
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(COOKIE, token, max_age=900, httponly=True, samesite="strict", path="/")
        return response

    @app.post("/logout")
    def logout(request: Request) -> RedirectResponse:
        data = fields(request, {"csrf"})
        sessions.logout(cookie(request), data.get("csrf", ("",))[0])
        response = RedirectResponse("/login", status_code=303)
        response.delete_cookie(COOKIE, httponly=True, samesite="strict", path="/")
        return response

    def queue(request: Request, offset: int) -> HTMLResponse:
        session = sessions.get(cookie(request))
        assert session.profile is not None
        return HTMLResponse(
            views.dashboard(api.queue(session.profile.api_token, offset), session, offset)
        )

    @app.get("/", response_class=HTMLResponse)
    def dashboard(request: Request) -> HTMLResponse:
        return queue(request, 0)

    @app.get("/queue/{offset}", response_class=HTMLResponse)
    def paginated(request: Request, offset: Annotated[int, Path(ge=16, le=64)]) -> HTMLResponse:
        return queue(request, offset)

    @app.get("/reviews/{entry_id}", response_class=HTMLResponse)
    def detail(
        request: Request, entry_id: Annotated[str, Path(pattern=r"^[a-f0-9]{64}$")]
    ) -> HTMLResponse:
        token = cookie(request)
        session = sessions.get(token)
        assert session.profile is not None
        view = api.view(session.profile.api_token, entry_id)
        ticket = sessions.prepare(token, view.detail)
        return HTMLResponse(views.case_detail(view, session, ticket))

    @app.post("/reviews/{entry_id}/actions", response_class=HTMLResponse)
    def act(
        request: Request, entry_id: Annotated[str, Path(pattern=r"^[a-f0-9]{64}$")]
    ) -> HTMLResponse:
        data = fields(
            request, {"csrf", "ticket", "action", "rationale", "evidence", "requested_evidence"}
        )
        token = cookie(request)
        profile, decision = sessions.decision(token, entry_id, data)
        event = api.act(profile.api_token, decision)
        return HTMLResponse(views.receipt(event, sessions.get(token)))

    app.add_middleware(BrowserBoundary, port=port)
    return app
