"""Real FastAPI TestClient contracts, synthetic access, idempotency and failure isolation."""

import asyncio
import io
import json
import logging
import socket
import subprocess
import sys
import threading
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from uuid import UUID, uuid4, uuid5

import httpx2
import pytest
from fastapi.openapi.models import OpenAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from pydantic import ValidationError

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.api.__main__ import NAMESPACE
from claims_ai.api.app import create_app
from claims_ai.api.auth import ApiAccess
from claims_ai.api.contracts import (
    ApiCode,
    ApiError,
    ApiLimits,
    ApiScope,
    ClaimStatus,
    ProcessRequest,
)
from claims_ai.api.fixtures import ApiFixture, demo_application
from claims_ai.api.service import ClaimsApplication
from claims_ai.human_review.__main__ import demo_decision
from claims_ai.human_review.contracts import (
    AssignmentRequest,
    InvalidationRequest,
    ReviewAction,
    ReviewBinding,
    ReviewDetail,
    ReviewEvent,
    ReviewSession,
)
from claims_ai.logging import configure_logging
from claims_ai.models import CaseState
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import Checkpoint, WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "data/rules/motor/v1"
URL = "http://127.0.0.1:8766"
type Context = tuple[ApiFixture, TestClient]


class CountRunner:
    def __init__(self, fault: str | None = None) -> None:
        self.calls = 0
        self.fault = fault
        self.runner = WorkflowRunner()

    async def run(self, request: WorkflowRequest, grant: ToolGrant) -> Checkpoint:
        self.calls += 1
        if self.fault == "unavailable":
            raise OSError("SYNTHETIC_PRIVATE_WORKFLOW_TRACE")
        result = await self.runner.run(request, grant)
        if self.fault == "forged":
            data = result.model_dump(mode="json")
            record = data["records"][-1]
            record["step"]["snapshot"]["review_task"]["reason"] = "dependency_unavailable"
            record["output_sha256"] = digest(record["step"]["snapshot"])
            record["record_sha256"] = digest(
                {k: v for k, v in record.items() if k != "record_sha256"}
            )
            return Checkpoint.model_validate(data)
        return result


def headers(
    fixture: ApiFixture,
    actor: str = "host",
    *,
    key: str | None = None,
    match: str | None = None,
    create: bool = False,
) -> dict[str, str]:
    result = {
        "Authorization": "Bearer " + fixture.tokens[actor],
        "X-Correlation-ID": str(uuid5(NAMESPACE, "api-test-correlation")),
    }
    if key is not None:
        result["Idempotency-Key"] = str(uuid5(NAMESPACE, key))
    if match is not None:
        result["If-Match"] = match
    if create:
        result["If-None-Match"] = "*"
    return result


@pytest.fixture
def context() -> Iterator[Context]:
    fixture = demo_application(SPEC_ROOT, runner=CountRunner())
    with TestClient(fixture.app, base_url=URL, client=("127.0.0.1", 50000)) as client:
        yield fixture, client


def intake(context: Context, index: int = 0) -> ClaimStatus:
    fixture, client = context
    bundle = fixture.bundles[index]
    response = client.post(
        "/api/v1/claims",
        headers=headers(fixture, key="intake-" + str(index), create=True),
        json={
            "bundle_id": bundle.bundle_id,
            "claim": bundle.request.intake.claim.model_dump(mode="json"),
        },
    )
    assert response.status_code == 201, response.text
    return ClaimStatus.model_validate(response.json())


def process(context: Context, index: int = 0) -> ClaimStatus:
    fixture, client = context
    first = intake(context, index)
    response = client.post(
        f"/api/v1/claims/{first.claim_id}/process",
        headers=headers(fixture, key="process-" + str(index), match='"1"'),
        json={
            "expected_case_revision": first.case_revision,
            "expected_case_sha256": first.case_sha256,
        },
    )
    assert response.status_code == 200, response.text
    return ClaimStatus.model_validate(response.json())


def review(context: Context, index: int = 0, actor: str = "reviewer") -> ReviewDetail:
    status = process(context, index)
    fixture, client = context
    response = client.get(
        f"/api/v1/reviews/{status.review_entry_id}", headers=headers(fixture, actor)
    )
    assert response.status_code == 200
    return ReviewDetail.model_validate(response.json())


def action(
    context: Context,
    detail: ReviewDetail,
    kind: ReviewAction = ReviewAction.APPROVE,
    actor: str = "reviewer",
    name: str = "api-action",
) -> httpx2.Response:
    fixture, client = context
    decision = demo_decision(detail.entry, kind, name)
    values = headers(fixture, actor, match=f'"{detail.entry.review_revision}"')
    values["Idempotency-Key"] = str(decision.action_id)
    return client.post(
        f"/api/v1/reviews/{detail.entry.entry_id}/actions",
        headers=values,
        json=decision.model_dump(mode="json"),
    )


