"""Real UI/M16 contracts plus bounded-session and hostile-browser regression cases."""

import asyncio
import subprocess
import sys
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import timedelta
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx2
import pytest
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from claims_ai.api.fixtures import ApiFixture, demo_application
from claims_ai.human_review.__main__ import NOW
from claims_ai.human_review.contracts import InvalidationRequest, ReviewBinding, ReviewState
from claims_ai.reviewer_ui import views
from claims_ai.reviewer_ui.__main__ import (
    ORIGIN,
    FormInputs,
    action_fields,
    demonstrate,
    enroll,
    snapshot,
)
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.boundary import COOKIE, BrowserBoundary
from claims_ai.reviewer_ui.client import ApiClient, CaseView, UiError
from claims_ai.reviewer_ui.host import seed
from claims_ai.reviewer_ui.sessions import Profile, Sessions

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data/rules/motor/v1"


@dataclass
class Environment:
    fixture: ApiFixture
    api: ApiClient
    transport: TestClient


@contextmanager
def environment(fixtures: tuple[str, ...]) -> Iterator[Environment]:
    fixture = demo_application(SPEC, fixtures=fixtures)
    with TestClient(
        fixture.app, base_url="http://127.0.0.1:8766", client=("127.0.0.1", 51000)
    ) as transport:
        seed(transport, fixture)
        yield Environment(fixture, ApiClient(transport), transport)


@pytest.fixture(scope="module")
def readonly() -> Iterator[Environment]:
    with environment(("valid-v1", "valid-v2", "conflicting-amounts")) as value:
        yield value


@pytest.fixture
def mutable() -> Iterator[Environment]:
    with environment(("valid-v1", "conflicting-amounts")) as value:
        yield value


@contextmanager
def browser(
    env: Environment, actor: str = "reviewer", *, sessions: Sessions | None = None
) -> Iterator[tuple[TestClient, Sessions]]:
    registry = sessions or Sessions(clock=lambda: NOW + timedelta(seconds=10))
    code = registry.provision(Profile("Synthetic " + actor, env.fixture.tokens[actor]))
    with TestClient(
        create_ui(env.api, registry), base_url=ORIGIN, client=("127.0.0.1", 52000)
    ) as client:
        enroll(client, code)
        yield client, registry


def entry(env: Environment, actor: str = "reviewer") -> str:
    return env.api.queue(env.fixture.tokens[actor]).items[0].entry_id


def post(client: TestClient, path: str, fields: dict[str, str]) -> httpx2.Response:
    return client.post(path, data=fields, headers={"Origin": ORIGIN})


def test_dashboard_uses_actual_assigned_api_queue(readonly: Environment) -> None:
    with browser(readonly) as (client, _):
        response = client.get("/")
        assert response.status_code == 200
        assert readonly.fixture.bundles[0].request.intake.claim.claim_id in response.text
        assert readonly.fixture.bundles[1].request.intake.claim.claim_id not in response.text
        assert "Pending human action" in response.text
        assert "simulated identity" in response.text
        assert "does not approve an insurance claim" in response.text
        assert "case / review revision" in response.text.lower()


def test_case_detail_contains_all_source_linked_sections(readonly: Environment) -> None:
    with browser(readonly) as (client, _):
        response = client.get("/reviews/" + entry(readonly))
        assert response.status_code == 200
        for heading in (
            "Evidence and provenance",
            "Retrieved policy citations",
            "Provisional rule findings",
            "Agent advisory",
            "Uncertainty and trust",
            "Snapshot and audit trace",
        ):
            assert heading in response.text
        assert "unapproved fixtures" in response.text
        assert "uncalibrated" in response.text
        assert "NS-EVD-" in response.text and "NS-DOC-" in response.text
        assert 'name="expected"' not in response.text
        assert 'name="role"' not in response.text
        assert 'name="case_revision"' not in response.text
        assert readonly.fixture.tokens["reviewer"] not in response.text


