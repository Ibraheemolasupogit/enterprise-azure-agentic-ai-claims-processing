"""Actual offline service composition and disposable faults; no production/provider claim."""

import asyncio
import json
import signal
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path
from uuid import UUID

import httpx2
from fastapi.testclient import TestClient

from claims_ai.agent_tools.__main__ import demo_grant as tool_grant
from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.agents.__main__ import demo_input
from claims_ai.api.fixtures import demo_application
from claims_ai.mcp_http.auth import SyntheticIssuer
from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip
from claims_ai.models import AssessmentOutcome
from claims_ai.outcomes.contracts import Action, ApprovedInput, Command, OutcomeError
from claims_ai.outcomes.demo import approved_fixture, command, demo_host, prepared_store
from claims_ai.outcomes.store import encoded
from claims_ai.quality_ops.boundaries import ObservedASGI, propagate_request
from claims_ai.quality_ops.instrumentation import ObservedReads, ObservedStages
from claims_ai.quality_ops.operational_authority import CONTEXT, EPOCH, INTEGRITY, NS, issue_grants
from claims_ai.quality_ops.telemetry import LocalSink, Telemetry, inject_parent
from claims_ai.reviewer_ui.__main__ import ORIGIN, action_fields, enroll
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.client import ApiClient
from claims_ai.reviewer_ui.host import seed
from claims_ai.reviewer_ui.sessions import Profile, Sessions
from claims_ai.security_hardening.lifecycle import Lifecycle
from claims_ai.workflow.__main__ import demo_grant, demo_request
from claims_ai.workflow.contracts import Checkpoint, Stage, State, WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner


class ObservedWorkflow:
    def __init__(self, telemetry: Telemetry):
        self.telemetry = telemetry

    async def run(self, request: WorkflowRequest, grant: ToolGrant) -> Checkpoint:
        with self.telemetry.boundary("workflow", grant.correlation_id):
            return await WorkflowRunner(
                services=ObservedStages(self.telemetry, grant.correlation_id)
            ).run(request, grant)


def workflow_probe(root: Path, telemetry: Telemetry, fault: str) -> dict[str, object]:
    request = demo_request(root, "valid-v1", "m22-" + fault)
    grant = demo_grant(request)
    stages = ObservedStages(telemetry, grant.correlation_id, fault=fault)

    async def execute() -> Checkpoint:
        with telemetry.boundary("workflow", grant.correlation_id):
            return await WorkflowRunner(services=stages).run(request, grant)

    checkpoint = asyncio.run(execute())
    expected = State.FAILED if fault in {"outage", "timeout"} else State.REVIEW
    attempts = sum(r.stage == Stage.POLICY for r in checkpoint.records)
    return {
        "scenario": "workflow_" + fault,
        "execution": "HOST_INJECTED_RUNTIME_GUARDS",
        "pass": checkpoint.state == expected
        and attempts == (1 if fault == "none" else 2)
        and checkpoint.snapshot.case.decision is None,
        "state": checkpoint.state.value,
        "policy_attempts": attempts,
        "operational_outcome": False,
    }


def api_review_probe(root: Path, telemetry: Telemetry) -> dict[str, object]:
    from datetime import timedelta

    from claims_ai.human_review.__main__ import NOW as REVIEW_NOW

    fixture = demo_application(root, runner=ObservedWorkflow(telemetry), fixtures=("valid-v1",))
    with TestClient(
        ObservedASGI(fixture.app, telemetry),
        base_url="http://127.0.0.1:8766",
        headers={"X-Correlation-ID": str(NS), **inject_parent()},
        client=("127.0.0.1", 51000),
    ) as backend:
        backend.event_hooks["request"].append(propagate_request)
        seed(backend, fixture)
        api = ApiClient(backend)
        entry = api.queue(fixture.tokens["reviewer"]).items[0]
        backlog = len(api.queue(fixture.tokens["reviewer"]).items)
        sessions = Sessions(
            clock=lambda: REVIEW_NOW + timedelta(seconds=10),
            credential_valid=lambda t: fixture.authenticator.verify(t) is not None,
        )
        code = sessions.provision(
            Profile("Synthetic development reviewer", fixture.tokens["reviewer"])
        )
        with TestClient(
            ObservedASGI(create_ui(api, sessions), telemetry, boundary="review.action"),
            base_url=ORIGIN,
            headers={"X-Correlation-ID": str(NS), **inject_parent()},
            client=("127.0.0.1", 52000),
        ) as browser:
            enroll(browser, code)
            path = "/reviews/" + entry.entry_id
            fields = action_fields(browser.get(path).text, "approve_recommendation")
            accepted = browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN})
            fixture.authenticator.revoke(fixture.tokens["reviewer"])
            denied = browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN})
        direct = backend.get(
            "/api/v1/reviews",
            headers={
                "traceparent": "00-" + "a" * 32 + "-" + "b" * 16 + "-01",
                "baggage": "role=supervisor,token=private",
                "X-Correlation-ID": str(NS),
            },
        )
    parents = {r["span_id"]: r for r in telemetry.sink.records if r["boundary"] == "review.action"}
    links = [
        r
        for r in telemetry.sink.records
        if r["boundary"] == "api.request" and r["parent_span_id"] in parents
    ]
    linked = bool(links) and all(
        r["trace_id"] == parents[r["parent_span_id"]]["trace_id"]
        and r["correlation_id"] == parents[r["parent_span_id"]]["correlation_id"]
        for r in links
    )
    return {
        "scenario": "api_ui_current_authority",
        "execution": "RUNTIME_ASGI",
        "pass": linked
        and accepted.status_code == 200
        and denied.status_code == direct.status_code == 401,
        "cross_boundary_link": linked,
        "revoked_receipt_status": denied.status_code,
        "trace_cannot_authenticate": direct.status_code,
        "review_backlog_before": backlog,
    }


