"""Trusted startup configuration and model-independent structured MCP replies."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import Field, model_validator

from claims_ai.agent_tools.contracts import Code, ToolGrant, ToolLimits, ToolReply
from claims_ai.models import Contract, Sha256, Version


class Error(StrEnum):
    CONTEXT = "trusted_context_unavailable"
    FORBIDDEN = "tool_not_allowed"
    LIMIT = "server_invocation_limit"
    ARGUMENTS = "invalid_or_oversized_arguments"
    EXPIRED = "server_execution_expired"
    FAILURE = "server_failure"


class ServerLimits(Contract):
    max_calls: Literal[3] = 3
    max_argument_bytes: Annotated[int, Field(strict=True, ge=256, le=16384)] = 4096
    lifetime_seconds: Annotated[float, Field(strict=True, gt=0, le=60, allow_inf_nan=False)] = 30.0
    tools: ToolLimits = ToolLimits()


class HostConfiguration(Contract):
    """Trusted local launcher input, never a JSON-RPC argument or identity token."""

    fixture_root: Path = Field(repr=False)
    fixture_id: Version
    manifest_sha256: Sha256
    grant: ToolGrant | None = None
    limits: ServerLimits = ServerLimits()


class ServerReply(Contract):
    status: Literal["ok", "error"]
    correlation_id: UUID | None = None
    code: Error | Code | None = None
    result: ToolReply | None = Field(default=None, repr=False)
    content_trust: Literal["untrusted_data"] = "untrusted_data"
    policy_status: Literal["provisional_unapproved"] = "provisional_unapproved"
    human_approval_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def safe_reply(self) -> Self:
        if self.status == "ok":
            if (
                self.result is None
                or self.result.status != "ok"
                or self.code is not None
                or self.correlation_id != self.result.correlation_id
            ):
                raise ValueError("successful MCP reply needs matching validated tool data")
        elif self.code is None or self.result is not None:
            raise ValueError("MCP error must contain a code and no tool data")
        return self
