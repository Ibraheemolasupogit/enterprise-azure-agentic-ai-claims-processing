"""Offline API/UI and genuine MCP security evidence; never writes credentials or keys."""

import argparse
import asyncio
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid5

import httpx2
from fastapi.testclient import TestClient

from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agents.__main__ import demo_input
from claims_ai.api.app import create_app
from claims_ai.api.fixtures import demo_application
from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.__main__ import NOW
from claims_ai.identity.adapters import GatewayIdentityAdapter, VerifiedCapabilities
from claims_ai.identity.contracts import (
    API_AUDIENCE,
    MCP_AUDIENCE,
    IdentityRole,
    VerificationPolicy,
)
from claims_ai.identity.keys import LocalKeyRing
from claims_ai.identity.verification import SyntheticTokenVerifier, UnconfiguredEntraVerifier, issue
from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip
from claims_ai.reviewer_ui.__main__ import ORIGIN, action_fields, enroll
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.client import ApiClient
from claims_ai.reviewer_ui.host import seed
from claims_ai.reviewer_ui.sessions import Profile, Sessions

NAMESPACE = UUID("18181818-1818-4818-8818-181818181818")
TENANT = uuid5(NAMESPACE, "tenant")
APPLICATION = uuid5(NAMESPACE, "application")


