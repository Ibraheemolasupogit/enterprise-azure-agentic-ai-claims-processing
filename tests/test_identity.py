"""Offline signature/policy/key negatives and actual API/UI/MCP integration."""

import hmac
import io
import json
import logging
import socket
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from fastapi.testclient import TestClient
from jwt.warnings import InsecureKeyLengthWarning
from pydantic import ValidationError

from claims_ai.api.app import create_app
from claims_ai.api.auth import ApiAccess, SyntheticAuthenticator
from claims_ai.api.contracts import ApiScope
from claims_ai.api.fixtures import ApiFixture, demo_application
from claims_ai.human_review.__main__ import NOW, demo_sessions
from claims_ai.human_review.contracts import PrincipalKind, ReviewSession
from claims_ai.identity.__main__ import APPLICATION, TENANT, offline_report
from claims_ai.identity.adapters import VerifiedCapabilities
from claims_ai.identity.capabilities import Capabilities
from claims_ai.identity.contracts import (
    API_AUDIENCE,
    MCP_AUDIENCE,
    AuthorityKind,
    IdentityRole,
    ProductionCookieRequirements,
    VerificationPolicy,
)
from claims_ai.identity.keys import LocalKeyRing
from claims_ai.identity.verification import SyntheticTokenVerifier, UnconfiguredEntraVerifier, issue
from claims_ai.logging import JsonFormatter, correlation_scope
from claims_ai.mcp_http.auth import AUDIENCE as LEGACY_AUDIENCE
from claims_ai.mcp_http.auth import SyntheticIssuer
from claims_ai.reviewer_ui.__main__ import ORIGIN, action_fields, enroll
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.boundary import COOKIE
from claims_ai.reviewer_ui.client import ApiClient, UiError
from claims_ai.reviewer_ui.host import seed
from claims_ai.reviewer_ui.sessions import Profile, Sessions

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data/rules/motor/v1"
EPOCH = 1_800_000_000
CASE = "NS-CLM-12345678"
OTHER = "NS-CLM-87654321"


def policy(role: IdentityRole = IdentityRole.REVIEWER) -> VerificationPolicy:
    name = {
        IdentityRole.REVIEWER: "reviewer",
        IdentityRole.SUPERVISOR: "supervisor",
        IdentityRole.INTAKE: "host",
        IdentityRole.BACKEND: "mcp",
    }[role]
    return VerificationPolicy(
        audience=MCP_AUDIENCE if role == IdentityRole.BACKEND else API_AUDIENCE,
        tenant_id=TENANT,
        application_id=APPLICATION,
        subject=demo_sessions()[name].principal.principal_id,
        role=role,
    )


@pytest.fixture
def keys() -> LocalKeyRing:
    return LocalKeyRing(clock=lambda: EPOCH)


def claims(keys: LocalKeyRing, selected: VerificationPolicy | None = None) -> dict[str, Any]:
    return jwt.decode(
        issue(keys, selected or policy(), (CASE,), now=EPOCH), options={"verify_signature": False}
    )


@pytest.mark.parametrize("role", list(IdentityRole))
def test_exact_signed_synthetic_principal_roles(keys: LocalKeyRing, role: IdentityRole) -> None:
    selected = policy(role)
    verifier = SyntheticTokenVerifier(selected, keys, clock=lambda: EPOCH)
    token = issue(keys, selected, (CASE,), now=EPOCH)
    identity = verifier.verify(token)
    assert identity is not None and identity.authority_kind == AuthorityKind.SYNTHETIC
    assert identity.claims.case_ids == (CASE,) and identity.claims.roles == (role,)
    assert identity.principal.principal_id == selected.subject
    assert (identity.principal.kind == PrincipalKind.HUMAN) == (
        role in {IdentityRole.REVIEWER, IdentityRole.SUPERVISOR}
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("iss", "https://login.microsoftonline.com/real/v2.0"),
        ("iss", "https://northstar.invalid/identity/v1/"),
        ("aud", "api://other"),
        ("aud", [API_AUDIENCE]),
        ("aud", MCP_AUDIENCE),
        ("tid", str(uuid4())),
        ("azp", str(uuid4())),
        ("sub", str(uuid4())),
        ("roles", ["Claims.Supervisor"]),
        ("roles", ["claims.reviewer"]),
        ("roles", ["Claims.Reviewer", "Claims.Supervisor"]),
        ("roles", "Claims.Reviewer"),
        ("roles", []),
        ("roles", ["Claims.Reviewer", "Claims.Reviewer"]),
        ("principal_kind", "mcp_client"),
        ("principal_kind", "agent"),
        ("authority", "entra_target_not_configured"),
        ("exp", EPOCH),
        ("exp", EPOCH + 301),
        ("exp", str(EPOCH + 60)),
        ("exp", True),
        ("iat", EPOCH + 1),
        ("iat", float(EPOCH)),
        ("nbf", EPOCH + 1),
        ("nbf", False),
        ("jti", "not-a-uuid"),
        ("case_ids", [CASE, CASE]),
        ("case_ids", []),
        ("case_ids", ["*"]),
    ],
)
def test_signed_invalid_claims_fail_closed(keys: LocalKeyRing, field: str, value: object) -> None:
    payload = claims(keys)
    payload[field] = value
    verifier = SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH)
    assert verifier.verify(keys.sign(payload)) is None