def test_supervisor_queue_and_missing_recommendation(readonly: Environment) -> None:
    with browser(readonly, "supervisor") as (client, _):
        assert all(
            b.request.intake.claim.claim_id in client.get("/").text
            for b in readonly.fixture.bundles
        )
        missing = next(
            item
            for item in readonly.api.queue(readonly.fixture.tokens["supervisor"]).items
            if not item.recommendation_available
        )
        response = client.get("/reviews/" + missing.entry_id)
        assert response.status_code == 200
        assert "No advisory recommendation is available" in response.text
        assert "Supervisor evidence triage only" in response.text


@pytest.mark.parametrize("actor", ["host", "agent", "mcp", "model", "outsider"])
def test_host_misdelivered_nonreviewer_capability_fails_api(
    readonly: Environment, actor: str
) -> None:
    with browser(readonly, actor) as (client, _):
        response = client.get("/")
        assert response.status_code == (200 if actor == "outsider" else 403)
        if actor == "outsider":
            assert "No assigned reviews" in response.text
        detail = client.get("/reviews/" + entry(readonly))
        assert detail.status_code in {403, 404}
        assert "Evidence and provenance" not in detail.text


def test_unknown_and_cross_case_have_same_safe_result(readonly: Environment) -> None:
    other_claim = readonly.fixture.bundles[1].request.intake.claim.claim_id
    other = next(
        item.entry_id
        for item in readonly.api.queue(readonly.fixture.tokens["supervisor"]).items
        if item.claim_id == other_claim
    )
    with browser(readonly) as (client, _):
        unknown, cross = client.get("/reviews/" + "f" * 64), client.get("/reviews/" + other)
        assert unknown.status_code == cross.status_code == 404
        assert unknown.text == cross.text
        assert "NS-CLM-" not in cross.text


@pytest.mark.parametrize(
    "action,state",
    [
        ("approve_recommendation", ReviewState.APPROVED),
        ("reject_recommendation", ReviewState.REJECTED),
        ("request_additional_evidence", ReviewState.EVIDENCE),
        ("escalate_to_supervisor", ReviewState.SUPERVISOR),
    ],
)
def test_explicit_actions_preserve_binding_and_never_create_outcome(
    mutable: Environment, action: str, state: ReviewState
) -> None:
    identifier = entry(mutable)
    old = mutable.api.view(mutable.fixture.tokens["reviewer"], identifier).detail.entry
    with browser(mutable) as (client, registry):
        path = "/reviews/" + identifier
        fields = action_fields(client.get(path).text, action)
        if action == "request_additional_evidence":
            fields["requested_evidence"] = "repair_estimate"
        response = post(client, path + "/actions", fields)
        assert response.status_code == 200
        assert "Recommendation action recorded" in response.text
        session = registry.get(client.cookies.get(COOKIE) or "")
        decision = session.forms[fields["ticket"]].decision
        assert decision is not None
        assert decision.expected == old.binding
        assert decision.expected_review_revision == old.review_revision
        assert decision.evidence == old.evidence[:1]
        updated = mutable.api.view(mutable.fixture.tokens["reviewer"], identifier)
        assert updated.detail.entry.state == state
        assert updated.detail.entry.events[-1].decision == decision
        assert updated.detail.current_case.decision is None
        assert updated.detail.current_case.assessment is None
        assert updated.status.final_outcome is None
        assert not updated.status.settlement_authorized


def test_exact_replay_rechecks_api_and_changed_replay_conflicts(mutable: Environment) -> None:
    path = "/reviews/" + entry(mutable)
    with browser(mutable) as (client, _):
        fields = action_fields(client.get(path).text, "approve_recommendation")
        first = post(client, path + "/actions", fields)
        assert first.status_code == 200
        assert post(client, path + "/actions", fields).text == first.text
        changed = {**fields, "rationale": "Changed replay must not reuse a receipt."}
        assert post(client, path + "/actions", changed).status_code == 409
        mutable.fixture.authenticator.revoke(mutable.fixture.tokens["reviewer"])
        revoked = post(client, path + "/actions", fields)
        assert revoked.status_code == 401
        assert "recorded" not in revoked.text