def offline_report(root: Path) -> dict[str, object]:
    now = [int((NOW + timedelta(seconds=10)).timestamp())]
    keys = LocalKeyRing(clock=lambda: now[0])
    capabilities = VerifiedCapabilities()
    fixture = demo_application(root, fixtures=("valid-v1",))
    tokens: dict[str, str] = {}
    credentials: dict[str, str] = {}
    verifiers: dict[str, SyntheticTokenVerifier] = {}
    policies: dict[str, VerificationPolicy] = {}
    for name, role in (
        ("host", IdentityRole.INTAKE),
        ("reviewer", IdentityRole.REVIEWER),
        ("supervisor", IdentityRole.SUPERVISOR),
    ):
        access = fixture.authenticator.verify(fixture.tokens[name])
        assert access is not None
        policy = VerificationPolicy(
            audience=API_AUDIENCE,
            tenant_id=TENANT,
            application_id=APPLICATION,
            subject=access.scope.principal.principal_id,
            role=role,
        )
        credential = issue(
            keys, policy, access.scope.claim_ids, now=now[0], token_id=uuid5(NAMESPACE, name)
        )
        verifier = SyntheticTokenVerifier(policy, keys, clock=lambda: now[0])
        policies[name], credentials[name], verifiers[name] = policy, credential, verifier
        tokens[name] = capabilities.issue(access, credential, verifier)
    scenarios: list[dict[str, object]] = []

    def check(name: str, condition: bool) -> None:
        if condition is not True:
            raise ValueError("offline identity verification failed")
        scenarios.append({"scenario": name, "passed": True})

    with TestClient(
        create_app(fixture.backend, authenticator=capabilities),
        base_url="http://127.0.0.1:8766",
        client=("127.0.0.1", 51000),
    ) as backend:
        seed(backend, fixture, host_token=tokens["host"])
        api = ApiClient(backend)
        entry = api.queue(tokens["reviewer"]).items[0]
        check(
            "verified-human-api-queue",
            entry.claim_id == fixture.bundles[0].request.intake.claim.claim_id,
        )
        check("opaque-api-capability-not-jwt", len(tokens["reviewer"]) == 43)
        check(
            "signed-token-not-an-api-session",
            backend.get(
                "/api/v1/reviews", headers={"Authorization": "Bearer " + credentials["reviewer"]}
            ).status_code
            == 401,
        )
        registry = Sessions(
            clock=lambda: NOW + timedelta(seconds=10),
            credential_valid=lambda token: capabilities.verify(token) is not None,
        )
        code = registry.provision(Profile("Synthetic reviewer", tokens["reviewer"]))
        with TestClient(
            create_ui(api, registry), base_url=ORIGIN, client=("127.0.0.1", 52000)
        ) as browser:
            enroll(browser, code)
            path = "/reviews/" + entry.entry_id
            detail = browser.get(path)
            check("verified-ui-detail", detail.status_code == 200)
            fields = action_fields(detail.text, "approve_recommendation")
            check(
                "explicit-recommendation-approval",
                browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN}).status_code
                == 200,
            )
            old_kid = keys.current
            keys.rotate()
            check(
                "rotation-overlap",
                verifiers["reviewer"].verify(credentials["reviewer"]) is not None,
            )
            replacement = issue(keys, policies["reviewer"], (entry.claim_id,), now=now[0])
            check("new-signing-key", verifiers["reviewer"].verify(replacement) is not None)
            keys.retire(old_kid)
            check("retired-key-denied", capabilities.verify(tokens["reviewer"]) is None)
            check("revoked-identity-invalidates-ui", browser.get("/").status_code == 401)
        # Reuse the existing canonical session; never construct a session from token claims.
        access = fixture.authenticator.verify(fixture.tokens["reviewer"])
        assert access is not None
        fresh = capabilities.issue(access, replacement, verifiers["reviewer"])
        verified = verifiers["reviewer"].verify(replacement)
        assert verified is not None
        verifiers["reviewer"].revoke_token(verified.claims.jti)
        check("token-revocation", capabilities.verify(fresh) is None)
        view = fixture.backend.queue.details.get(fixture.sessions["reviewer"], entry.entry_id)
        check(
            "human-authority-preserved",
            view.current_case.decision is None and view.current_case.assessment is None,
        )
    # Separate MCP audience/machine principal; the host's case grant remains independent.
    value = demo_input(root, "valid-v1")
    case_ids = (value.rule_request.case.claim.claim_id,)
    machine = VerificationPolicy(
        audience=MCP_AUDIENCE,
        tenant_id=TENANT,
        application_id=APPLICATION,
        subject=uuid5(NAMESPACE, "gateway"),
        role=IdentityRole.BACKEND,
    )
    machine_verifier = SyntheticTokenVerifier(machine, keys, clock=lambda: now[0])
    machine_token = issue(keys, machine, case_ids, now=now[0])
    boundary = HttpBoundary(
        value,
        demo_grant(value, "m18-identity"),
        port=8765,
        gateway_subject=machine.subject,
        verifier=GatewayIdentityAdapter(machine_verifier, case_ids),
    )

    async def protocol() -> dict[str, object]:
        async with boundary.app.router.lifespan_context(boundary.app):
            return await protocol_roundtrip(
                "http://127.0.0.1:8765/mcp",
                machine_token,
                value,
                transport=httpx2.ASGITransport(app=boundary.app),
            )

    result = asyncio.run(protocol())
    check(
        "genuine-mcp-three-governed-reads",
        len(result["tools"]) == 3 if isinstance(result["tools"], list) else False,
    )
    check(
        "human-token-cannot-authenticate-mcp",
        GatewayIdentityAdapter(verifiers["reviewer"], case_ids).verify(replacement) is None,
    )
    now[0] += 300
    check("exact-expiry-denied", machine_verifier.verify(machine_token) is None)
    check(
        "entra-is-unconfigured-and-denied",
        UnconfiguredEntraVerifier().verify(machine_token) is None,
    )
    return {
        "milestone": 18,
        "execution_surface": "OFFLINE_SIGNED_IDENTITY_AND_REAL_API_UI_MCP_ASGI_NOT_TCP",
        "authority": "LOCAL_SYNTHETIC_NOT_ENTRA",
        "azure_operations": 0,
        "network_calls": 0,
        "live_identity_provider_calls": 0,
        "live_model_calls": 0,
        "autonomous_outcomes": 0,
        "apim_enforcement": "STATIC_ONLY_NOT_LIVE",
        "storage": "BOUNDED_VOLATILE_MEMORY",
        "scenarios": scenarios,
        "identity_source_sha256": sha256(
            b"".join(
                p.name.encode() + b"\0" + p.read_bytes()
                for p in sorted(Path(__file__).parent.glob("*.py"))
            )
        ).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline identity/security evidence; no network")
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root, output = args.spec_root.resolve(), args.output.resolve()
        protected = [root, Path("data").resolve(), *(p for p in root.parents if p.name == "data")]
        if output.exists() or any(output.is_relative_to(p) for p in protected):
            raise ValueError("new evidence outside reference data is required")
        report = offline_report(root)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(json_bytes(report))
    except Exception as failure:
        parser.exit(
            1,
            f"Offline identity evidence unavailable ({type(failure).__name__}); payload omitted.\n",
        )
    print(
        "Offline signed identity, API/UI and genuine MCP evidence recorded; no Entra/network calls."
    )


if __name__ == "__main__":
    main()