@pytest.mark.parametrize(
    "field",
    [
        "iss",
        "aud",
        "tid",
        "azp",
        "sub",
        "roles",
        "iat",
        "nbf",
        "exp",
        "jti",
        "authority",
        "case_ids",
        "principal_kind",
    ],
)
def test_missing_or_renamed_claims_are_rejected(keys: LocalKeyRing, field: str) -> None:
    payload = claims(keys)
    payload["renamed_" + field] = payload.pop(field)
    assert (
        SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH).verify(keys.sign(payload))
        is None
    )


@pytest.mark.parametrize(
    "header",
    [
        {"alg": "none"},
        {"alg": "HS256"},
        {"alg": "RS512"},
        {"typ": "JWT"},
        {"kid": "unknown"},
        {"kid": "https://evil.invalid/key"},
        {"jku": "https://evil.invalid/jwks"},
        {"jwk": {"kty": "oct", "k": "attacker"}},
        {"x5u": "https://evil.invalid/certificate"},
        {"crit": ["evil"]},
    ],
)
def test_untrusted_header_signing_instructions_never_resolve_network(
    keys: LocalKeyRing, header: dict[str, object], monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts: list[object] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        attempts.append(args)
        raise AssertionError("network forbidden")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    lookups: list[str] = []

    class Published:
        authority_kind = AuthorityKind.SYNTHETIC

        def resolve(self, kid: str, now: int) -> rsa.RSAPublicKey | None:
            lookups.append(kid)
            return private.public_key() if kid == "local-0001" else None

    original: dict[str, object] = {"alg": "RS256", "typ": "at+jwt", "kid": "local-0001"}
    original.update(header)
    raw_header = jwt.utils.base64url_encode(json.dumps(original).encode())
    raw_payload = jwt.utils.base64url_encode(json.dumps(claims(keys)).encode())
    signing = raw_header + b"." + raw_payload
    algorithm = hashes.SHA512() if original["alg"] == "RS512" else hashes.SHA256()
    signed = (
        signing
        + b"."
        + jwt.utils.base64url_encode(private.sign(signing, padding.PKCS1v15(), algorithm))
    )
    assert (
        SyntheticTokenVerifier(policy(), Published(), clock=lambda: EPOCH).verify(signed.decode())
        is None
    )
    assert attempts == [] and lookups == []


@pytest.mark.parametrize("part", [0, 1])
def test_duplicate_json_members_are_not_last_value_wins(keys: LocalKeyRing, part: int) -> None:
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    class Published:
        authority_kind = AuthorityKind.SYNTHETIC

        def resolve(self, kid: str, now: int) -> rsa.RSAPublicKey:
            return private.public_key()

    raw_parts = [
        json.dumps({"alg": "RS256", "typ": "at+jwt", "kid": "local-0001"}),
        json.dumps(claims(keys)),
    ]
    raw = raw_parts[part]
    duplicate = '"alg":"none",' if part == 0 else '"roles":["Claims.Supervisor"],'
    raw_parts[part] = "{" + duplicate + raw[1:]
    signing = b".".join(jwt.utils.base64url_encode(raw.encode()) for raw in raw_parts)
    signed = (
        signing
        + b"."
        + jwt.utils.base64url_encode(private.sign(signing, padding.PKCS1v15(), hashes.SHA256()))
    )
    verifier = SyntheticTokenVerifier(policy(), Published(), clock=lambda: EPOCH)
    # PyJWT's default parser accepts the correctly signed last-value interpretation.
    assert jwt.decode(
        signed,
        private.public_key(),
        algorithms=["RS256"],
        audience=API_AUDIENCE,
        options={"verify_exp": False, "verify_nbf": False, "verify_iat": False},
    )["roles"] == ["Claims.Reviewer"]
    assert verifier.verify(signed.decode()) is None


@pytest.mark.parametrize("token", ["", "a.b", "a.b.c.d", "a.b.c", "." * 9000, "a=.b.c", "é.b.c"])
def test_malformed_and_oversized_credentials(keys: LocalKeyRing, token: str) -> None:
    assert SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH).verify(token) is None