def test_supervisor_cannot_be_bypassed_by_visible_controls(mutable: Environment) -> None:
    path = "/reviews/" + entry(mutable)
    with browser(mutable) as (client, _):
        fields = action_fields(client.get(path).text, "escalate_to_supervisor")
        assert post(client, path + "/actions", fields).status_code == 200
        escalated = client.get(path)
        assert "Required reviewer: <strong>Supervisor</strong>" in escalated.text
        assert "<td>Supervisor</td>" in client.get("/").text
        unauthorized = action_fields(escalated.text, "approve_recommendation")
        assert post(client, path + "/actions", unauthorized).status_code == 403
    with browser(mutable, "supervisor") as (client, _):
        authorized = action_fields(client.get(path).text, "approve_recommendation")
        assert post(client, path + "/actions", authorized).status_code == 200


def test_missing_recommendation_approval_denied_by_api(mutable: Environment) -> None:
    item = next(
        item
        for item in mutable.api.queue(mutable.fixture.tokens["supervisor"]).items
        if not item.recommendation_available
    )
    with browser(mutable, "supervisor") as (client, _):
        path = "/reviews/" + item.entry_id
        fields = action_fields(client.get(path).text, "approve_recommendation")
        assert post(client, path + "/actions", fields).status_code == 409
        assert (
            mutable.api.view(mutable.fixture.tokens["supervisor"], item.entry_id).detail.entry.state
            == ReviewState.SUPERVISOR
        )


def test_competing_tabs_keep_original_revision_and_one_winner(mutable: Environment) -> None:
    path = "/reviews/" + entry(mutable)
    with browser(mutable) as (client, _):
        old = action_fields(client.get(path).text, "reject_recommendation")
        new = action_fields(client.get(path).text, "approve_recommendation")
        assert post(client, path + "/actions", new).status_code == 200
        response = post(client, path + "/actions", old)
        assert response.status_code == 409
        assert "Reload and inspect" in response.text
        assert "Recommendation action recorded" not in response.text


def test_stale_evidence_and_old_duplicate_fail_closed(mutable: Environment) -> None:
    identifier = entry(mutable)
    with browser(mutable) as (client, _):
        path = "/reviews/" + identifier
        fields = action_fields(client.get(path).text, "approve_recommendation")
        old = mutable.api.view(mutable.fixture.tokens["reviewer"], identifier).detail.entry
        mutable.fixture.backend.queue.invalidate(
            mutable.fixture.sessions["host"],
            InvalidationRequest(
                request_id=uuid4(),
                entry_id=identifier,
                expected_review_revision=old.review_revision,
                replacement=ReviewBinding.model_validate(
                    {**old.binding.model_dump(), "evidence_sha256": "f" * 64}
                ),
                occurred_at=NOW + timedelta(seconds=10),
                rationale="Synthetic host announces replacement evidence.",
            ),
        )
        assert post(client, path + "/actions", fields).status_code == 412
        assert "Review snapshot changed" in post(client, path + "/actions", fields).text


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-rationale",
        "unknown-evidence",
        "missing-evidence",
        "missing-document-kind",
        "wrong-document-kind",
        "forged-role",
        "forged-revision",
        "forged-grant",
        "wrong-ticket",
        "csrf",
    ],
)
def test_malformed_or_forged_action_is_not_recorded(readonly: Environment, mutation: str) -> None:
    identifier = entry(readonly)
    before = readonly.api.view(readonly.fixture.tokens["reviewer"], identifier).detail.entry
    with browser(readonly) as (client, _):
        path = "/reviews/" + identifier
        fields = action_fields(client.get(path).text, "approve_recommendation")
        if mutation == "missing-rationale":
            fields["rationale"] = " "
        elif mutation == "unknown-evidence":
            fields["evidence"] = "NS-EVD-FFFFFFFF"
        elif mutation == "missing-evidence":
            fields.pop("evidence")
        elif mutation == "missing-document-kind":
            fields["action"] = "request_additional_evidence"
        elif mutation == "wrong-document-kind":
            fields["requested_evidence"] = "arbitrary"
        elif mutation == "forged-role":
            fields["role"] = "supervisor"
        elif mutation == "forged-revision":
            fields["case_revision"] = "999"
        elif mutation == "forged-grant":
            fields["grant"] = "arbitrary"
        elif mutation == "wrong-ticket":
            fields["ticket"] = str(uuid4())
        else:
            fields["csrf"] = "forged"
        response = post(client, path + "/actions", fields)
        assert response.status_code in {403, 412, 422}
        assert "Recommendation action recorded" not in response.text
        assert (
            readonly.api.view(readonly.fixture.tokens["reviewer"], identifier).detail.entry
            == before
        )


