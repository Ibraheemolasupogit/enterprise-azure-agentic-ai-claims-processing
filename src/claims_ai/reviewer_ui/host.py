"""Explicit synthetic host setup: seed through M16, never through private review methods."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid5

from fastapi import FastAPI
from fastapi.testclient import TestClient

from claims_ai.api.contracts import ClaimStatus
from claims_ai.api.fixtures import ApiFixture, demo_application
from claims_ai.human_review.__main__ import NOW
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.client import ApiClient
from claims_ai.reviewer_ui.sessions import Profile, Sessions

NAMESPACE = UUID("17171717-1717-4717-8717-171717171717")


@dataclass(frozen=True)
class UiHost:
    app: FastAPI
    api: ApiClient
    sessions: Sessions
    fixture: ApiFixture = field(repr=False)
    codes: dict[str, str] = field(repr=False)


def seed(client: TestClient, fixture: ApiFixture) -> None:
    for bundle in fixture.bundles:
        claim = bundle.request.intake.claim
        headers = {
            "Authorization": "Bearer " + fixture.tokens["host"],
            "Idempotency-Key": str(uuid5(NAMESPACE, bundle.bundle_id + "/intake")),
            "If-None-Match": "*",
        }
        response = client.post(
            "/api/v1/claims",
            headers=headers,
            json={"bundle_id": bundle.bundle_id, "claim": claim.model_dump(mode="json")},
        )
        if response.status_code != 201:
            raise ValueError("synthetic host intake unavailable")
        status = ClaimStatus.model_validate_json(response.content)
        headers.pop("If-None-Match")
        headers.update(
            {
                "Idempotency-Key": str(uuid5(NAMESPACE, bundle.bundle_id + "/process")),
                "If-Match": f'"{status.application_revision}"',
            }
        )
        response = client.post(
            f"/api/v1/claims/{claim.claim_id}/process",
            headers=headers,
            json={
                "expected_case_revision": status.case_revision,
                "expected_case_sha256": status.case_sha256,
            },
        )
        if response.status_code != 200:
            raise ValueError("synthetic host processing unavailable")
        ClaimStatus.model_validate_json(response.content)


@contextmanager
def demo_host(root: Path, *, port: int = 8767) -> Iterator[UiHost]:
    fixture = demo_application(root)
    with TestClient(
        fixture.app, base_url="http://127.0.0.1:8766", client=("127.0.0.1", 51000)
    ) as transport:
        seed(transport, fixture)
        api = ApiClient(transport)
        sessions = Sessions(clock=lambda: NOW + timedelta(seconds=10))
        codes = {
            name: sessions.provision(Profile("Synthetic " + name, fixture.tokens[name]))
            for name in ("reviewer", "supervisor")
        }
        yield UiHost(create_ui(api, sessions, port=port), api, sessions, fixture, codes)