def test_rsa_hmac_key_confusion_and_wrong_valid_key_are_denied(keys: LocalKeyRing) -> None:
    public = keys.resolve(keys.current, EPOCH)
    assert public is not None
    der = public.public_bytes(
        serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    signing = b".".join(
        jwt.utils.base64url_encode(json.dumps(value).encode())
        for value in ({"alg": "HS256", "typ": "at+jwt", "kid": keys.current}, claims(keys))
    )
    token = (
        signing + b"." + jwt.utils.base64url_encode(hmac.new(der, signing, sha256).digest())
    ).decode()
    verifier = SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH)
    assert verifier.verify(token) is None
    other = LocalKeyRing(clock=lambda: EPOCH)
    assert verifier.verify(issue(other, policy(), (CASE,), now=EPOCH)) is None


def test_rotation_overlap_retirement_expiry_and_finite_key_discovery() -> None:
    now = [EPOCH]
    ring = LocalKeyRing(clock=lambda: now[0])
    verifier = SyntheticTokenVerifier(policy(), ring, clock=lambda: now[0])
    old = issue(ring, policy(), (CASE,), now=now[0])
    old_kid = ring.current
    ring.rotate()
    new = issue(ring, policy(), (CASE,), now=now[0])
    assert verifier.verify(old) is not None and verifier.verify(new) is not None
    ring.retire(old_kid)
    assert verifier.verify(old) is None and verifier.verify(new) is not None
    now[0] += 300
    assert verifier.verify(new) is None
    now[0] += 300
    assert ring.resolve(ring.current, now[0]) is None
    with pytest.raises(ValueError):
        ring.sign(claims(LocalKeyRing(clock=lambda: EPOCH)))
    bounded = LocalKeyRing(clock=lambda: EPOCH)
    for _ in range(3):
        bounded.rotate()
    with pytest.raises(ValueError):
        bounded.rotate()
    for _ in range(4):
        bounded.retire(bounded.current)
        bounded.rotate()
    bounded.retire(bounded.current)
    with pytest.raises(ValueError):
        bounded.rotate()


def test_token_principal_and_capacity_revocation_fail_closed(keys: LocalKeyRing) -> None:
    verifier = SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH)
    token = issue(keys, policy(), (CASE,), now=EPOCH)
    verified = verifier.verify(token)
    assert verified is not None
    verifier.revoke_token(verified.claims.jti)
    assert verifier.verify(token) is None
    fresh = issue(keys, policy(), (CASE,), now=EPOCH)
    assert verifier.verify(fresh) is not None
    verifier.revoke_principal()
    assert verifier.verify(fresh) is None
    bounded = SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH)
    for _ in range(64):
        bounded.revoke_token(uuid4())
    with pytest.raises(ValueError):
        bounded.revoke_token(uuid4())
    assert bounded.verify(fresh) is None


def test_clock_rollback_latches_verifier_closed(keys: LocalKeyRing) -> None:
    now = [EPOCH + 10]
    verifier = SyntheticTokenVerifier(policy(), keys, clock=lambda: now[0])
    token = issue(keys, policy(), (CASE,), now=EPOCH)
    assert verifier.verify(token) is not None
    now[0] -= 1
    assert verifier.verify(token) is None
    now[0] += 2
    assert verifier.verify(token) is None


