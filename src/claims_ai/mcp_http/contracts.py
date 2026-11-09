"""Local HTTP limits and verified synthetic gateway identity; no production credentials."""

from dataclasses import dataclass
from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field

from claims_ai.models import Contract


class HttpLimits(Contract):
    host: Literal["127.0.0.1"] = "127.0.0.1"
    max_request_bytes: Annotated[int, Field(strict=True, ge=256, le=16384)] = 16384
    requests_per_window: Annotated[int, Field(strict=True, ge=1, le=60)] = 12
    window_seconds: Annotated[float, Field(strict=True, gt=0, le=300, allow_inf_nan=False)] = 60.0
    request_timeout_seconds: Annotated[
        float, Field(strict=True, gt=0, le=10, allow_inf_nan=False)
    ] = 5.0


@dataclass(frozen=True)
class VerifiedGateway:
    subject: UUID
    application_id: UUID


METHODS = ("initialize", "notifications/initialized", "ping", "tools/list", "tools/call")