def mcp_probe(root: Path, telemetry: Telemetry) -> dict[str, object]:
    value = demo_input(root, "valid-v1")
    grant = tool_grant(value, "m22-tools")
    issuer = SyntheticIssuer()
    boundary = HttpBoundary(
        value,
        grant,
        port=8765,
        gateway_subject=issuer.subject,
        verifier=issuer.verifier,
        services=ObservedReads(telemetry, grant.correlation_id),
    )
    observed = ObservedASGI(boundary.app, telemetry, boundary="mcp.request")

    class Transport(httpx2.AsyncBaseTransport):
        async def handle_async_request(self, request: httpx2.Request) -> httpx2.Response:
            request.headers.update(inject_parent())
            request.headers["X-Correlation-ID"] = str(grant.correlation_id)
            return await httpx2.ASGITransport(app=observed).handle_async_request(request)

    async def execute() -> tuple[dict[str, object], int]:
        async with boundary.app.router.lifespan_context(boundary.app):
            with telemetry.boundary("workflow", grant.correlation_id):
                result = await protocol_roundtrip(
                    "http://127.0.0.1:8765/mcp", issuer.issue(), value, transport=Transport()
                )
                async with httpx2.AsyncClient(transport=Transport()) as client:
                    denied = await client.post("http://127.0.0.1:8765/mcp", json={})
        return result, denied.status_code

    result, denied = asyncio.run(execute())
    tools = result["tools"]
    if not isinstance(tools, list):
        raise ValueError("MCP discovery unavailable")
    return {
        "scenario": "mcp_three_governed_reads",
        "execution": "RUNTIME_ASGI_SDK",
        "pass": len(tools) == 3 and denied == 401,
        "tool_count": len(tools),
        "missing_identity_status": denied,
    }


def child_request(
    directory: Path,
    approval: ApprovedInput,
    request: Command,
    lifecycle: Lifecycle,
    grants: dict[str, object],
    telemetry: Telemetry,
    *,
    fault: str = "none",
    fail_export: bool = False,
) -> subprocess.CompletedProcess[str]:
    import claims_ai

    package = str(Path(claims_ai.__file__).resolve().parent.parent)
    payload = {
        "approval": encoded(approval),
        "command": encoded(request),
        "database": str(directory / "case.sqlite3"),
        "lifecycle": str(lifecycle.path),
        "context": CONTEXT,
        "integrity_key": INTEGRITY.hex(),
        "anchor": lifecycle.checkpoint().model_dump(mode="json"),
        "grants": grants,
        "fault": fault,
        "telemetry_fail": fail_export,
        "correlation": str(request.correlation_id),
        "carrier": inject_parent(),
    }
    code = (
        "import sys;sys.path.insert(0,sys.argv[1]);"
        "from claims_ai.quality_ops.operational_worker import main;main()"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, package],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=directory,
        timeout=30,
    )
    if len(result.stdout) > 65536:
        raise ValueError("child response capacity")
    return result