def test_discovery_outage_provider_separation_and_unconfigured_entra(keys: LocalKeyRing) -> None:
    class Unavailable:
        authority_kind = AuthorityKind.SYNTHETIC

        def resolve(self, kid: str, now: int) -> None:
            raise RuntimeError("SECRET-discovery-error")

    token = issue(keys, policy(), (CASE,), now=EPOCH)
    assert (
        SyntheticTokenVerifier(policy(), Unavailable(), clock=lambda: EPOCH).verify(token) is None
    )
    assert UnconfiguredEntraVerifier().verify(token) is None

    class Foreign(Unavailable):
        authority_kind = AuthorityKind.ENTRA

    with pytest.raises(ValueError):
        SyntheticTokenVerifier(policy(), Foreign())


@pytest.mark.parametrize("invalid", [0, -1, 901, float("inf"), float("nan"), True])
def test_invalid_opaque_capability_lifetimes(invalid: float) -> None:
    with pytest.raises(ValueError):
        Capabilities[str]().issue("value", ttl=invalid)


def test_default_api_capability_absolute_expiry_revocation_and_capacity() -> None:
    now = [0.0]
    authority = SyntheticAuthenticator(timer=lambda: now[0])
    session = demo_sessions()["reviewer"]
    access = ApiAccess(ApiScope(principal=session.principal, claim_ids=(CASE,)), session)
    token = authority.issue(access)
    assert authority.verify(token) is access
    now[0] = 900
    assert authority.verify(token) is None
    revoked = authority.issue(access)
    authority.revoke(revoked)
    assert authority.verify(revoked) is None
    for _ in range(64):
        authority.issue(access)
    with pytest.raises(ValueError):
        authority.issue(access)
    now[0] = 1800
    assert len(authority.issue(access)) == 43
    now[0] = 1799
    assert authority.verify(token) is None
    now[0] = 1801
    with pytest.raises(ValueError):
        authority.issue(access)  # The clock remains closed after rollback.


def test_opaque_clock_failure_and_collision_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable() -> float:
        raise RuntimeError("SECRET-clock")

    assert Capabilities[str](timer=unavailable).resolve("x" * 43) is None
    monkeypatch.setattr(
        "claims_ai.identity.capabilities.secrets.token_urlsafe", lambda count: "A" * 43
    )
    store = Capabilities[str]()
    store.issue("first")
    with pytest.raises(ValueError):
        store.issue("replacement")
    assert store.resolve("A" * 43) == "first"


def test_identity_does_not_create_case_or_session_authority(keys: LocalKeyRing) -> None:
    session = demo_sessions()["reviewer"]
    selected = policy()
    token = issue(keys, selected, (CASE,), now=EPOCH)
    verifier = SyntheticTokenVerifier(selected, keys, clock=lambda: EPOCH)
    cap = VerifiedCapabilities()
    access = ApiAccess(ApiScope(principal=session.principal, claim_ids=(CASE,)), session)
    assert cap.verify(token) is None
    opaque = cap.issue(access, token, verifier)
    assert cap.verify(opaque) is access
    for wrong in [
        ApiAccess(ApiScope(principal=session.principal, claim_ids=(OTHER,)), session),
        ApiAccess(access.scope),
    ]:
        with pytest.raises(ValueError):
            cap.issue(wrong, token, verifier)
    expanded = issue(keys, selected, (CASE, OTHER), now=EPOCH)
    with pytest.raises(ValueError):
        cap.issue(access, expanded, verifier)
    cap.revoke(opaque)
    assert cap.verify(opaque) is None
    machine_policy = policy(IdentityRole.BACKEND)
    machine = issue(keys, machine_policy, (CASE,), now=EPOCH)
    with pytest.raises(ValueError):
        cap.issue(
            access, machine, SyntheticTokenVerifier(machine_policy, keys, clock=lambda: EPOCH)
        )