@pytest.mark.parametrize(
    "headers,content,status",
    [
        ({"Origin": "https://evil.example"}, "csrf=x", 403),
        ({}, "csrf=x", 403),
        ({"Origin": ORIGIN, "Content-Type": "application/json"}, "{}", 415),
        (
            {
                "Origin": ORIGIN,
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Encoding": "gzip",
            },
            "csrf=x",
            415,
        ),
        (
            {"Origin": ORIGIN, "Content-Type": "application/x-www-form-urlencoded"},
            "x=" + "a" * 8192,
            413,
        ),
        (
            {"Origin": ORIGIN, "Content-Type": "application/x-www-form-urlencoded"},
            "csrf=a&csrf=b",
            422,
        ),
        ({"Origin": ORIGIN, "Content-Type": "application/x-www-form-urlencoded"}, "x=%ff", 422),
    ],
)
def test_browser_form_origin_media_and_actual_byte_guards(
    readonly: Environment, headers: dict[str, str], content: str, status: int
) -> None:
    with browser(readonly) as (client, _):
        response = client.post("/logout", headers=headers, content=content)
        assert response.status_code == status


@pytest.mark.parametrize(
    "headers",
    [
        {"Host": "evil.example"},
        {"Origin": "null"},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Role": "supervisor"},
        {"Authorization": "Bearer browser-injected"},
    ],
)
def test_host_and_spoofed_identity_headers_rejected(
    readonly: Environment, headers: dict[str, str]
) -> None:
    with browser(readonly) as (client, _):
        assert client.get("/", headers=headers).status_code == 403


def test_no_query_credentials_no_extra_ui_api_no_downloads(readonly: Environment) -> None:
    with browser(readonly) as (client, _):
        assert client.get("/?role=supervisor").status_code == 403
        assert client.get("/openapi.json").status_code == 404
        assert client.get("/api/v1/claims").status_code == 404
        assert client.get("/reviews/../../etc/passwd").status_code == 404
        assert client.get("/queue/17").status_code == 400


def test_session_rotation_expiry_logout_and_cookie_controls(readonly: Environment) -> None:
    now = [0.0]
    sessions = Sessions(timer=lambda: now[0], clock=lambda: NOW + timedelta(seconds=10))
    code = sessions.provision(Profile("Synthetic reviewer", readonly.fixture.tokens["reviewer"]))
    with TestClient(
        create_ui(readonly.api, sessions), base_url=ORIGIN, client=("127.0.0.1", 52000)
    ) as client:
        login = client.get("/login")
        old = client.cookies.get(COOKIE)
        assert (
            "HttpOnly" in login.headers["set-cookie"]
            and "SameSite=strict" in login.headers["set-cookie"]
        )
        fields = FormInputs(login.text).values
        response = post(client, "/login", {"csrf": fields["csrf"], "code": code})
        assert response.status_code == 200 and client.cookies.get(COOKIE) != old
        with pytest.raises(UiError):
            sessions.get(old or "")
        now[0] = 901
        expired = client.get("/")
        assert expired.status_code == 401 and "expired or was revoked" in expired.text
        assert client.cookies.get(COOKIE) is None
    with browser(readonly) as (client, _):
        csrf = FormInputs(client.get("/").text).values["csrf"]
        assert post(client, "/logout", {"csrf": csrf}).status_code == 200
        assert client.get("/").status_code == 401


