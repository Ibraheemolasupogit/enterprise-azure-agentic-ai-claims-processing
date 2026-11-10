"""Exercise real workflow/framework/tool/MCP consumers with synthetic hostile sources."""

from hashlib import sha256
from pathlib import Path

import httpx2
from mcp import Client, types
from mcp.client.streamable_http import streamable_http_client

from claims_ai.adversarial.application import observed
from claims_ai.adversarial.authoring import contaminated
from claims_ai.adversarial.contracts import AttackCase, Observation
from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agent_tools.contracts import PolicyData, ToolLimits, ToolName
from claims_ai.agent_tools.tools import GovernedTools, LocalReadServices
from claims_ai.agents.__main__ import demo_input
from claims_ai.agents.assessment import INSTRUCTIONS, assess
from claims_ai.agents.contracts import AssessmentInput, Limits
from claims_ai.agents.offline import Mode, OfflineChatClient
from claims_ai.agents.prepare import prepare_packet
from claims_ai.benchmark.contracts import ExtractionResponse
from claims_ai.evidence.contracts import ProcessingRequest
from claims_ai.mcp_http.auth import SyntheticIssuer
from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip
from claims_ai.mcp_server.client import arguments, checked
from claims_ai.mcp_server.contracts import ServerReply
from claims_ai.mcp_server.server import GovernedMCP
from claims_ai.rules.contracts import EvidenceInput
from claims_ai.workflow.__main__ import demo_grant as workflow_grant
from claims_ai.workflow.__main__ import demo_request, injected_document
from claims_ai.workflow.contracts import WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner


class ManipulatedPolicy(LocalReadServices):
    def __init__(self, payload: str) -> None:
        self.payload, self.calls = payload, 0

    async def policy(self, value: AssessmentInput) -> PolicyData:
        actual = await super().policy(value)
        self.calls += 1
        chunk = actual.clauses[0]
        clause = chunk.clause.model_copy(update={"text": self.payload})
        changed = chunk.model_copy(update={"clause": clause})
        return PolicyData(clauses=(changed, *actual.clauses[1:]))


