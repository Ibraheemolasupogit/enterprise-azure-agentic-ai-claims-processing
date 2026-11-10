"""Versioned genuine FastAPI routes over existing host-governed services."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated, Any, Literal
from urllib.parse import parse_qsl
from uuid import UUID

from fastapi import APIRouter, Depends, FastAPI, Header, Path, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from claims_ai.api.auth import ApiAccess, Authenticator, DenyAll
from claims_ai.api.boundary import ApiBoundary, error_response
from claims_ai.api.contracts import (
    AdvisoryResponse,
    ApiCode,
    ApiError,
    ApiLimits,
    ClaimStatus,
    ErrorResponse,
    IntakeRequest,
    LivenessResponse,
    ProcessRequest,
    ReadinessResponse,
    ReviewQueueResponse,
)
from claims_ai.api.service import ClaimsApplication
from claims_ai.human_review.contracts import ReviewDecision, ReviewDetail, ReviewEvent

bearer = HTTPBearer(
    auto_error=False,
    scheme_name="SyntheticHostBearer",
    bearerFormat="OPAQUE_SYNTHETIC_HOST_CAPABILITY_NOT_ENTRA",
    description="Host-issued ephemeral synthetic capability. No real Entra/OAuth authentication.",
)


def identity(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> ApiAccess:
    access = getattr(request.state, "api_access", None)
    if credentials is None or not isinstance(access, ApiAccess):
        raise ApiError(401, ApiCode.AUTH)
    return access


Access = Annotated[ApiAccess, Depends(identity)]
Key = Annotated[
    UUID,
    Header(alias="Idempotency-Key", description="Required stable UUID for this logical operation."),
]
Match = Annotated[
    str,
    Header(
        alias="If-Match",
        pattern=r'^"[1-9][0-9]{0,7}"$',
        description="Strong quoted application revision, or review revision for review actions.",
    ),
]
ClaimPath = Annotated[str, Path(pattern=r"^NS-CLM-[A-Z0-9]{8}$")]
EntryPath = Annotated[str, Path(pattern=r"^[a-f0-9]{64}$")]


@dataclass
class Lifecycle:
    started: bool = False


def create_app(
    backend: ClaimsApplication | None = None,
    *,
    authenticator: Authenticator | None = None,
    limits: ApiLimits | None = None,
    logger: logging.Logger | None = None,
) -> FastAPI:
    profile = ApiLimits.model_validate(limits or (backend.limits if backend else ApiLimits()))
    lifecycle = Lifecycle()

    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncIterator[None]:
        lifecycle.started = True
        try:
            yield
        finally:
            lifecycle.started = False

    app = FastAPI(
        title="Northstar Offline Claims Application",
        version="1.0.0",
        description=(
            "Synthetic host identity; advisory recommendations only. No Azure readiness, "
            "real authentication, durable store or insurance-outcome authority."
        ),
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
        servers=[
            {
                "url": f"http://127.0.0.1:{profile.port}",
                "description": "Offline loopback profile; no hosting or TLS claim",
            }
        ],
    )

    def service() -> ClaimsApplication:
        if backend is None or not lifecycle.started:
            raise ApiError(503, ApiCode.UNAVAILABLE)
        return backend

    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, ApiError)
        return error_response(error.status, error.code, request.state.request_correlation_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, RequestValidationError)
        missing = any(
            e["type"] == "missing"
            and e["loc"][0] == "header"
            and e["loc"][-1].lower() in {"if-match", "if-none-match", "idempotency-key"}
            for e in error.errors()
        )
        return error_response(
            428 if missing else 422,
            ApiCode.REQUIRED if missing else ApiCode.INVALID,
            request.state.request_correlation_id,
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: Exception) -> JSONResponse:
        assert isinstance(error, HTTPException)
        response = error_response(
            error.status_code,
            ApiCode.MISSING if error.status_code == 404 else ApiCode.INVALID,
            request.state.request_correlation_id,
        )
        if error.status_code == 405 and error.headers:
            allow = error.headers.get("Allow") or error.headers.get("allow")
            if allow is not None:
                response.headers["Allow"] = allow
        return response

    @app.get("/health/live", response_model=LivenessResponse, operation_id="liveness")
    async def live() -> LivenessResponse:
        return LivenessResponse()

    @app.get(
        "/health/ready",
        response_model=ReadinessResponse,
        responses={503: {"model": ReadinessResponse}},
        operation_id="local_readiness",
    )
    async def ready(response: Response) -> ReadinessResponse:
        configured = backend is not None
        available = backend is not None and backend.available
        auth_configured = authenticator is not None and not isinstance(authenticator, DenyAll)
        local_ready = (
            lifecycle.started and auth_configured and backend is not None and backend.ready
        )
        response.status_code = 200 if local_ready else 503
        return ReadinessResponse(
            local_application_ready=local_ready,
            started=lifecycle.started,
            services_configured=configured,
            workflow_available=available,
            synthetic_authenticator_configured=auth_configured,
        )

    errors: dict[int | str, dict[str, Any]] = {
        status: {"model": ErrorResponse}
        for status in (400, 401, 403, 404, 405, 408, 409, 412, 413, 415, 422, 428, 429, 500, 503)
    }
    router = APIRouter(prefix="/api/v1", responses=errors)

    @router.post(
        "/claims", response_model=ClaimStatus, status_code=201, operation_id="intake_claim"
    )
    async def intake(
        body: IntakeRequest,
        access: Access,
        key: Key,
        response: Response,
        create_only: Annotated[Literal["*"], Header(alias="If-None-Match")],
    ) -> ClaimStatus:
        result = await service().intake(access, body, key)
        response.headers["ETag"] = f'"{result.application_revision}"'
        return result

    @router.post(
        "/claims/{claim_id}/process", response_model=ClaimStatus, operation_id="process_claim"
    )
    async def process(
        claim_id: ClaimPath,
        body: ProcessRequest,
        access: Access,
        key: Key,
        match: Match,
        response: Response,
    ) -> ClaimStatus:
        result = await service().process(access, claim_id, body, key, int(match[1:-1]))
        response.headers["ETag"] = f'"{result.application_revision}"'
        return result

    @router.get(
        "/claims/{claim_id}/status",
        response_model=ClaimStatus,
        operation_id="claim_processing_status",
    )
    async def status(claim_id: ClaimPath, access: Access, response: Response) -> ClaimStatus:
        result = service().status(access, claim_id)
        response.headers["ETag"] = f'"{result.application_revision}"'
        return result

    @router.get(
        "/claims/{claim_id}/advisory",
        response_model=AdvisoryResponse,
        operation_id="claim_advisory",
    )
    async def advisory(claim_id: ClaimPath, access: Access) -> AdvisoryResponse:
        return service().advisory(access, claim_id)

    @router.get(
        "/reviews", response_model=ReviewQueueResponse, operation_id="assigned_review_queue"
    )
    async def review_queue(
        request: Request,
        access: Access,
        limit: Annotated[int, Query(ge=1, le=16)] = 10,
        offset: Annotated[int, Query(ge=0, le=64)] = 0,
    ) -> ReviewQueueResponse:
        pairs = parse_qsl(request.url.query, keep_blank_values=True)
        if any(k not in {"limit", "offset"} for k, _ in pairs) or len({k for k, _ in pairs}) != len(
            pairs
        ):
            raise ApiError(400, ApiCode.INVALID)
        return service().review_list(access, offset, limit)

    @router.get(
        "/reviews/{entry_id}", response_model=ReviewDetail, operation_id="assigned_review_detail"
    )
    async def detail(entry_id: EntryPath, access: Access, response: Response) -> ReviewDetail:
        result = service().review_detail(access, entry_id)
        response.headers["ETag"] = f'"{result.entry.review_revision}"'
        return result

    @router.post(
        "/reviews/{entry_id}/actions",
        response_model=ReviewEvent,
        operation_id="human_recommendation_action",
    )
    async def action(
        entry_id: EntryPath,
        body: ReviewDecision,
        access: Access,
        key: Key,
        match: Match,
        response: Response,
    ) -> ReviewEvent:
        result = await service().review_action(access, entry_id, body, key, int(match[1:-1]))
        response.headers["ETag"] = f'"{result.sequence}"'
        return result

    app.include_router(router)
    app.add_middleware(
        ApiBoundary,
        authenticator=authenticator or DenyAll(),
        limits=profile,
        logger=logger or logging.getLogger("claims_ai.api"),
    )
    return app