def test_one_use_code_expiry_capacity_and_attempt_limit() -> None:
    now = [0.0]
    sessions = Sessions(timer=lambda: now[0], clock=lambda: NOW)
    profile = Profile("Synthetic reviewer", "SECRET-API-TOKEN")
    code = sessions.provision(profile)
    cookie, anon = sessions.anonymous()
    rotated, _ = sessions.login(cookie, anon.csrf, code)
    other, second = sessions.anonymous()
    with pytest.raises(UiError):
        sessions.login(other, second.csrf, code)
    assert "SECRET-API-TOKEN" not in repr(profile)
    sessions.get(rotated)
    expiring = sessions.provision(profile)
    now[0] = 301
    fresh, anon = sessions.anonymous()
    with pytest.raises(UiError):
        sessions.login(fresh, anon.csrf, expiring)
    for _ in range(20):
        try:
            sessions.login(fresh, anon.csrf, "invalid")
        except UiError:
            pass
    with pytest.raises(UiError) as failure:
        sessions.login(fresh, anon.csrf, sessions.provision(profile))
    assert failure.value.status == 429
    bounded = Sessions(clock=lambda: NOW)
    for _ in range(8):
        bounded.anonymous()
    with pytest.raises(UiError) as failure:
        bounded.anonymous()
    assert failure.value.status == 429
    for _ in range(8):
        bounded.provision(profile)
    with pytest.raises(UiError):
        bounded.provision(profile)


def test_view_tickets_are_bounded_and_evicted_actions_cannot_submit(readonly: Environment) -> None:
    with browser(readonly) as (client, registry):
        path = "/reviews/" + entry(readonly)
        old = action_fields(client.get(path).text, "approve_recommendation")
        for _ in range(4):
            assert client.get(path).status_code == 200
        session = registry.get(client.cookies.get(COOKIE) or "")
        assert len(session.forms) == 4
        assert post(client, path + "/actions", old).status_code == 412


class Structure(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str | None]]] = []
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, dict(attrs)))