class RuntimeHarness:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.valid = demo_input(root, "valid-v1")

    async def content(self, case: AttackCase) -> Observation:
        if case.attack in {
            "workflow_document",
            "extract_forge",
            "source_tamper",
            "conflicting_evidence",
        }:
            request = demo_request(
                self.root,
                "conflicting-amounts" if case.attack == "conflicting_evidence" else "valid-v1",
                "m19-" + case.case_id,
            )
            if case.attack == "workflow_document":
                request = injected_document(request)
            elif case.attack in {"extract_forge", "source_tamper"}:
                target = request.evidence_inputs[0]
                raw = target.response.model_dump(mode="json")
                processing = target.request
                if case.attack == "extract_forge":
                    raw["fields"][0]["value"] = case.payload
                else:
                    processing = ProcessingRequest.model_validate(
                        {**processing.model_dump(), "content": processing.content + b"CORRUPTED"}
                    )
                replacement = EvidenceInput(
                    request=processing, response=ExtractionResponse.model_validate(raw)
                )
                request = WorkflowRequest.model_validate(
                    {
                        **request.model_dump(exclude={"evidence_inputs"}),
                        "evidence_inputs": (replacement, *request.evidence_inputs[1:]),
                    }
                )
            checkpoint = await WorkflowRunner().run(request, workflow_grant(request))
            snapshot = checkpoint.snapshot
            task = snapshot.review_task
            return observed(
                {
                    "state": checkpoint.state.value,
                    "human_required": task is not None and task.human_approval_required,
                    "supervisor_required": task is not None
                    and task.required_reviewer.value == "supervisor",
                    "no_outcome": snapshot.case.decision is None
                    and snapshot.case.assessment is None,
                    "payload_in_evidence": any(
                        case.payload in e.observed_value for e in snapshot.case.evidence
                    ),
                    "model_executed": snapshot.agent_result is not None
                    and snapshot.agent_result.framework_executed,
                },
                (
                    "Actual M12/M6/M9 runtime over in-memory synthetic bytes and "
                    "extraction fields; model execution remains simulated."
                ),
            )
        value = self.valid
        packet_has_payload = False
        if case.attack in {"document", "policy"}:
            value = contaminated(value, case.payload, policy=case.attack == "policy")
            packet_has_payload = case.payload in prepare_packet(value, Limits()).model_dump_json()
        elif case.attack == "note":
            value = AssessmentInput.model_validate(
                {
                    **value.model_dump(exclude={"rule_request"}),
                    "rule_request": value.rule_request,
                    "untrusted_note": case.payload,
                }
            )
        client = OfflineChatClient(Limits())
        result = await assess(value, client=client)
        return Observation(
            execution="SIMULATED_MODEL_RUNTIME_GUARDS",
            facts={
                "status": result.status,
                "framework_executed": result.framework_executed,
                "payload_in_packet": packet_has_payload,
                "instructions_unchanged": bool(client.instructions)
                and all(item == INSTRUCTIONS for item in client.instructions),
                "payload_in_instructions": any(
                    case.payload in item for item in client.instructions
                ),
                "no_outcome": result.final_outcome is None and not result.settlement_authorized,
                "human_required": result.human_review_required,
            },
            evidence_note=(
                "Valid synthetic source bytes replayed through M6/M7/M9 and actual"
                " SDK dispatch. Simulated client behavior is not evidence of "
                "live-model injection resistance."
            ),
        )

    async def agent(self, case: AttackCase) -> Observation:
        modes = {
            "positive": Mode.NORMAL,
            "forbidden": Mode.FORBIDDEN_TOOL,
            "downgrade": Mode.DOWNGRADE,
            "unsupported": Mode.UNSUPPORTED,
            "citation": Mode.WRONG_CITATION,
            "evidence": Mode.WRONG_EVIDENCE,
            "cross_case": Mode.WRONG_CLAIM,
            "flood": Mode.FLOOD,
            "malformed": Mode.MALFORMED,
            "oversized": Mode.OVERSIZED,
        }
        value = (
            demo_input(self.root, "gradual-wear-exclusion")
            if case.attack == "downgrade"
            else self.valid
        )
        before = value.rule_request.case.model_dump_json()
        client = OfflineChatClient(Limits(), modes[case.attack])
        result = await assess(value, client=client)
        return Observation(
            execution="SIMULATED_MODEL_RUNTIME_GUARDS",
            facts={
                "status": result.status,
                "framework_executed": result.framework_executed,
                "model_calls": result.model_calls,
                "tool_calls": result.tool_executions,
                "reason": result.reason.value if result.reason is not None else None,
                "timed_out": result.reason is not None
                and result.reason.value == "execution_timeout",
                "attack_emitted": client.calls > 0,
                "privileged_tools_advertised": any(
                    "settle_claim" in names for names in client.advertised_tools
                ),
                "no_outcome": result.final_outcome is None and not result.settlement_authorized,
                "case_unchanged": before == value.rule_request.case.model_dump_json(),
            },
            evidence_note=(
                "Existing scripted malicious model outputs/tool requests pass "
                "through actual Microsoft Agent Framework invocation and "
                "deterministic host validation."
            ),
        )

    async def tools(self, case: AttackCase) -> Observation:
        services = ManipulatedPolicy(case.payload)
        tools = GovernedTools(
            self.valid,
            demo_grant(self.valid, "m19-" + case.case_id),
            ToolLimits(),
            services=services if case.attack == "manipulated" else None,
        )
        tool = (
            ToolName.POLICY
            if case.attack in {"wrong_version", "manipulated"}
            else ToolName.EVIDENCE
        )
        args = arguments(self.valid, tool)
        if case.attack == "cross_case":
            args["claim_id"] = "NS-CLM-00000000"
        if case.attack == "spoof_grant":
            args["principal_id"] = "caller-cannot-authorize"
        if case.attack == "wrong_version":
            args["policy_version"] = "wrong-version"
        reply = await tools.read(tool, args)
        if case.attack == "repeat":
            reply = await tools.read(tool, args)
        return observed(
            {
                "status": reply.status,
                "code": reply.code.value if reply.code else None,
                "service_called": services.calls == 1,
            },
            (
                "Production M11 guard; manipulated dependency first executes the "
                "real local retrieval before returning altered content."
            ),
            injected=case.attack == "manipulated",
        )

    async def mcp(self, case: AttackCase) -> Observation:
        issuer = SyntheticIssuer()
        grant = demo_grant(self.valid, "m19-" + case.case_id)
        if case.attack == "budget":
            server = GovernedMCP(self.valid, grant)
            params = types.CallToolRequestParams(
                name=ToolName.EVIDENCE.value, arguments=arguments(self.valid, ToolName.EVIDENCE)
            )
            first = await server.invoke(params)
            second = await server.invoke(params)
            return observed(
                {
                    "first_ok": first.status == "ok",
                    "code": second.code.value if second.code else None,
                },
                "Direct production M13 server invocation guard; not a socket/protocol measurement.",
            )
        services = ManipulatedPolicy(case.payload)
        boundary = HttpBoundary(
            self.valid,
            grant,
            port=8765,
            gateway_subject=issuer.subject,
            verifier=issuer.verifier,
            services=services if case.attack == "service_payload" else None,
        )
        url = "http://127.0.0.1:8765/mcp"
        async with boundary.app.router.lifespan_context(boundary.app):
            transport = httpx2.ASGITransport(app=boundary.app)
            if case.attack == "positive":
                report = await protocol_roundtrip(
                    url, issuer.issue(), self.valid, transport=transport
                )
                tools = report["tools"]
                return observed(
                    {
                        "three_reads": isinstance(tools, list) and len(tools) == 3,
                        "only_read_tools": tools == list(ToolName),
                    },
                    (
                        "Actual MCP 2.2.0 initialization, discovery and typed calls "
                        "through Streamable HTTP/ASGI."
                    ),
                )
            if case.attack in {"unauthenticated", "forbidden", "spoof_header", "duplicate_json"}:
                headers = {
                    "Content-Type": "application/json",
                    "Accept": "application/json, text/event-stream",
                    "Authorization": "Bearer " + issuer.issue(),
                }
                if case.attack in {"unauthenticated", "spoof_header"}:
                    headers.pop("Authorization")
                if case.attack == "spoof_header":
                    headers["X-Gateway-Principal"] = "caller-selected"
                body = (
                    b'{"jsonrpc":"2.0","jsonrpc":"2.0","id":1,"method":"ping"}'
                    if case.attack == "duplicate_json"
                    else (
                        b'{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"s'
                        b'ettle_claim","arguments":{}}}'
                    )
                )
                if case.attack in {"unauthenticated", "spoof_header"}:
                    body = b'{"jsonrpc":"2.0","id":1,"method":"ping"}'
                async with httpx2.AsyncClient(transport=transport, trust_env=False) as http:
                    response = await http.post(url, headers=headers, content=body)
                return observed(
                    {
                        "status": response.status_code,
                        "response_sha256": sha256(response.content).hexdigest(),
                    },
                    "Actual M14 pre-SDK HTTP authentication/envelope/allowlist guard.",
                )
            async with httpx2.AsyncClient(
                headers={"Authorization": "Bearer " + issuer.issue()},
                transport=transport,
                trust_env=False,
            ) as http:
                stream = streamable_http_client(url, http_client=http, terminate_on_close=False)
                async with Client(stream, mode="legacy", read_timeout_seconds=5) as client:
                    tool = ToolName.EVIDENCE if case.attack == "cross_case" else ToolName.POLICY
                    args = arguments(self.valid, tool)
                    if case.attack == "cross_case":
                        args["claim_id"] = "NS-CLM-00000000"
                    result = await client.call_tool(tool.value, args)
                    original = checked(result, value=self.valid, tool=tool)
                    if case.attack in {"cross_case", "service_payload"}:
                        return observed(
                            {
                                "status": original.status,
                                "code": original.code.value if original.code else None,
                                "service_called": services.calls == 1,
                                "foreign_case_present": "NS-CLM-00000000"
                                in original.model_dump_json(),
                            },
                            (
                                "Actual SDK invocation consumes adversarial arguments or a "
                                "host-injected retrieval-service result."
                            ),
                            injected=case.attack == "service_payload",
                        )
                    if (
                        original.status != "ok"
                        or original.result is None
                        or not isinstance(original.result.data, PolicyData)
                    ):
                        raise ValueError("successful canonical MCP policy response required")
                    reply_payload = original.model_dump(mode="json")
                    reply_payload["result"]["data"]["clauses"][0]["clause"]["text"] = case.payload
                    mutated = ServerReply.model_validate(reply_payload)
                    tampered = types.CallToolResult.model_validate(
                        {
                            "isError": False,
                            "structuredContent": mutated.model_dump(mode="json"),
                            "content": [
                                {
                                    "type": "text",
                                    "text": original.model_dump_json()
                                    if case.attack == "text_mismatch"
                                    else mutated.model_dump_json(),
                                }
                            ],
                        }
                    )
                    rejected = False
                    payload_returned = False
                    try:
                        payload_returned = (
                            case.payload
                            in checked(tampered, value=self.valid, tool=tool).model_dump_json()
                        )
                    except ValueError:
                        rejected = True
                    return observed(
                        {
                            "tamper_rejected": rejected,
                            "payload_returned": payload_returned,
                            "canonical_sdk_response": True,
                        },
                        (
                            "Real SDK response is modified after server validation; actual M13"
                            " consumer parser is evaluated. Simulated compromised-response "
                            "path, not a demonstrated remote exploit."
                        ),
                        injected=True,
                    )
