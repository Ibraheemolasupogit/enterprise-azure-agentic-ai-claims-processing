"""Actual M16/M17 requests and isolated M15 fault injection; no business-rule implementation."""

from contextlib import ExitStack
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid5

import httpx2
from fastapi.testclient import TestClient

from claims_ai.adversarial.contracts import AttackCase, Observation, Scalar
from claims_ai.api.fixtures import demo_application
from claims_ai.human_review.__main__ import NOW, demo_decision
from claims_ai.human_review.contracts import (
    AssignmentRequest,
    Principal,
    PrincipalKind,
    ReviewAction,
    ReviewError,
    ReviewSession,
)
from claims_ai.human_review.service import ReviewQueue
from claims_ai.models import ReviewerRole
from claims_ai.reviewer_ui.__main__ import ORIGIN, FormInputs, enroll
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.client import ApiClient, CaseView
from claims_ai.reviewer_ui.host import NAMESPACE as SEED_NAMESPACE
from claims_ai.reviewer_ui.host import seed
from claims_ai.reviewer_ui.sessions import Profile, Sessions
from claims_ai.reviewer_ui.views import case_detail

NAMESPACE = UUID("19191919-1919-4919-8919-191919191919")


def observed(
    facts: dict[str, Scalar],
    note: str = "Actual application boundary response.",
    *,
    injected: bool = False,
) -> Observation:
    return Observation(
        execution="HOST_INJECTED_RUNTIME_GUARDS" if injected else "RUNTIME",
        facts=facts,
        evidence_note=note,
    )