def test_escaped_untrusted_content_csp_and_accessibility_structure(readonly: Environment) -> None:
    original = readonly.api.view(readonly.fixture.tokens["reviewer"], entry(readonly))
    payload = '<script>alert(1)</script><img src="https://evil.example/x" onerror="steal()">'
    claim = original.detail.current_case.claim.model_copy(update={"narrative": payload})
    detail = original.detail.model_copy(
        update={"current_case": original.detail.current_case.model_copy(update={"claim": claim})}
    )
    session = Sessions(clock=lambda: NOW)
    token, anonymous = session.anonymous()
    html = views.case_detail(
        CaseView(detail, original.status, original.advisory), anonymous, "example-ticket"
    )
    assert payload not in html and "&lt;script&gt;" in html
    assert "<script" not in html and "<img" not in html
    parsed = Structure(html)
    ids = {attrs["id"] for _, attrs in parsed.tags if "id" in attrs}
    assert all(
        attrs["for"] in ids for tag, attrs in parsed.tags if tag == "label" and "for" in attrs
    )
    assert sum(tag == "main" for tag, _ in parsed.tags) == 1
    assert all(attrs.get("scope") == "col" for tag, attrs in parsed.tags if tag == "th")
    assert '<html lang="en">' in html and "Skip to main content" in html
    assert "@media(max-width:760px)" in views.CSS and ":focus-visible" in views.CSS
    with browser(readonly) as (client, _):
        response = client.get("/")
        csp = response.headers["content-security-policy"]
        assert "script-src 'none'" in csp and views.STYLE_HASH in csp
        assert "frame-ancestors 'none'" in csp and "form-action 'self'" in csp
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.parametrize(
    "mode", ["exception", "html", "oversized", "bad-json", "wrong-etag", "wrong-case"]
)
def test_api_failures_never_render_raw_payload_or_success(
    readonly: Environment, monkeypatch: pytest.MonkeyPatch, mode: str
) -> None:
    real = readonly.transport.request
    secret = "SECRET-exception-or-backend-payload"

    def broken(method: str, url: str, **kwargs: Any) -> httpx2.Response:
        if mode == "exception":
            raise RuntimeError(secret)
        if mode == "html":
            return httpx2.Response(500, text=secret)
        if mode == "oversized":
            return httpx2.Response(
                200, content=b"x" * 8388609, headers={"content-type": "application/json"}
            )
        response = real(method, url, **kwargs)
        if mode == "bad-json":
            return httpx2.Response(
                200, content=b"{bad", headers={"content-type": "application/json"}
            )
        if mode == "wrong-etag":
            response.headers["etag"] = '"999"'
        elif mode == "wrong-case" and "/status" in url:
            body = response.json()
            body["claim_id"] = readonly.fixture.bundles[1].request.intake.claim.claim_id
            return httpx2.Response(200, json=body, headers=dict(response.headers))
        return response

    with browser(readonly) as (client, _):
        identifier = entry(readonly)
        monkeypatch.setattr(readonly.transport, "request", broken)
        response = client.get("/reviews/" + identifier)
        assert response.status_code == 503
        assert secret not in response.text and "RuntimeError" not in response.text
        assert "Evidence and provenance" not in response.text
        assert "Recommendation action recorded" not in response.text


def test_form_ticket_cannot_be_used_for_another_case(readonly: Environment) -> None:
    identifiers = [
        item.entry_id for item in readonly.api.queue(readonly.fixture.tokens["supervisor"]).items
    ]
    with browser(readonly, "supervisor") as (client, _):
        fields = action_fields(
            client.get("/reviews/" + identifiers[0]).text, "approve_recommendation"
        )
        assert post(client, "/reviews/" + identifiers[1] + "/actions", fields).status_code == 412


def test_boundary_discards_partial_oversized_or_exception_responses() -> None:
    async def run(oversized: bool) -> list[Message]:
        sent: list[Message] = []

        async def broken(scope: Scope, receive: Receive, send: Send) -> None:
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"SECRET-PARTIAL", "more_body": True})
            if oversized:
                await send({"type": "http.response.body", "body": b"x" * 2097153})
            else:
                raise RuntimeError("SECRET-INTERNAL")

        async def receive() -> Message:
            return {"type": "http.request", "body": b""}

        async def send(message: Message) -> None:
            sent.append(message)

        scope: Scope = {
            "type": "http",
            "method": "GET",
            "scheme": "http",
            "headers": [(b"host", b"127.0.0.1:8767")],
            "query_string": b"",
            "client": ("127.0.0.1", 52000),
            "server": ("127.0.0.1", 8767),
            "path": "/",
        }
        await BrowserBoundary(broken)(scope, receive, send)
        return sent

    for oversized in (True, False):
        sent = asyncio.run(run(oversized))
        assert sent[0]["status"] == 503
        body = b"".join(message.get("body", b"") for message in sent)
        assert b"SECRET-" not in body


def test_snapshot_redacts_csrf_and_tickets(readonly: Environment) -> None:
    with browser(readonly) as (client, _):
        html = client.get("/reviews/" + entry(readonly)).text
        fields = FormInputs(html).values
        saved = snapshot(html).decode()
        assert fields["csrf"] not in saved and fields["ticket"] not in saved
        assert "REDACTED" in saved and 'type="submit" disabled' in saved