def test_genuine_fastapi_processing_and_assigned_advisory_detail(context: Context) -> None:
    fixture, client = context
    detail = review(context)
    assert (
        detail.entry.recommendation_available and detail.current_case.state == CaseState.ASSESSING
    )
    advisory = client.get(
        f"/api/v1/claims/{detail.entry.binding.claim_id}/advisory",
        headers=headers(fixture, "reviewer"),
    )
    assert advisory.status_code == 200 and advisory.json()["draft"]["findings"]
    assert advisory.json()["final_outcome"] is None and not advisory.json()["settlement_authorized"]
    listed = client.get("/api/v1/reviews?limit=1&offset=0", headers=headers(fixture, "reviewer"))
    assert len(listed.json()["items"]) == 1
    assert "events" not in listed.json()["items"][0]
    assert listed.headers["cache-control"] == "no-store"


@pytest.mark.parametrize("kind", list(ReviewAction))
def test_permitted_review_actions_delegate_to_m15_without_claim_authority(
    context: Context, kind: ReviewAction
) -> None:
    fixture, client = context
    detail = review(context)
    response = action(context, detail, kind)
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["decision"]["purpose"] == "advisory_recommendation_only"
    assert (
        result["decision"]["final_outcome"] is None
        and not result["decision"]["settlement_authorized"]
    )
    current = client.get(
        f"/api/v1/claims/{detail.entry.binding.claim_id}/status", headers=headers(fixture)
    ).json()
    assert current["case_state"] == (
        "awaiting_evidence" if kind == ReviewAction.REQUEST_EVIDENCE else "assessing"
    )
    assert current["final_outcome"] is None and current["human_approval_required"]


@pytest.mark.parametrize("actor", ["agent", "mcp", "model"])
def test_nonhuman_credentials_never_reach_protected_api_operations(
    context: Context, actor: str
) -> None:
    fixture, client = context
    for path in (
        "/api/v1/reviews",
        f"/api/v1/claims/{fixture.bundles[0].request.intake.claim.claim_id}/status",
    ):
        response = client.get(path, headers=headers(fixture, actor))
        assert response.status_code == 403 and response.json()["code"] == ApiCode.DENIED