class ApplicationHarness:
    def __init__(self, root: Path, stack: ExitStack) -> None:
        self.fixture = demo_application(
            root, fixtures=("valid-v1", "conflicting-amounts", "valid-v2")
        )
        self.client = stack.enter_context(
            TestClient(
                self.fixture.app, base_url="http://127.0.0.1:8766", client=("127.0.0.1", 51000)
            )
        )
        seed(self.client, self.fixture)
        self.api = ApiClient(self.client)
        self.entry_id = self.api.queue(self.fixture.tokens["reviewer"]).items[0].entry_id
        self.detail = self.api.view(self.fixture.tokens["reviewer"], self.entry_id).detail
        self.receipt: bytes | None = None
        self.accepted_body: dict[str, object] | None = None
        self.ui_sessions = Sessions(
            clock=lambda: NOW + timedelta(seconds=10),
            credential_valid=lambda token: self.fixture.authenticator.verify(token) is not None,
        )
        code = self.ui_sessions.provision(
            Profile("Synthetic reviewer", self.fixture.tokens["reviewer"])
        )
        self.browser = stack.enter_context(
            TestClient(
                create_ui(self.api, self.ui_sessions), base_url=ORIGIN, client=("127.0.0.1", 52000)
            )
        )
        enroll(self.browser, code)

    def headers(self, actor: str, case: AttackCase) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + self.fixture.tokens[actor],
            "X-Correlation-ID": str(uuid5(NAMESPACE, case.case_id)),
        }

    def response(self, response: httpx2.Response) -> Observation:
        facts: dict[str, Scalar] = {
            "status": response.status_code,
            "response_sha256": sha256(response.content).hexdigest(),
        }
        if response.headers.get("content-type", "").startswith("application/json"):
            body = response.json()
            if isinstance(body, dict) and isinstance(body.get("code"), str):
                facts["code"] = body["code"]
        return observed(facts)

    def decision(
        self, case: AttackCase, action: ReviewAction = ReviewAction.APPROVE, *, fresh: bool = False
    ) -> dict[str, object]:
        entry = (
            self.api.view(self.fixture.tokens["supervisor"], self.entry_id).detail.entry
            if fresh
            else self.detail.entry
        )
        return demo_decision(entry, action, "m19-" + case.case_id).model_dump(mode="json")

    def submit(
        self, case: AttackCase, body: dict[str, object], actor: str = "reviewer"
    ) -> httpx2.Response:
        return self.client.post(
            "/api/v1/reviews/" + self.entry_id + "/actions",
            headers={
                **self.headers(actor, case),
                "Idempotency-Key": str(body["action_id"]),
                "If-Match": '"' + str(body["expected_review_revision"]) + '"',
            },
            json=body,
        )

    def run(self, case: AttackCase) -> Observation:
        attack = case.attack
        headers = self.headers("reviewer", case)
        if attack == "positive":
            view = self.api.view(self.fixture.tokens["reviewer"], self.entry_id)
            return observed(
                {
                    "queue_visible": True,
                    "no_outcome": view.status.final_outcome is None
                    and not view.status.settlement_authorized,
                    "human_required": view.status.human_approval_required,
                }
            )
        if attack in {"forged", "spoof_role", "machine", "cross_case", "forbidden_outcome"}:
            path = "/api/v1/reviews"
            if attack == "forged":
                headers["Authorization"] = "Bearer " + "A" * 43
            elif attack == "spoof_role":
                headers["X-Role"] = "supervisor"
            elif attack == "machine":
                headers = self.headers("mcp", case)
            elif attack == "cross_case":
                path = (
                    "/api/v1/claims/"
                    + self.fixture.bundles[1].request.intake.claim.claim_id
                    + "/advisory"
                )
            else:
                path = "/api/v1/claims/" + self.detail.entry.binding.claim_id + "/settle"
            response = self.client.get(path, headers=headers)
            result = self.response(response)
            if attack == "cross_case":
                foreign = self.fixture.bundles[1].request.intake.claim.claim_id
                return observed({**result.facts, "foreign_case_present": foreign in response.text})
            return result
        if attack in {
            "duplicate_json",
            "oversized",
            "media",
            "trusted_fields",
            "missing_preconditions",
        }:
            body = {"expected_case_revision": 1, "expected_case_sha256": "a" * 64}
            path = "/api/v1/claims/" + self.detail.entry.binding.claim_id + "/process"
            headers.update(
                {
                    "Idempotency-Key": str(uuid5(NAMESPACE, case.case_id)),
                    "If-Match": '"1"',
                    "Content-Type": "application/json",
                }
            )
            if attack == "duplicate_json":
                return self.response(
                    self.client.post(
                        path,
                        headers=headers,
                        content=b'{"expected_case_revision":1,"expected_case_revision":2}',
                    )
                )
            if attack == "oversized":
                return self.response(self.client.post(path, headers=headers, content=b"x" * 16385))
            if attack == "media":
                headers["Content-Type"] = "text/plain"
            if attack == "trusted_fields":
                body["grant"] = True
            if attack == "missing_preconditions":
                headers.pop("If-Match")
            return self.response(self.client.post(path, headers=headers, json=body))
        if attack in {"duplicate_intake", "changed_intake"}:
            first = self.fixture.bundles[0]
            bundle = self.fixture.bundles[1] if attack == "changed_intake" else first
            response = self.client.post(
                "/api/v1/claims",
                headers={
                    **self.headers("host", case),
                    "Idempotency-Key": str(uuid5(SEED_NAMESPACE, first.bundle_id + "/intake")),
                    "If-None-Match": "*",
                },
                json={
                    "bundle_id": bundle.bundle_id,
                    "claim": bundle.request.intake.claim.model_dump(mode="json"),
                },
            )
            return self.response(response)
        if attack in {
            "missing_rationale",
            "outsider",
            "stale_binding",
            "unknown_evidence",
            "escalate",
            "supervisor_bypass",
            "stale_revision",
            "supervisor_approve",
            "duplicate_action",
            "changed_action",
            "revoked_action",
        }:
            action = ReviewAction.ESCALATE if attack == "escalate" else ReviewAction.APPROVE
            body = self.decision(
                case, action, fresh=attack in {"supervisor_bypass", "supervisor_approve"}
            )
            actor = (
                "outsider"
                if attack == "outsider"
                else "supervisor"
                if attack == "supervisor_approve"
                else "reviewer"
            )
            if attack == "missing_rationale":
                body["rationale"] = " "
            elif attack == "stale_binding":
                binding = dict(self.detail.entry.binding.model_dump(mode="json"))
                binding["evidence_sha256"] = "f" * 64
                body["expected"] = binding
            elif attack == "unknown_evidence":
                source = self.detail.entry.evidence[0].model_dump(mode="json")
                source["evidence_id"] = "NS-EVD-00000000"
                body["evidence"] = [source]
            elif attack in {"duplicate_action", "changed_action", "revoked_action"}:
                if self.accepted_body is None:
                    raise ValueError("positive decision prerequisite missing")
                body = dict(self.accepted_body)
                actor = "supervisor"
                if attack == "changed_action":
                    body["rationale"] = "Changed duplicate; do not reuse the receipt."
                if attack == "revoked_action":
                    self.fixture.authenticator.revoke(self.fixture.tokens["supervisor"])
            response = self.submit(case, body, actor)
            observation = self.response(response)
            if attack == "supervisor_approve" and response.status_code == 200:
                self.accepted_body, self.receipt = body, response.content
                view = self.api.view(self.fixture.tokens["reviewer"], self.entry_id)
                return observed(
                    {
                        **observation.facts,
                        "no_outcome": view.detail.current_case.decision is None
                        and view.detail.current_case.assessment is None,
                    }
                )
            if attack == "duplicate_action":
                return observed(
                    {**observation.facts, "same_receipt": response.content == self.receipt}
                )
            return observation
        if attack.startswith("ui_"):
            if attack == "ui_escape":
                view = self.api.view(self.fixture.tokens["reviewer"], self.entry_id)
                claim = view.detail.current_case.claim.model_copy(
                    update={"narrative": case.payload}
                )
                detail = view.detail.model_copy(
                    update={
                        "current_case": view.detail.current_case.model_copy(update={"claim": claim})
                    }
                )
                cookie = self.browser.cookies.get("northstar_reviewer") or ""
                html = case_detail(
                    CaseView(detail, view.status, view.advisory),
                    self.ui_sessions.get(cookie),
                    "render-only-ticket",
                )
                return observed(
                    {
                        "raw_html_present": case.payload in html,
                        "escaped_present": "&lt;script&gt;" in html,
                    },
                    (
                        "Direct production renderer with synthetic API-derived detail and "
                        "malicious text; no browser execution."
                    ),
                    injected=True,
                )
            fields = FormInputs(self.browser.get("/").text).values
            if attack == "ui_csrf":
                return self.response(
                    self.browser.post(
                        "/logout", headers={"Origin": ORIGIN}, data={"csrf": "forged"}
                    )
                )
            if attack == "ui_origin":
                return self.response(
                    self.browser.post(
                        "/logout",
                        headers={"Origin": "https://attacker.invalid"},
                        data={"csrf": fields["csrf"]},
                    )
                )
            if attack == "ui_role":
                return self.response(
                    self.browser.post(
                        "/logout",
                        headers={"Origin": ORIGIN},
                        data={"csrf": fields["csrf"], "role": "supervisor"},
                    )
                )
            if attack == "ui_revoked":
                self.ui_sessions.revoke(self.browser.cookies.get("northstar_reviewer") or "")
                return self.response(self.browser.get("/"))
        raise ValueError("unknown application probe")

    def review_probe(self, case: AttackCase) -> Observation:
        bundle = self.fixture.bundles[0]
        record = self.fixture.backend._records[bundle.request.intake.claim.claim_id]
        if record.checkpoint is None:
            raise ValueError("actual workflow checkpoint missing")
        producer = ReviewSession(
            Principal(
                principal_id=bundle.grant.principal_id,
                kind=PrincipalKind.HUMAN,
                role=ReviewerRole.REVIEWER,
            )
        )
        queue = ReviewQueue(
            (*self.fixture.sessions.values(), producer), clock=lambda: NOW + timedelta(seconds=10)
        )
        import asyncio

        entry = asyncio.run(
            queue.enqueue(
                self.fixture.sessions["host"],
                bundle.request,
                bundle.grant,
                record.checkpoint,
                occurred_at=NOW,
            )
        )
        assignee = producer if case.attack == "self_review" else self.fixture.sessions["reviewer"]
        request = AssignmentRequest(
            request_id=uuid5(NAMESPACE, case.case_id),
            entry_id=entry.entry_id,
            claim_id=entry.binding.claim_id,
            expected_review_revision=entry.review_revision,
            assignee_id=assignee.principal.principal_id,
            occurred_at=NOW + timedelta(seconds=1),
            rationale="Synthetic adversarial assignment probe.",
        )
        if case.attack == "self_review":
            code = "accepted"
            try:
                queue.assign(self.fixture.sessions["host"], request)
            except ReviewError as error:
                code = error.code.value
            return observed(
                {
                    "code": code,
                    "registered_producer": producer.principal.principal_id in queue._principals,
                    "forbidden_producer": producer.principal.principal_id in entry.producer_ids,
                },
                "Registered synthetic human producer attempts host assignment; M15 guard runs.",
            )
        queue.assign(self.fixture.sessions["host"], request)
        entry = queue.details.get(assignee, entry.entry_id).entry
        altered = (
            entry.model_copy(update={"events": entry.events[:-1]})
            if case.attack == "audit_truncate"
            else entry.model_copy(
                update={
                    "events": (
                        entry.events[0].model_copy(update={"rationale": case.payload}),
                        *entry.events[1:],
                    )
                }
            )
        )
        queue._entries[entry.entry_id] = altered
        code = "accepted"
        try:
            queue.details.get(assignee, entry.entry_id)
        except ReviewError as error:
            code = error.code.value
        return observed(
            {"code": code},
            (
                "Isolated host-memory corruption; actual M15 semantic/hash/head "
                "replay executes. This is not an HTTP write capability."
            ),
            injected=True,
        )