@pytest.mark.parametrize("same_action", [True, False])
def test_concurrent_browser_actions_have_one_mutation(
    mutable: Environment, same_action: bool
) -> None:
    identifier = entry(mutable)
    path = "/reviews/" + identifier
    before = mutable.api.view(mutable.fixture.tokens["reviewer"], identifier).detail.entry
    with browser(mutable) as (client, _):
        first = action_fields(client.get(path).text, "approve_recommendation")
        second = (
            first if same_action else action_fields(client.get(path).text, "reject_recommendation")
        )
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(
                pool.map(lambda data: post(client, path + "/actions", data), (first, second))
            )
        assert sorted(response.status_code for response in results) == (
            [200, 200] if same_action else [200, 409]
        )
        after = mutable.api.view(mutable.fixture.tokens["reviewer"], identifier).detail.entry
        assert len(after.events) == len(before.events) + 1
        if same_action:
            assert results[0].text == results[1].text


@pytest.mark.parametrize("surface", ["evidence", "policy", "rule", "advisory"])
def test_all_untrusted_text_surfaces_are_escaped(readonly: Environment, surface: str) -> None:
    view = readonly.api.view(readonly.fixture.tokens["reviewer"], entry(readonly))
    payload = '<svg onload="steal()"><a href="javascript:steal()">UNTRUSTED</a></svg>'
    if surface == "evidence":
        case = view.detail.current_case
        changed = case.evidence[0].model_copy(update={"observed_value": payload})
        detail = view.detail.model_copy(
            update={
                "current_case": case.model_copy(update={"evidence": (changed, *case.evidence[1:])})
            }
        )
        view = CaseView(detail, view.status, view.advisory)
    elif surface == "policy":
        retrieval = view.detail.advisory_snapshot.retrieval_response
        assert retrieval is not None
        hit = retrieval.hits[0]
        clause = hit.chunk.clause.model_copy(update={"text": payload})
        changed_hit = hit.model_copy(
            update={"chunk": hit.chunk.model_copy(update={"clause": clause})}
        )
        changed_retrieval = retrieval.model_copy(
            update={"hits": (changed_hit, *retrieval.hits[1:])}
        )
        changed_snapshot = view.detail.advisory_snapshot.model_copy(
            update={"retrieval_response": changed_retrieval}
        )
        view = CaseView(
            view.detail.model_copy(update={"advisory_snapshot": changed_snapshot}),
            view.status,
            view.advisory,
        )
    elif surface == "rule":
        rules = view.advisory.rules
        assert rules is not None
        changed_finding = rules.findings[0].model_copy(update={"explanation": payload})
        changed_rules = rules.model_copy(
            update={"findings": (changed_finding, *rules.findings[1:])}
        )
        view = CaseView(
            view.detail, view.status, view.advisory.model_copy(update={"rules": changed_rules})
        )
    else:
        draft = view.advisory.draft
        assert draft is not None
        changed_summary = draft.findings[0].model_copy(update={"explanation": payload})
        changed_draft = draft.model_copy(
            update={"findings": (changed_summary, *draft.findings[1:])}
        )
        view = CaseView(
            view.detail, view.status, view.advisory.model_copy(update={"draft": changed_draft})
        )
    _, session = Sessions(clock=lambda: NOW).anonymous()
    html = views.case_detail(view, session, "render-test")
    assert payload not in html and "&lt;svg" in html
    assert "<svg" not in html and 'href="javascript:' not in html