def outcome_probes(
    root: Path, telemetry: Telemetry
) -> tuple[list[dict[str, object]], list[object]]:
    approval = asyncio.run(
        approved_fixture(root, name="m22-operations", approved_outcome=AssessmentOutcome.ELIGIBLE)
    )
    rows: list[dict[str, object]] = []
    child_spans: list[object] = []
    with tempfile.TemporaryDirectory(prefix="m22-outcomes-") as name:
        base = Path(name)
        for variant in ("export_failure", "before_commit", "after_commit", "storage_failure"):
            directory = base / variant
            directory.mkdir(mode=0o700)
            lifecycle = Lifecycle(
                directory / "lifecycle.sqlite3",
                context_sha256=CONTEXT,
                integrity_key=INTEGRITY,
                create=True,
                clock=lambda: EPOCH,
            )
            host = demo_host((approval,))
            grants = issue_grants(host, lifecycle)
            grant_data: dict[str, object] = {
                n: g.model_dump(mode="json") for n, g in grants.items()
            }
            store, _, state = prepared_store(directory / "case.sqlite3", approval, host)
            request = command(Action.DECIDE, "m22-" + variant, approval, state)
            before = store.read(host.tokens["host"], request.claim_id)
            if variant == "storage_failure":

                def storage_fault(point: str) -> None:
                    if point == "after_projection":
                        raise sqlite3.OperationalError("synthetic storage write failure")

                store.fault = storage_fault
                try:
                    with telemetry.boundary("outcome.commit", request.correlation_id):
                        store.execute(host.tokens["reviewer"], request)
                except OutcomeError as error:
                    denied = str(error) == "storage_unavailable_or_corrupt"
                else:
                    denied = False
                store.fault = lambda point: None
                unchanged = store.read(host.tokens["host"], request.claim_id) == before
                rows.append(
                    {
                        "scenario": "storage_projection_failure_rollback",
                        "execution": "RUNTIME",
                        "pass": denied and unchanged,
                        "partial_outcome_committed": not unchanged,
                    }
                )
                continue
            export_failed = False
            if variant == "export_failure":
                failed = Telemetry(sink=LocalSink())
                failed.sink.fail = True
                with failed.boundary("outcome.commit", request.correlation_id):
                    accepted = store.execute(host.tokens["reviewer"], request)
                export_failed = failed.sink.export_failures == 1
                failed.close()
                event_hash = accepted.event_sha256
            else:
                with telemetry.boundary("recovery", request.correlation_id):
                    killed = child_request(
                        directory,
                        approval,
                        request,
                        lifecycle,
                        grant_data,
                        telemetry,
                        fault=variant,
                    )
                if killed.returncode != -signal.SIGKILL:
                    raise ValueError("process fault was not exercised")
                event_hash = None
            with telemetry.boundary("recovery", request.correlation_id):
                carrier = inject_parent()
                child = child_request(
                    directory, approval, request, lifecycle, grant_data, telemetry
                )
            if child.returncode:
                raise ValueError("fresh authority recovery unavailable")
            recovered = json.loads(child.stdout)
            raw_spans = recovered["telemetry"]["spans"]
            linked = (
                len(raw_spans) == 1 and raw_spans[0]["trace_id"] == carrier["traceparent"][3:35]
            )
            linked = linked and raw_spans[0]["parent_span_id"] == carrier["traceparent"][36:52]
            child_spans.extend(raw_spans)
            duplicate = child_request(
                directory, approval, request, lifecycle, grant_data, telemetry
            )
            if duplicate.returncode:
                raise ValueError("duplicate recovery unavailable")
            repeated = json.loads(duplicate.stdout)
            passed = (
                recovered["allowed"] is True
                and recovered["decisions"] == 1
                and recovered["audit_events"] == 5
                and linked
                and repeated["event_sha256"] == recovered["event_sha256"]
                and (event_hash is None or recovered["event_sha256"] == event_hash)
            )
            rows.append(
                {
                    "scenario": "outcome_" + variant,
                    "execution": "ACTUAL_SUBPROCESSES",
                    "pass": passed and (export_failed if variant == "export_failure" else True),
                    "decisions": recovered["decisions"],
                    "audit_events": recovered["audit_events"],
                    "duplicate_receipt_equal": repeated["event_sha256"]
                    == recovered["event_sha256"],
                    "w3c_process_link": linked,
                    "sigkill": variant != "export_failure",
                    "export_failure": export_failed,
                }
            )
            if variant == "export_failure":
                try:
                    store.execute(
                        host.tokens["reviewer"],
                        command(Action.DECIDE, "m22-stale", approval, state),
                    )
                except OutcomeError as error:
                    stale = str(error) == "revision_conflict"
                else:
                    stale = False
                rows.append({"scenario": "stale_revision", "execution": "RUNTIME", "pass": stale})
                statuses = [
                    store.dispatch(
                        host.tokens["host"], request.claim_id, accepted.event_id, unavailable=True
                    )
                    for _ in range(3)
                ]
                rows.append(
                    {
                        "scenario": "bounded_outbox_retries",
                        "execution": "RUNTIME",
                        "pass": statuses == ["pending", "pending", "dead"],
                        "attempts": len(statuses),
                        "state": statuses[-1],
                    }
                )
                lifecycle.revoke(grants["reviewer"].grant_id)
                revoked = child_request(
                    directory, approval, request, lifecycle, grant_data, telemetry
                )
                if revoked.returncode:
                    raise ValueError("revoked historical replay unavailable")
                denied = json.loads(revoked.stdout)
                rows.append(
                    {
                        "scenario": "revoked_duplicate_after_process_recovery",
                        "execution": "RUNTIME",
                        "pass": denied["allowed"] is False
                        and denied["audit_events"] == 5
                        and denied["decisions"] == 1,
                        "duplicate_allowed": denied["allowed"],
                        "history_retained": True,
                    }
                )
                rows.append(
                    {
                        "scenario": "outbox_retries_survive_restart",
                        "execution": "ACTUAL_SUBPROCESS",
                        "pass": denied["outbox_dead"] == 1 and denied["outbox_attempts"] == 3,
                        "dead": denied["outbox_dead"],
                        "attempts": denied["outbox_attempts"],
                    }
                )
    return rows, child_spans


