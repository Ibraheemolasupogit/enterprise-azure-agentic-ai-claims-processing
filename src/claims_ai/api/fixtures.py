"""Explicit synthetic host configuration for tests/CLI; never activated by default app creation."""

from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI

from claims_ai.api.app import create_app
from claims_ai.api.auth import ApiAccess, SyntheticAuthenticator
from claims_ai.api.contracts import ApiLimits, ApiScope
from claims_ai.api.service import ClaimsApplication, HostBundle, WorkflowService
from claims_ai.human_review.__main__ import NOW, demo_sessions
from claims_ai.human_review.contracts import ReviewSession
from claims_ai.human_review.service import ReviewQueue
from claims_ai.workflow.__main__ import demo_grant, demo_request


@dataclass(frozen=True)
class ApiFixture:
    app: FastAPI
    backend: ClaimsApplication
    authenticator: SyntheticAuthenticator
    bundles: tuple[HostBundle, ...]
    sessions: dict[str, ReviewSession]
    tokens: dict[str, str] = field(repr=False)


def demo_application(
    root: Path,
    *,
    runner: WorkflowService | None = None,
    limits: ApiLimits | None = None,
    fixtures: tuple[str, ...] = (
        "valid-v1",
        "valid-v2",
        "gradual-wear-exclusion",
        "conflicting-amounts",
        "missing-estimate",
    ),
) -> ApiFixture:
    sessions = demo_sessions()
    now = NOW + timedelta(seconds=10)
    queue = ReviewQueue(tuple(sessions.values()), clock=lambda: now)
    bundles = []
    for name in fixtures:
        request = demo_request(root, name, "m16-" + name)
        bundles.append(
            HostBundle(
                name, request, demo_grant(request), (sessions["reviewer"], sessions["supervisor"])
            )
        )
    backend = ClaimsApplication(
        tuple(bundles), queue, sessions["host"], runner=runner, limits=limits, clock=lambda: now
    )
    authenticator = SyntheticAuthenticator()
    tokens = {}
    all_cases = tuple(b.request.intake.claim.claim_id for b in bundles)
    for name, session in sessions.items():
        human = session.principal.role is not None
        claim_ids = all_cases[:1] if name in {"reviewer", "outsider"} else all_cases
        tokens[name] = authenticator.issue(
            ApiAccess(
                ApiScope(
                    principal=session.principal,
                    claim_ids=claim_ids,
                    can_intake=name == "host",
                    can_process=name == "host",
                ),
                session if human else None,
            )
        )
    return ApiFixture(
        create_app(backend, authenticator=authenticator, limits=limits),
        backend,
        authenticator,
        tuple(bundles),
        sessions,
        tokens,
    )