def test_complete_offline_ui_demo_uses_real_endpoints() -> None:
    report, captures = demonstrate(SPEC)
    assert (
        report["azure_operations"]
        == report["live_model_calls"]
        == report["autonomous_outcomes"]
        == 0
    )
    assert report["insurance_outcome_authority"] is False
    assert report["execution_surface"] == "REAL_FASTAPI_UI_AND_M16_TESTCLIENT_ASGI_NOT_TCP"
    cases = report["scenarios"]
    assert isinstance(cases, list)
    scenarios = {case["scenario"]: case["status"] for case in cases}
    assert scenarios["missing-recommendation-blocked"] == scenarios["stale-review-revision"] == 409
    assert scenarios["supervisor-boundary"] == 403
    assert scenarios["supervisor-evidence-request"] == 200
    assert len(captures) == 4
    assert all(b"REDACTED" in html for html in captures.values())


def test_ui_inflight_capacity_is_bounded() -> None:
    async def run() -> list[int]:
        entered, release = asyncio.Event(), asyncio.Event()
        running = 0

        async def slow(scope: Scope, receive: Receive, send: Send) -> None:
            nonlocal running
            running += 1
            if running == 8:
                entered.set()
            await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"bounded"})

        boundary = BrowserBoundary(slow)

        async def request() -> int:
            sent: list[Message] = []

            async def receive() -> Message:
                return {"type": "http.request", "body": b""}

            async def send(message: Message) -> None:
                sent.append(message)

            scope: Scope = {
                "type": "http",
                "method": "GET",
                "scheme": "http",
                "headers": [(b"host", b"127.0.0.1:8767")],
                "query_string": b"",
                "client": ("127.0.0.1", 52000),
                "server": ("127.0.0.1", 8767),
                "path": "/",
            }
            await boundary(scope, receive, send)
            status: int = sent[0]["status"]
            return status

        tasks = [asyncio.create_task(request()) for _ in range(9)]
        await asyncio.wait_for(entered.wait(), timeout=2)
        release.set()
        return await asyncio.gather(*tasks)

    assert sorted(asyncio.run(run())) == [200] * 8 + [429]


def test_slow_response_clients_cannot_bypass_inflight_capacity() -> None:
    async def run() -> int:
        full, release = asyncio.Event(), asyncio.Event()
        blocked = 0

        async def application(scope: Scope, receive: Receive, send: Send) -> None:
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"buffered"})

        boundary = BrowserBoundary(application)

        async def request(slow: bool) -> int:
            sent: list[Message] = []

            async def receive() -> Message:
                return {"type": "http.request", "body": b""}

            async def send(message: Message) -> None:
                nonlocal blocked
                sent.append(message)
                if slow and message["type"] == "http.response.start":
                    blocked += 1
                    if blocked == 8:
                        full.set()
                    await release.wait()

            scope: Scope = {
                "type": "http",
                "method": "GET",
                "scheme": "http",
                "headers": [(b"host", b"127.0.0.1:8767")],
                "query_string": b"",
                "client": ("127.0.0.1", 52000),
                "server": ("127.0.0.1", 8767),
                "path": "/",
            }
            await boundary(scope, receive, send)
            status: int = sent[0]["status"]
            return status

        tasks = [asyncio.create_task(request(True)) for _ in range(8)]
        try:
            await asyncio.wait_for(full.wait(), timeout=2)
            ninth = await request(False)
        finally:
            release.set()
            await asyncio.gather(*tasks)
        return ninth

    assert asyncio.run(run()) == 429


def test_ui_cli_refuses_existing_or_reference_evidence_paths(tmp_path: Path) -> None:
    existing = tmp_path / "keep.json"
    existing.write_text("PRESERVE")
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            "import runpy,sys;sys.path.insert(0,sys.argv.pop(1));"
            'runpy.run_module("claims_ai.reviewer_ui",run_name="__main__")',
            str(Path(views.__file__).resolve().parents[1].parent),
            "demo",
            "--spec-root",
            str(SPEC),
            "--output",
            str(existing),
            "--html-dir",
            str(tmp_path / "html"),
        ],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
    )
    assert result.returncode != 0 and existing.read_text() == "PRESERVE"
    assert "raw details omitted" in result.stderr