@pytest.mark.parametrize("token", [None, "forged", "eyJhbGciOiJub25lIn0.e30."])
def test_missing_invalid_or_client_asserted_credentials_are_not_identity(
    context: Context, token: str | None
) -> None:
    _, client = context
    response = client.get(
        "/api/v1/reviews", headers={} if token is None else {"Authorization": "Bearer " + token}
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"].startswith("Bearer")


def test_token_revocation_and_unregistered_human_context_block_replay(context: Context) -> None:
    fixture, client = context
    detail = review(context)
    assert action(context, detail, ReviewAction.ESCALATE).status_code == 200
    original = fixture.sessions["reviewer"]
    scope = ApiScope(principal=original.principal, claim_ids=(detail.entry.binding.claim_id,))
    forged = fixture.authenticator.issue(ApiAccess(scope, ReviewSession(original.principal)))
    response = client.get(
        f"/api/v1/reviews/{detail.entry.entry_id}", headers={"Authorization": "Bearer " + forged}
    )
    assert response.status_code == 404
    fixture.authenticator.revoke(fixture.tokens["reviewer"])
    assert action(context, detail, ReviewAction.ESCALATE).status_code == 401


def test_case_scope_is_checked_even_when_m15_assigned_the_same_human(context: Context) -> None:
    fixture, client = context
    first, second = process(context, 0), process(context, 1)
    assert fixture.backend.queue.details.get(
        fixture.sessions["reviewer"], second.review_entry_id or ""
    ).entry
    for path in (
        f"/api/v1/claims/{second.claim_id}/status",
        f"/api/v1/claims/{second.claim_id}/advisory",
        f"/api/v1/reviews/{second.review_entry_id}",
    ):
        response = client.get(path, headers=headers(fixture, "reviewer"))
        assert response.status_code == 404 and second.claim_id not in response.text
    listed = client.get("/api/v1/reviews", headers=headers(fixture, "reviewer")).json()["items"]
    assert [item["claim_id"] for item in listed] == [first.claim_id]
    assert (
        client.get(
            f"/api/v1/claims/{fixture.bundles[2].request.intake.claim.claim_id}/status",
            headers=headers(fixture),
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "kind", [ReviewAction.APPROVE, ReviewAction.REJECT, ReviewAction.REQUEST_EVIDENCE]
)
def test_supervisor_routing_cannot_be_bypassed_through_http(
    context: Context, kind: ReviewAction
) -> None:
    fixture, _ = context
    # Scope grant is host-provided and does not change the canonical M15 reviewer role.
    status = process(context, 2)
    scope = ApiScope(principal=fixture.sessions["reviewer"].principal, claim_ids=(status.claim_id,))
    fixture.tokens["reviewer"] = fixture.authenticator.issue(
        ApiAccess(scope, fixture.sessions["reviewer"])
    )
    response = context[1].get(
        f"/api/v1/reviews/{status.review_entry_id}", headers=headers(fixture, "reviewer")
    )
    detail = ReviewDetail.model_validate(response.json())
    assert detail.entry.state == "awaiting_supervisor"
    assert action(context, detail, kind).status_code == 403
    assert action(context, detail, kind, "supervisor", "supervised").status_code == 200


def test_abstained_conflicting_task_only_allows_supervisor_evidence_handling(
    context: Context,
) -> None:
    fixture, client = context
    status = process(context, 3)
    response = client.get(
        f"/api/v1/reviews/{status.review_entry_id}", headers=headers(fixture, "supervisor")
    )
    detail = ReviewDetail.model_validate(response.json())
    assert not detail.entry.recommendation_available
    assert action(context, detail, ReviewAction.APPROVE, "supervisor").status_code == 409
    assert (
        action(context, detail, ReviewAction.REQUEST_EVIDENCE, "supervisor", "evidence").status_code
        == 200
    )


def test_early_blocked_workflow_has_status_but_no_invented_review_recommendation(
    context: Context,
) -> None:
    status = process(context, 4)
    assert status.processing_phase == "needs_human_attention" and status.review_entry_id is None
    fixture, client = context
    response = client.get(f"/api/v1/claims/{status.claim_id}/advisory", headers=headers(fixture))
    assert response.status_code == 200 and response.json()["draft"] is None


def test_intake_and_processing_replays_do_not_repeat_model_work(context: Context) -> None:
    fixture, client = context
    original = intake(context)
    assert intake(context) == original
    body = {
        "expected_case_revision": original.case_revision,
        "expected_case_sha256": original.case_sha256,
    }
    path = f"/api/v1/claims/{original.claim_id}/process"
    values = headers(fixture, key="process-once", match='"1"')
    first = client.post(path, headers=values, json=body)
    second = client.post(path, headers={**values, "X-Correlation-ID": str(uuid4())}, json=body)
    assert first.status_code == second.status_code == 200 and first.content == second.content
    assert isinstance(fixture.backend.runner, CountRunner) and fixture.backend.runner.calls == 1
    changed = client.post(path, headers=values, json={**body, "expected_case_revision": 99})
    assert changed.status_code == 409


def test_review_replay_delegates_freshness_and_revocation_instead_of_http_cache(
    context: Context,
) -> None:
    fixture, _ = context
    detail = review(context)
    first, second = (
        action(context, detail, ReviewAction.ESCALATE),
        action(context, detail, ReviewAction.ESCALATE),
    )
    assert first.status_code == second.status_code == 200 and first.content == second.content
    current = fixture.backend.queue.details.get(
        fixture.sessions["reviewer"], detail.entry.entry_id
    ).entry
    fixture.backend.queue.invalidate(
        fixture.sessions["host"],
        InvalidationRequest(
            request_id=uuid4(),
            entry_id=current.entry_id,
            expected_review_revision=current.review_revision,
            replacement=ReviewBinding.model_validate(
                {**current.binding.model_dump(), "evidence_sha256": "0" * 64}
            ),
            occurred_at=demo_decision(current, ReviewAction.APPROVE, "clock").occurred_at,
            rationale="Host reports changed evidence.",
        ),
    )
    assert action(context, detail, ReviewAction.ESCALATE).status_code == 412


def test_reassignment_revokes_cached_review_action_authority(context: Context) -> None:
    fixture, _ = context
    detail = review(context)
    assert action(context, detail, ReviewAction.ESCALATE).status_code == 200
    current = fixture.backend.queue.details.get(
        fixture.sessions["reviewer"], detail.entry.entry_id
    ).entry
    fixture.backend.queue.assign(
        fixture.sessions["host"],
        AssignmentRequest(
            request_id=uuid4(),
            entry_id=current.entry_id,
            claim_id=current.binding.claim_id,
            expected_review_revision=current.review_revision,
            assignee_id=fixture.sessions["outsider"].principal.principal_id,
            occurred_at=demo_decision(current, ReviewAction.APPROVE, "clock").occurred_at,
            rationale="Host replaces reviewer.",
        ),
    )
    assert action(context, detail, ReviewAction.ESCALATE).status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("case_revision", 999),
        ("case_sha256", "0" * 64),
        ("evidence_sha256", "0" * 64),
        ("policy_version", "wrong-policy"),
        ("rule_version", "wrong-rule"),
        ("advisory_task_sha256", "0" * 64),
    ],
)
def test_review_exact_case_and_snapshot_preconditions_survive_http(
    context: Context, field: str, value: object
) -> None:
    fixture, client = context
    detail = review(context)
    decision = demo_decision(detail.entry, ReviewAction.APPROVE, "stale-binding")
    body = decision.model_dump(mode="json")
    body["expected"][field] = value
    values = headers(fixture, "reviewer", match=f'"{detail.entry.review_revision}"')
    values["Idempotency-Key"] = str(decision.action_id)
    response = client.post(
        f"/api/v1/reviews/{detail.entry.entry_id}/actions", headers=values, json=body
    )
    assert response.status_code == 412
    assert (
        fixture.backend.queue.details.get(fixture.sessions["reviewer"], detail.entry.entry_id).entry
        == detail.entry
    )


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_key",
        "wrong_match",
        "changed_duplicate",
        "missing_reason",
        "claim_outcome",
        "grant",
        "old_action",
    ],
)
def test_review_contract_rejects_bypasses_and_malformed_actions(
    context: Context, fault: str
) -> None:
    fixture, client = context
    detail = review(context)
    decision = demo_decision(detail.entry, ReviewAction.APPROVE, "bad-action")
    body = decision.model_dump(mode="json")
    values = headers(fixture, "reviewer", match=f'"{detail.entry.review_revision}"')
    values["Idempotency-Key"] = str(decision.action_id)
    expected = 422
    if fault == "wrong_key":
        values["Idempotency-Key"] = str(uuid4())
        expected = 409
    elif fault == "wrong_match":
        values["If-Match"] = '"99"'
        expected = 412
    elif fault == "changed_duplicate":
        assert action(context, detail, name="bad-action").status_code == 200
        body["rationale"] = "Changed duplicate."
        expected = 409
    elif fault == "missing_reason":
        body["rationale"] = " "
    elif fault == "claim_outcome":
        body["final_outcome"] = "eligible"
    elif fault == "grant":
        body["reviewer_id"] = str(fixture.sessions["supervisor"].principal.principal_id)
    else:
        body["action"] = "settle_claim"
    assert (
        client.post(
            f"/api/v1/reviews/{detail.entry.entry_id}/actions", headers=values, json=body
        ).status_code
        == expected
    )