@contextmanager
def integration(
    *, copied_session: bool = False
) -> Iterator[
    tuple[
        TestClient,
        ApiClient,
        VerifiedCapabilities,
        str,
        SyntheticTokenVerifier,
        Sessions,
        ApiFixture,
    ]
]:
    fixture = demo_application(SPEC, fixtures=("valid-v1",))
    ring = LocalKeyRing(clock=lambda: EPOCH)
    caps = VerifiedCapabilities()
    tokens = {}
    verifiers = {}
    for name, role in [("host", IdentityRole.INTAKE), ("reviewer", IdentityRole.REVIEWER)]:
        access = fixture.authenticator.verify(fixture.tokens[name])
        assert access is not None
        if copied_session and name == "reviewer":
            access = ApiAccess(access.scope, ReviewSession(access.scope.principal))
        selected = policy(role)
        verifier = SyntheticTokenVerifier(selected, ring, clock=lambda: EPOCH)
        tokens[name] = caps.issue(
            access, issue(ring, selected, access.scope.claim_ids, now=EPOCH), verifier
        )
        verifiers[name] = verifier
    with TestClient(
        create_app(fixture.backend, authenticator=caps),
        base_url="http://127.0.0.1:8766",
        client=("127.0.0.1", 51000),
    ) as backend:
        seed(backend, fixture, host_token=tokens["host"])
        registry = Sessions(
            clock=lambda: NOW + timedelta(seconds=10),
            credential_valid=lambda token: caps.verify(token) is not None,
        )
        yield (
            backend,
            ApiClient(backend),
            caps,
            tokens["reviewer"],
            verifiers["reviewer"],
            registry,
            fixture,
        )


def test_real_api_ui_authority_and_revocation_with_verified_capabilities() -> None:
    with integration() as (backend, api, caps, token, verifier, registry, fixture):
        identifier = api.queue(token).items[0].entry_id
        code = registry.provision(Profile("Synthetic reviewer", token))
        with TestClient(
            create_ui(api, registry), base_url=ORIGIN, client=("127.0.0.1", 52000)
        ) as browser:
            enroll(browser, code)
            path = "/reviews/" + identifier
            fields = action_fields(browser.get(path).text, "approve_recommendation")
            first = browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN})
            assert first.status_code == 200
            verifier.revoke_principal()
            assert (
                browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN}).status_code
                == 401
            )
            assert browser.get("/").status_code == 401
            assert (
                backend.get(
                    "/api/v1/reviews", headers={"Authorization": "Bearer " + token}
                ).status_code
                == 401
            )
            assert caps.verify(token) is None
        assert (
            fixture.backend.queue.details.get(
                fixture.sessions["reviewer"], identifier
            ).current_case.decision
            is None
        )


def test_verified_signature_cannot_replace_canonical_m15_session() -> None:
    with integration(copied_session=True) as (
        backend,
        api,
        caps,
        token,
        verifier,
        registry,
        fixture,
    ):
        assert (
            backend.get("/api/v1/reviews", headers={"Authorization": "Bearer " + token}).status_code
            == 404
        )
        assert (
            caps.verify(token) is not None
        )  # Authentication succeeds; M15 authorization still fails.


def test_host_revokes_ui_cookie_codes_and_profiles_without_changing_api_authority() -> None:
    with integration() as (_, api, caps, token, _, registry, _):
        code = registry.provision(Profile("Synthetic reviewer", token))
        with TestClient(
            create_ui(api, registry), base_url=ORIGIN, client=("127.0.0.1", 52000)
        ) as browser:
            enroll(browser, code)
            cookie = browser.cookies.get(COOKIE) or ""
            registry.revoke(cookie)
            assert browser.get("/").status_code == 401
            assert caps.verify(token) is not None
        code = registry.provision(Profile("Synthetic reviewer", token))
        cookie, anonymous = registry.anonymous()
        registry.revoke_profile(token)
        with pytest.raises(UiError):
            registry.login(cookie, anonymous.csrf, code)
        caps.revoke(token)
        with pytest.raises(UiError):
            registry.provision(Profile("revoked", token))


