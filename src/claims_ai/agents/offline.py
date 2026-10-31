"""Supported SDK custom-client extension; model responses/faults here are SIMULATED."""

import asyncio
import json
from collections.abc import Mapping, Sequence
from enum import StrEnum
from typing import Any

from agent_framework import (
    BaseChatClient,
    ChatOptions,
    ChatResponse,
    Content,
    FunctionInvocationLayer,
    Message,
)

from claims_ai.agents.contracts import AgentDraft, Limits, ReviewPacket

TOOL_NAME = "read_review_packet"


class Mode(StrEnum):
    NORMAL = "normal"
    FORBIDDEN_TOOL = "forbidden_tool"
    WRONG_ARGUMENTS = "wrong_arguments"
    FLOOD = "tool_flood"
    LOOP = "loop"
    MALFORMED = "malformed_output"
    UNSUPPORTED = "unsupported_conclusion"
    WRONG_CITATION = "wrong_citation"
    WRONG_EVIDENCE = "wrong_evidence"
    WRONG_CLAIM = "wrong_claim"
    DOWNGRADE = "reviewer_downgrade"
    OVERSIZED = "oversized_output"
    TIMEOUT = "timeout"
    ERROR = "backend_error"
    ABSTAIN = "model_abstention"


class ExecutionLimit(ValueError):
    pass


class OfflineChatClient(
    FunctionInvocationLayer[ChatOptions[None]], BaseChatClient[ChatOptions[None]]
):
    """A real BaseChatClient extension using the SDK's real function-invocation layer."""

    def __init__(self, limits: Limits, mode: Mode = Mode.NORMAL) -> None:
        super().__init__(
            function_invocation_configuration={
                "enabled": True,
                "max_iterations": 2,
                "max_function_calls": 1,
                "max_duration_seconds": limits.timeout_seconds,
                "allow_concurrent_invocation": False,
                "terminate_on_unknown_calls": True,
                "include_detailed_errors": False,
            }
        )
        self.limits = limits
        self.mode = mode
        self.calls = 0
        self.requested_tool_calls = 0
        self.observed_roles: list[tuple[str, ...]] = []
        self.instructions: list[str] = []
        self.advertised_tools: list[tuple[str, ...]] = []

    async def _inner_get_response(
        self,
        *,
        messages: Sequence[Message],
        stream: bool,
        options: Mapping[str, Any],
        **kwargs: Any,
    ) -> ChatResponse[Any]:
        if stream:
            raise ValueError("offline client supports bounded non-streaming runs only")
        normalized = await self._validate_options(options)
        if self.calls >= self.limits.max_model_calls:
            raise ExecutionLimit("model_call_limit")
        self.calls += 1
        self.observed_roles.append(tuple(m.role for m in messages))
        self.instructions.append(str(normalized.get("instructions", "")))
        self.advertised_tools.append(
            tuple(t.name for t in normalized.get("tools", []) if hasattr(t, "name"))
        )
        if self.mode == Mode.TIMEOUT:
            await asyncio.Event().wait()
        if self.mode == Mode.ERROR:
            raise OSError("offline_backend_failure")
        if self.calls == 1 or self.mode == Mode.LOOP:
            name = "settle_claim" if self.mode == Mode.FORBIDDEN_TOOL else TOOL_NAME
            arguments = {"claim_id": "NS-CLM-00000000"} if self.mode == Mode.WRONG_ARGUMENTS else {}
            calls = [Content.from_function_call("read-1", name, arguments=arguments)]
            if self.mode == Mode.FLOOD:
                calls.append(Content.from_function_call("read-2", TOOL_NAME, arguments={}))
            self.requested_tool_calls += len(calls)
            return ChatResponse(
                messages=Message("assistant", calls), response_id="offline-tool-step"
            )
        results = [
            c.result
            for m in messages
            if m.role == "tool"
            for c in m.contents
            if c.type == "function_result"
        ]
        if len(results) != 1 or not isinstance(results[0], str):
            raise ValueError("one successful packet tool result is required")
        packet = ReviewPacket.model_validate_json(results[0])
        data: dict[str, object]
        if self.mode == Mode.ABSTAIN:
            data = {
                "claim_id": packet.claim_id,
                "packet_sha256": packet.packet_sha256,
                "disposition": "abstain",
                "required_reviewer": "supervisor",
                "findings": [],
            }
        else:
            data = {
                "claim_id": packet.claim_id,
                "packet_sha256": packet.packet_sha256,
                "disposition": "escalate" if packet.required_reviewer == "supervisor" else "review",
                "required_reviewer": packet.required_reviewer.value,
                "findings": [
                    {
                        "rule_id": f.rule_id.value,
                        "status": f.status.value,
                        "evidence_ids": list(f.evidence_ids),
                        "citations": [c.model_dump(mode="json") for c in f.citations],
                        "explanation": f.explanation,
                    }
                    for f in packet.findings
                ],
            }
        text = AgentDraft.model_validate(data).model_dump_json()
        if self.mode == Mode.MALFORMED:
            text = "not a structured response"
        elif self.mode == Mode.UNSUPPORTED:
            parsed = json.loads(text)
            parsed["findings"][0]["explanation"] = "This claim is approved for payment."
            text = json.dumps(parsed)
        elif self.mode == Mode.WRONG_CITATION:
            parsed = json.loads(text)
            parsed["findings"][0]["citations"][0]["policy_version"] = "wrong-version"
            text = json.dumps(parsed)
        elif self.mode == Mode.WRONG_EVIDENCE:
            parsed = json.loads(text)
            parsed["findings"][1]["evidence_ids"] = ["NS-EVD-00000000"]
            text = json.dumps(parsed)
        elif self.mode == Mode.WRONG_CLAIM:
            parsed = json.loads(text)
            parsed["claim_id"] = "NS-CLM-00000000"
            text = json.dumps(parsed)
        elif self.mode == Mode.DOWNGRADE:
            parsed = json.loads(text)
            parsed["required_reviewer"] = "reviewer"
            parsed["disposition"] = "review"
            text = json.dumps(parsed)
        elif self.mode == Mode.OVERSIZED:
            text = "x" * (self.limits.max_output_bytes + 1)
        return ChatResponse(
            messages=Message("assistant", [text]), response_id="offline-structured-step"
        )