@pytest.mark.parametrize("header", ["Idempotency-Key", "If-None-Match"])
def test_missing_intake_preconditions_are_explicit_428(context: Context, header: str) -> None:
    fixture, client = context
    values = headers(fixture, key="missing", create=True)
    del values[header]
    bundle = fixture.bundles[0]
    response = client.post(
        "/api/v1/claims",
        headers=values,
        json={
            "bundle_id": bundle.bundle_id,
            "claim": bundle.request.intake.claim.model_dump(mode="json"),
        },
    )
    assert response.status_code == 428 and response.json()["code"] == ApiCode.REQUIRED


@pytest.mark.parametrize("header", ["Idempotency-Key", "If-Match"])
def test_missing_processing_preconditions_are_explicit_428(context: Context, header: str) -> None:
    fixture, client = context
    first = intake(context)
    values = headers(fixture, key="missing", match='"1"')
    del values[header]
    response = client.post(
        f"/api/v1/claims/{first.claim_id}/process",
        headers=values,
        json={"expected_case_revision": 1, "expected_case_sha256": first.case_sha256},
    )
    assert response.status_code == 428


@pytest.mark.parametrize(
    "changes", [{"documents": []}, {"grant": {}}, {"policy": {}}, {"synthetic": False}]
)
def test_intake_cannot_supply_trusted_scan_policy_or_authorization_assertions(
    context: Context, changes: dict[str, object]
) -> None:
    fixture, client = context
    bundle = fixture.bundles[0]
    body = {
        "bundle_id": bundle.bundle_id,
        "claim": bundle.request.intake.claim.model_dump(mode="json"),
        **changes,
    }
    assert (
        client.post(
            "/api/v1/claims", headers=headers(fixture, key="invalid", create=True), json=body
        ).status_code
        == 422
    )


@pytest.mark.parametrize(
    "fault,expected",
    [
        ("json", 400),
        ("batch", 400),
        ("duplicate", 400),
        ("nan", 400),
        ("media", 415),
        ("compression", 415),
        ("size", 413),
        ("misleading_length", 413),
        ("utf8", 400),
    ],
)
def test_actual_body_validation_and_sanitized_errors(
    context: Context, fault: str, expected: int
) -> None:
    fixture, client = context
    values = {**headers(fixture, key="body", create=True), "Content-Type": "application/json"}
    body = {
        "json": b'{"PRIVATE_SECRET":',
        "batch": b"[]",
        "duplicate": b'{"a":1,"a":2}',
        "nan": b'{"a":NaN}',
        "media": b"{}",
        "compression": b"{}",
        "size": b"x" * 16385,
        "misleading_length": b"x" * 16385,
        "utf8": b"\xff",
    }[fault]
    if fault == "media":
        values["Content-Type"] = "text/plain"
    if fault == "compression":
        values["Content-Encoding"] = "gzip"
    if fault == "misleading_length":
        values["Content-Length"] = "1"
    response = client.post("/api/v1/claims", headers=values, content=body)
    assert response.status_code == expected and "PRIVATE_SECRET" not in response.text
    assert "detail" not in response.json() and "Traceback" not in response.text
    assert UUID(response.headers["X-Correlation-ID"]) == UUID(
        response.json()["request_correlation_id"]
    )