def test_signed_identity_still_requires_exact_case_scope_at_api() -> None:
    with integration() as (backend, _, _, token, _, _, _):
        response = backend.get(
            "/api/v1/claims/" + OTHER + "/status", headers={"Authorization": "Bearer " + token}
        )
        assert response.status_code == 404 and OTHER not in response.text
        assert (
            backend.get(
                "/api/v1/reviews",
                headers={"Authorization": "Bearer " + token, "X-Role": "supervisor"},
            ).status_code
            == 403
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("secure", False),
        ("httponly", False),
        ("samesite", "lax"),
        ("domain", "localhost"),
        ("path", "/reviews"),
        ("tls_required", False),
    ],
)
def test_production_cookie_contract_cannot_enable_an_insecure_profile(
    field: str, value: object
) -> None:
    with pytest.raises(ValidationError):
        ProductionCookieRequirements.model_validate({field: value})
    assert ProductionCookieRequirements().secure


def test_identity_audit_is_correlated_redacted_and_non_durable(keys: LocalKeyRing) -> None:
    stream = io.StringIO()
    logger = logging.Logger("identity-test")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    verifier = SyntheticTokenVerifier(policy(), keys, clock=lambda: EPOCH, logger=logger)
    token = issue(keys, policy(), (CASE,), now=EPOCH)
    correlation = uuid4()
    with correlation_scope(correlation):
        assert verifier.verify(token) is not None
        assert verifier.verify("SECRET-credential") is None
    records = [json.loads(line) for line in stream.getvalue().splitlines()]
    assert [record["fields"] for record in records] == [{"status": "ok"}, {"status": "denied"}]
    assert all(
        record["correlation_id"] == str(correlation) and record["event"] == "identity_verification"
        for record in records
    )
    assert (
        token not in stream.getvalue()
        and "SECRET" not in stream.getvalue()
        and CASE not in stream.getvalue()
    )


@pytest.mark.parametrize(
    "mutation", [{"aud": [LEGACY_AUDIENCE]}, {"exp": True}, {"iat": 0.5}, {"nbf": 0}]
)
def test_existing_m14_verifier_rejects_ambiguous_audience_and_dates(
    mutation: dict[str, object],
) -> None:
    issuer = SyntheticIssuer()
    assert issuer.verifier.verify(issuer.issue()) is not None
    assert issuer.verifier.verify(issuer.issue(**mutation)) is None


def test_complete_offline_evidence_forbids_all_socket_connections(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts: list[object] = []

    def forbidden(*args: object, **kwargs: object) -> None:
        attempts.append(args)
        raise AssertionError("identity demo must make no network call")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "bind", forbidden)
    report = offline_report(SPEC)
    assert report["network_calls"] == report["azure_operations"] == report["live_model_calls"] == 0
    scenarios = report["scenarios"]
    assert isinstance(scenarios, list)
    assert len(scenarios) == 15 and all(item["passed"] for item in scenarios)
    assert any(item["scenario"] == "genuine-mcp-three-governed-reads" for item in scenarios)
    assert attempts == []


def test_correctly_signed_weak_rsa_key_is_not_accepted(keys: LocalKeyRing) -> None:
    private = rsa.generate_private_key(public_exponent=65537, key_size=1024)

    class Weak:
        authority_kind = AuthorityKind.SYNTHETIC

        def resolve(self, kid: str, now: int) -> rsa.RSAPublicKey:
            return private.public_key()

    with pytest.warns(InsecureKeyLengthWarning):
        token = jwt.encode(
            claims(keys), private, algorithm="RS256", headers={"kid": "local-0001", "typ": "at+jwt"}
        )
    assert SyntheticTokenVerifier(policy(), Weak(), clock=lambda: EPOCH).verify(token) is None


def test_actual_api_identity_audit_uses_request_correlation() -> None:
    stream = io.StringIO()
    logger = logging.getLogger("claims_ai.identity")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    previous_level = logger.level
    logger.setLevel(logging.INFO)
    try:
        with integration() as (backend, _, _, token, _, _, _):
            stream.seek(0)
            stream.truncate()
            correlation = uuid4()
            response = backend.get(
                "/api/v1/reviews",
                headers={
                    "Authorization": "Bearer " + token,
                    "X-Correlation-ID": str(correlation),
                },
            )
            assert response.status_code == 200
            records = [json.loads(line) for line in stream.getvalue().splitlines()]
            assert records and all(
                record["correlation_id"] == str(correlation) for record in records
            )
            assert all(record["fields"] == {"status": "ok"} for record in records)
            assert token not in stream.getvalue()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)