def graph_check(records: list[dict[str, object]], correlation: UUID) -> bool:
    selected = [r for r in records if r["correlation_id"] == str(correlation)]
    lookup = {r["span_id"]: r for r in selected}
    expected = {s.value: "workflow" for s in Stage}
    expected.update({"tool.evidence": "agent", "tool.policy": "agent", "tool.rules": "agent"})
    for name, parent in expected.items():
        matches = [r for r in selected if r["boundary"] == name]
        if len(matches) != 1 or matches[0]["parent_span_id"] not in lookup:
            return False
        ancestor = lookup[matches[0]["parent_span_id"]]
        if ancestor["boundary"] != parent or ancestor["trace_id"] != matches[0]["trace_id"]:
            return False
    return True


def exercise(root: Path, telemetry: Telemetry) -> tuple[dict[str, object], list[object]]:
    rows = [
        workflow_probe(root, telemetry, fault)
        for fault in ("none", "outage", "timeout", "retry_once")
    ]
    normal = demo_grant(demo_request(root, "valid-v1", "m22-none")).correlation_id
    rows.append(
        {
            "scenario": "complete_workflow_trace_graph",
            "execution": "RUNTIME_SDK",
            "pass": graph_check(telemetry.sink.records, normal),
        }
    )
    rows.extend((api_review_probe(root, telemetry), mcp_probe(root, telemetry)))
    outcomes, child_spans = outcome_probes(root, telemetry)
    rows.extend(outcomes)
    healthy = Telemetry(sink=LocalSink(max_spans=1))
    for _ in range(2):
        with healthy.boundary("identity.check", NS):
            pass
    bounded = len(healthy.sink.records) == healthy.sink.dropped == 1
    healthy.close()
    rows.append(
        {
            "scenario": "telemetry_capacity",
            "execution": "RUNTIME_SDK",
            "pass": bounded,
            "dropped": 1 if bounded else healthy.sink.dropped,
        }
    )
    from claims_ai.security_hardening.evaluation import restart_observation

    rollback = restart_observation("rollback")
    facts = rollback.facts
    rows.append(
        {
            "scenario": "current_anchor_rollback",
            "execution": "ACTUAL_SUBPROCESSES",
            "pass": facts.get("positive_before") is True
            and facts.get("signature_valid_after") is True
            and facts.get("preserved_context") is True
            and facts.get("allowed_after") is False,
            "signature_valid_after": facts.get("signature_valid_after"),
            "allowed_after": facts.get("allowed_after"),
        }
    )
    by_name = {str(r["scenario"]): r for r in rows}
    dependency_failures = sum(
        int(str(r["policy_attempts"]))
        for r in rows
        if r["scenario"] in {"workflow_outage", "workflow_timeout"}
    )
    return {
        "rows": rows,
        "counts": {
            "PASS": sum(r["pass"] is True for r in rows),
            "FAIL": sum(r["pass"] is not True for r in rows),
        },
        "signals": {
            "dependency_failures": dependency_failures,
            "storage_failures": int(by_name["storage_projection_failure_rollback"]["pass"] is True),
            "stale_denials": int(by_name["stale_revision"]["pass"] is True),
            "outbox_dead": int(by_name["bounded_outbox_retries"]["state"] == "dead"),
            "export_failures": int(by_name["outcome_export_failure"]["export_failure"] is True),
            "telemetry_drops": healthy.sink.dropped,
            "tool_denials": int(
                by_name["mcp_three_governed_reads"]["missing_identity_status"] == 401
            ),
            "review_backlog": by_name["api_ui_current_authority"]["review_backlog_before"],
        },
    }, child_spans