@pytest.mark.parametrize(
    "extra",
    [
        {"Host": "evil.invalid"},
        {"Origin": "https://evil.invalid"},
        {"Forwarded": "for=127.0.0.1"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Role": "supervisor"},
        {"X-Claims-Grant": "trusted"},
    ],
)
def test_host_origin_proxy_and_identity_spoofing_is_rejected(
    context: Context, extra: dict[str, str]
) -> None:
    fixture, client = context
    assert (
        client.get("/api/v1/reviews", headers={**headers(fixture, "reviewer"), **extra}).status_code
        == 403
    )


def test_duplicate_credentials_query_credentials_and_bad_correlation_are_rejected(
    context: Context,
) -> None:
    fixture, client = context
    values = [("Authorization", "Bearer " + fixture.tokens["reviewer"])] * 2
    assert client.get("/api/v1/reviews", headers=values).status_code == 400
    claim_id = fixture.bundles[0].request.intake.claim.claim_id
    assert (
        client.get(
            f"/api/v1/claims/{claim_id}/status?token=forged", headers=headers(fixture)
        ).status_code
        == 400
    )
    assert (
        client.get(
            "/api/v1/reviews",
            headers={**headers(fixture, "reviewer"), "X-Correlation-ID": "PRIVATE_SECRET"},
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "query", ["limit=17", "offset=65", "limit=not-an-int", "actor=supervisor", "limit=1&limit=2"]
)
def test_queue_queries_are_bounded_and_cannot_select_actor_or_case(
    context: Context, query: str
) -> None:
    fixture, client = context
    response = client.get("/api/v1/reviews?" + query, headers=headers(fixture, "reviewer"))
    assert response.status_code in {400, 422}


def test_health_readiness_and_default_deny_do_not_claim_azure_or_prestartup_readiness() -> None:
    app = create_app()
    with TestClient(app, base_url=URL, client=("127.0.0.1", 1)) as client:
        assert client.get("/health/live").json()["status"] == "alive"
        ready = client.get("/health/ready")
        assert ready.status_code == 503 and not ready.json()["local_application_ready"]
        assert (
            not ready.json()["external_azure_ready"]
            and ready.json()["azure_dependencies"] == "NOT_CONFIGURED_NOT_PROBED"
        )
        assert client.get("/api/v1/reviews").status_code == 401
    fixture = demo_application(SPEC_ROOT, fixtures=("valid-v1",))
    client = TestClient(fixture.app, base_url=URL, client=("127.0.0.1", 1))
    assert client.get("/health/ready").status_code == 503
    with client:
        assert client.get("/health/ready").status_code == 200
        fixture.backend.available = False
        assert client.get("/health/ready").status_code == 503
    fixture.backend.available = True
    with TestClient(create_app(fixture.backend), base_url=URL, client=("127.0.0.1", 1)) as denied:
        ready = denied.get("/health/ready")
        assert ready.status_code == 503 and ready.json()["services_configured"]
        assert (
            ready.json()["workflow_available"]
            and not ready.json()["synthetic_authenticator_configured"]
        )


@pytest.mark.parametrize("field,value", [("state", CaseState.ASSESSING), ("revision", 2)])
def test_host_registry_cannot_intake_an_advanced_case_as_a_fresh_claim(
    field: str, value: object
) -> None:
    fixture = demo_application(SPEC_ROOT, fixtures=("valid-v1",))
    bundle = fixture.bundles[0]
    case = type(bundle.request.intake).model_validate(
        {**bundle.request.intake.model_dump(), field: value}
    )
    changed = replace(bundle, request=bundle.request.model_copy(update={"intake": case}))
    with pytest.raises(ValueError, match="received revision"):
        ClaimsApplication((changed,), fixture.backend.queue, fixture.sessions["host"])


def test_public_peer_or_wrong_server_scope_is_denied_without_network() -> None:
    fixture = demo_application(SPEC_ROOT, fixtures=("valid-v1",))
    with TestClient(fixture.app, base_url=URL, client=("203.0.113.1", 1)) as client:
        assert client.get("/health/live").status_code == 403
    with TestClient(
        fixture.app, base_url="http://127.0.0.1:9999", client=("127.0.0.1", 1)
    ) as client:
        assert client.get("/health/live").status_code == 403


@pytest.mark.parametrize("fault", ["unavailable", "forged"])
def test_failed_workflow_is_sanitized_and_cannot_be_reexecuted_by_replay(fault: str) -> None:
    runner = CountRunner(fault)
    fixture = demo_application(SPEC_ROOT, runner=runner, fixtures=("valid-v1",))
    with TestClient(fixture.app, base_url=URL, client=("127.0.0.1", 1)) as client:
        first = intake((fixture, client))
        path = f"/api/v1/claims/{first.claim_id}/process"
        values = headers(fixture, key="failure", match='"1"')
        body = {"expected_case_revision": 1, "expected_case_sha256": first.case_sha256}
        for _ in range(2):
            response = client.post(path, headers=values, json=body)
            assert response.status_code == 503 and "SYNTHETIC_PRIVATE" not in response.text
        assert runner.calls == 1
        assert (
            client.get("/api/v1/reviews", headers=headers(fixture, "reviewer")).json()["items"]
            == []
        )
        status = client.get(
            f"/api/v1/claims/{first.claim_id}/status", headers=headers(fixture)
        ).json()
        assert (
            status["processing_phase"] == "application_processing_failed"
            and status["final_outcome"] is None
        )


def test_partial_host_assignment_failure_never_publishes_the_review(
    context: Context, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, client = context
    original = fixture.backend.queue.assign
    count = 0

    def assign(host: ReviewSession, request: AssignmentRequest) -> ReviewEvent:
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("PRIVATE_ASSIGNMENT_TRACE")
        return original(host, request)

    monkeypatch.setattr(fixture.backend.queue, "assign", assign)
    first = intake(context)
    response = client.post(
        f"/api/v1/claims/{first.claim_id}/process",
        headers=headers(fixture, key="partial", match='"1"'),
        json={"expected_case_revision": 1, "expected_case_sha256": first.case_sha256},
    )
    assert response.status_code == 503
    assert len(fixture.backend.queue.details.list(fixture.sessions["reviewer"])) == 1
    assert client.get("/api/v1/reviews", headers=headers(fixture, "reviewer")).json()["items"] == []


def test_invalid_host_workflow_grant_is_rejected_before_workflow_invocation(
    context: Context,
) -> None:
    fixture, client = context
    first = intake(context)
    record = fixture.backend._records[first.claim_id]
    wrong = ToolGrant.model_validate(
        {**record.bundle.grant.model_dump(), "claim_id": "NS-CLM-00000000"}
    )
    fixture.backend._records[first.claim_id] = replace(
        record, bundle=replace(record.bundle, grant=wrong)
    )
    response = client.post(
        f"/api/v1/claims/{first.claim_id}/process",
        headers=headers(fixture, key="bad-grant", match='"1"'),
        json={"expected_case_revision": 1, "expected_case_sha256": first.case_sha256},
    )
    assert response.status_code == 403
    assert isinstance(fixture.backend.runner, CountRunner) and fixture.backend.runner.calls == 0


def test_concurrent_processing_duplicates_execute_one_real_workflow(context: Context) -> None:
    fixture, client = context
    first = intake(context)

    def call(_: int) -> httpx2.Response:
        return client.post(
            f"/api/v1/claims/{first.claim_id}/process",
            headers=headers(fixture, key="concurrent-process", match='"1"'),
            json={"expected_case_revision": 1, "expected_case_sha256": first.case_sha256},
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(call, range(2)))
    assert [r.status_code for r in responses] == [200, 200] and responses[0].content == responses[
        1
    ].content
    assert isinstance(fixture.backend.runner, CountRunner) and fixture.backend.runner.calls == 1


def test_concurrent_incompatible_http_review_actions_have_one_winner(context: Context) -> None:
    detail = review(context)
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(
            pool.map(
                lambda kind: action(context, detail, kind, name=kind.value),
                [ReviewAction.APPROVE, ReviewAction.REJECT],
            )
        )
    assert sorted(r.status_code for r in responses) == [200, 409]


def test_slow_body_is_bounded_before_fastapi_parses_it() -> None:
    fixture = demo_application(
        SPEC_ROOT, limits=ApiLimits(body_timeout_seconds=0.01), fixtures=("valid-v1",)
    )

    async def run() -> None:
        async def slow() -> AsyncIterator[bytes]:
            yield b"{"
            await asyncio.Event().wait()

        async with fixture.app.router.lifespan_context(fixture.app):
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=fixture.app), base_url=URL, trust_env=False
            ) as client:
                response = await client.post(
                    "/api/v1/claims",
                    headers={**headers(fixture), "Content-Type": "application/json"},
                    content=slow(),
                )
                assert response.status_code == 408

    asyncio.run(run())


def test_request_concurrency_and_response_capacity_are_bounded() -> None:
    class Gate(CountRunner):
        def __init__(self) -> None:
            super().__init__()
            self.started = threading.Event()
            self.release = threading.Event()

        async def run(self, request: WorkflowRequest, grant: ToolGrant) -> Checkpoint:
            self.started.set()
            await asyncio.to_thread(self.release.wait, 10)
            return await super().run(request, grant)

    runner = Gate()
    fixture = demo_application(
        SPEC_ROOT, runner=runner, limits=ApiLimits(max_inflight=1), fixtures=("valid-v1",)
    )
    with TestClient(fixture.app, base_url=URL, client=("127.0.0.1", 1)) as client:
        first = intake((fixture, client))

        def call() -> httpx2.Response:
            return client.post(
                f"/api/v1/claims/{first.claim_id}/process",
                headers=headers(fixture, key="gate", match='"1"'),
                json={"expected_case_revision": 1, "expected_case_sha256": first.case_sha256},
            )

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(call)
            assert runner.started.wait(10)
            try:
                response = client.get(
                    f"/api/v1/claims/{first.claim_id}/status", headers=headers(fixture)
                )
                assert response.status_code == 429 and response.headers["Retry-After"] == "1"
            finally:
                runner.release.set()
            assert pending.result(timeout=20).status_code == 200
    limited = demo_application(
        SPEC_ROOT, limits=ApiLimits(max_response_bytes=65536), fixtures=("valid-v1",)
    )
    with TestClient(limited.app, base_url=URL, client=("127.0.0.1", 1)) as client:
        status = process((limited, client))
        response = client.get(
            f"/api/v1/reviews/{status.review_entry_id}", headers=headers(limited, "reviewer")
        )
        assert response.status_code == 503 and response.json()["code"] == ApiCode.RESPONSE


def test_receipt_capacity_fails_without_invoking_workflow_or_changing_case() -> None:
    runner = CountRunner()
    fixture = demo_application(
        SPEC_ROOT,
        runner=runner,
        limits=ApiLimits(max_receipts=2),
        fixtures=("valid-v1", "valid-v2"),
    )
    with TestClient(fixture.app, base_url=URL, client=("127.0.0.1", 1)) as client:
        first = intake((fixture, client))
        intake((fixture, client), 1)
        response = client.post(
            f"/api/v1/claims/{first.claim_id}/process",
            headers=headers(fixture, key="capacity", match='"1"'),
            json={"expected_case_revision": 1, "expected_case_sha256": first.case_sha256},
        )
        assert response.status_code == 503 and runner.calls == 0
        assert (
            client.get(f"/api/v1/claims/{first.claim_id}/status", headers=headers(fixture)).json()[
                "application_revision"
            ]
            == 1
        )


def test_human_cannot_create_processing_grants_and_genuine_api_tests_open_no_socket(
    context: Context, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture, _ = context
    with pytest.raises(ValidationError):
        ApiScope(principal=fixture.sessions["reviewer"].principal, claim_ids=(), can_process=True)

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline FastAPI evidence must not open sockets or call Azure")

    monkeypatch.setattr(socket.socket, "bind", forbidden)
    monkeypatch.setattr(socket.socket, "connect", forbidden)
    assert process(context).final_outcome is None


def test_cancelled_processing_keeps_a_failure_tombstone_instead_of_restarting() -> None:
    class Blocking:
        def __init__(self) -> None:
            self.calls = 0
            self.started = asyncio.Event()

        async def run(self, request: WorkflowRequest, grant: ToolGrant) -> Checkpoint:
            self.calls += 1
            self.started.set()
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    runner = Blocking()
    fixture = demo_application(SPEC_ROOT, runner=runner, fixtures=("valid-v1",))
    access = fixture.authenticator.verify(fixture.tokens["host"])
    assert access is not None

    async def run() -> None:
        from claims_ai.api.contracts import IntakeRequest

        bundle = fixture.bundles[0]
        first = await fixture.backend.intake(
            access,
            IntakeRequest(bundle_id=bundle.bundle_id, claim=bundle.request.intake.claim),
            uuid4(),
        )
        request = ProcessRequest(expected_case_revision=1, expected_case_sha256=first.case_sha256)
        key = uuid4()
        task = asyncio.create_task(fixture.backend.process(access, first.claim_id, request, key, 1))
        await runner.started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        with pytest.raises(ApiError) as error:
            await fixture.backend.process(access, first.claim_id, request, key, 1)
        assert error.value.status == 503 and runner.calls == 1
        assert (
            fixture.backend.status(access, first.claim_id).processing_phase
            == "application_processing_failed"
        )

    asyncio.run(run())


def test_redacted_structured_api_logs_never_include_credentials_payloads_or_errors(
    context: Context,
) -> None:
    fixture, client = context
    logger = logging.getLogger("claims_ai")
    previous = (logger.handlers[:], logger.level, logger.propagate)
    stream = io.StringIO()
    try:
        configure_logging(stream=stream)
        response = client.post(
            "/api/v1/claims",
            headers={
                **headers(fixture, key="logs", create=True),
                "Content-Type": "application/json",
            },
            content=b'{"PRIVATE_NARRATIVE":',
        )
        assert response.status_code == 400
        rows = [json.loads(line) for line in stream.getvalue().splitlines()]
        assert (
            rows
            and rows[-1]["event"] == "api_request"
            and rows[-1]["fields"]["status"] == "invalid"
        )
        assert rows[-1]["correlation_id"] == response.headers["X-Correlation-ID"]
        assert (
            "PRIVATE_NARRATIVE" not in stream.getvalue()
            and fixture.tokens["host"] not in stream.getvalue()
        )
    finally:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
        logger.handlers = previous[0]
        logger.setLevel(previous[1])
        logger.propagate = previous[2]


def test_openapi_models_security_headers_references_and_actual_response_contracts(
    context: Context,
) -> None:
    fixture, client = context
    specification = client.get("/openapi.json").json()
    wrong_method = client.put("/api/v1/claims", headers=headers(fixture))
    assert wrong_method.status_code == 405 and wrong_method.headers["Allow"] == "POST"
    OpenAPI.model_validate(specification)
    assert specification["openapi"] == "3.1.0"
    assert len(specification["paths"]) == 9
    for path, operations in specification["paths"].items():
        for method, operation in operations.items():
            if not path.startswith("/api/v1"):
                continue
            assert operation["security"] == [{"SyntheticHostBearer": []}]
            if method == "post":
                required = {p["name"] for p in operation.get("parameters", []) if p["required"]}
                assert "Idempotency-Key" in required and (
                    "If-Match" in required or "If-None-Match" in required
                )
    schemas = specification["components"]["schemas"]
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    assert not {"ApiAccess", "HostBundle", "ReviewSession", "ToolGrant"} & set(schemas)
    assert schemas["ReviewDecision"]["properties"]["final_outcome"]["type"] == "null"
    assert schemas["ReviewAction"]["enum"] == [k.value for k in ReviewAction]
    status = intake(context)
    response = client.get(f"/api/v1/claims/{status.claim_id}/status", headers=headers(fixture))
    contract = specification["paths"]["/api/v1/claims/{claim_id}/status"]["get"]["responses"][
        "200"
    ]["content"]["application/json"]["schema"]
    Draft202012Validator({**contract, "components": specification["components"]}).validate(
        response.json()
    )
    text = json.dumps(specification)
    assert all(token not in text for token in fixture.tokens.values())


@pytest.mark.parametrize(
    "path", ["/api/v1/claims/approve", "/api/v1/payments", "/api/v1/assignments", "/api/v1/tokens"]
)
def test_no_claim_outcome_assignment_or_credential_issuance_endpoint_exists(
    context: Context, path: str
) -> None:
    fixture, client = context
    response = client.post(path, headers=headers(fixture, key="forbidden"), json={})
    assert response.status_code == 404


def test_api_evidence_reproduces_from_other_cwd_without_socket_or_reference_changes(
    tmp_path: Path,
) -> None:
    import claims_ai

    assert claims_ai.__file__ is not None
    package_root = str(Path(claims_ai.__file__).resolve().parents[1])
    bootstrap = (
        "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.api',run_name='__main__')"
    )
    command = [
        sys.executable,
        "-I",
        "-B",
        "-c",
        bootstrap,
        package_root,
        "--spec-root",
        str(SPEC_ROOT),
    ]
    reports = [tmp_path / "a.json", tmp_path / "b.json"]
    specs = [tmp_path / "a-openapi.json", tmp_path / "b-openapi.json"]
    for report, spec in zip(reports, specs, strict=True):
        subprocess.run(
            [*command, "--output", str(report), "--openapi-output", str(spec)],
            cwd=tmp_path,
            check=True,
            capture_output=True,
            timeout=30,
        )
    assert (
        reports[0].read_bytes() == reports[1].read_bytes()
        and specs[0].read_bytes() == specs[1].read_bytes()
    )
    data = json.loads(reports[0].read_bytes())
    assert data["azure_operations"] == data["live_model_calls"] == data["autonomous_outcomes"] == 0
    assert data["execution_surface"] == "FASTAPI_TESTCLIENT_ASGI_NOT_TCP"
    assert not data["insurance_outcome_authority"]
    result = subprocess.run(
        [
            *command,
            "--output",
            str(SPEC_ROOT / "m16-must-not-write.json"),
            "--openapi-output",
            str(tmp_path / "unused.json"),
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 1 and not (SPEC_ROOT / "m16-must-not-write.json").exists()
