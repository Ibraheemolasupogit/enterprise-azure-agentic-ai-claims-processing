"""M21 real verification, existing services and durable process restart boundaries."""

import asyncio
import io
import json
import logging
import os
import socket
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx2
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from pydantic import ValidationError

from claims_ai.api.app import create_app
from claims_ai.api.auth import ApiAccess, SyntheticAuthenticator
from claims_ai.api.contracts import ApiScope
from claims_ai.api.fixtures import demo_application
from claims_ai.human_review.__main__ import NOW as REVIEW_NOW
from claims_ai.human_review.__main__ import demo_sessions
from claims_ai.human_review.contracts import ReviewSession
from claims_ai.identity.adapters import VerifiedCapabilities
from claims_ai.identity.contracts import API_AUDIENCE, IdentityRole, VerificationPolicy
from claims_ai.identity.keys import LocalKeyRing
from claims_ai.identity.verification import UnconfiguredEntraVerifier, issue
from claims_ai.logging import JsonFormatter
from claims_ai.models import AssessmentOutcome, ReviewerRole
from claims_ai.outcomes.contracts import Action, ApprovedInput, OutcomeError
from claims_ai.outcomes.demo import NOW, approved_fixture, command, demo_host, prepared_store
from claims_ai.outcomes.store import OutcomeStore
from claims_ai.reviewer_ui.__main__ import ORIGIN, action_fields, enroll
from claims_ai.reviewer_ui.app import create_ui
from claims_ai.reviewer_ui.client import ApiClient, UiError
from claims_ai.reviewer_ui.host import seed
from claims_ai.reviewer_ui.sessions import Profile, Sessions
from claims_ai.security_hardening.bindings import (
    LifecycleAuthenticator,
    LifecycleGateway,
    access_binding,
    gateway_binding,
)
from claims_ai.security_hardening.contracts import (
    MATRIX,
    DeploymentContract,
    Grant,
    IdentityClass,
    Permission,
)
from claims_ai.security_hardening.lifecycle import Lifecycle, LifecycleError
from claims_ai.security_hardening.providers import (
    OfflineFixtureVerifier,
    PinnedKey,
    ProviderProfile,
    load_fixture,
    synthetic_context,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "data/security/identity/v1"
SPEC = ROOT / "data/rules/motor/v1"
EPOCH = 1800000000
CASE = "NS-CLM-12345678"
OTHER = "NS-CLM-87654321"
# Synthetic test integrity context only. Never a credential or production secret.
KEY = b"T" * 32
CONTEXT = "1" * 64


def grant_for(access: ApiAccess, *, target: str = "api", now: int = EPOCH) -> Grant:
    name = access.scope.principal.role
    kind = IdentityClass.SUPERVISOR if name == ReviewerRole.SUPERVISOR else IdentityClass.REVIEWER
    permissions = {Permission.REVIEW if target == "api" else Permission.OUTCOME}
    if name == ReviewerRole.SUPERVISOR:
        permissions.add(Permission.SUPERVISE)
    if name is None:
        kind = IdentityClass.PUBLISHER if target == "outcomes" else IdentityClass.WORKLOAD
        permissions = {Permission.PUBLISH} if target == "outcomes" else set()
        if access.scope.can_intake:
            permissions.add(Permission.INTAKE)
        if access.scope.can_process:
            permissions.add(Permission.PROCESS)
    assert target in {"api", "outcomes"}
    return Grant(
        grant_id=uuid4(),
        principal_id=access.scope.principal.principal_id,
        identity_class=kind,
        case_ids=access.scope.claim_ids,
        permissions=tuple(sorted(permissions)),
        binding_sha256=access_binding(access, "api" if target == "api" else "outcomes"),
        issued_at=now,
        expires_at=now + 300,
    )


@pytest.fixture
def ledger(tmp_path: Path) -> Lifecycle:
    return Lifecycle(
        tmp_path / "lifecycle.sqlite3",
        context_sha256=CONTEXT,
        integrity_key=KEY,
        create=True,
        clock=lambda: EPOCH,
    )


@pytest.fixture(scope="module")
def signed_fixture() -> tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile]:
    data = json.loads((FIXTURES / "human_reviewer.json").read_text())
    claims = jwt.decode(data["token"], options={"verify_signature": False})
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return claims, key, ProviderProfile.model_validate(data["profile"])


def signed_mutation(
    source: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
    changes: dict[str, object],
    *,
    headers: dict[str, object] | None = None,
) -> tuple[OfflineFixtureVerifier, str]:
    claims, key, profile = source
    token = jwt.encode(
        {**claims, **changes},
        key,
        algorithm="RS256",
        headers=headers or {"kid": "fixture-0001", "typ": "JWT"},
    )
    verifier = OfflineFixtureVerifier(
        profile,
        {"fixture-0001": PinnedKey(key.public_key(), EPOCH, EPOCH + 600)},
        clock=lambda: EPOCH,
    )
    return verifier, token


@pytest.mark.parametrize("kind", list(IdentityClass))
def test_pinned_offline_profiles_accept_exact_signed_inputs_without_network(
    monkeypatch: pytest.MonkeyPatch,
    kind: IdentityClass,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("offline verifier attempted network")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(socket.socket, "bind", forbidden)
    verifier, token = load_fixture(str(FIXTURES / (kind.value + ".json")))
    result = verifier.verify(token)
    assert result is not None and result.simulated and result.identity_class == kind
    assert not hasattr(result, "principal") and not hasattr(verifier, "authority_kind")
    assert UnconfiguredEntraVerifier().verify(token) is None


@pytest.mark.parametrize("size", [65535, 65536, 65537, 131072])
def test_fixture_loading_bounds_actual_file_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, size: int
) -> None:
    raw = (FIXTURES / "human_reviewer.json").read_bytes()
    path = tmp_path / "fixture.json"
    path.write_bytes(raw + b" " * (size - len(raw)))
    reads: list[tuple[int, int]] = []

    class MonitoredFile(io.FileIO):
        def read(self, size: int | None = -1, /) -> bytes:
            assert size is not None and 0 <= size <= 65537, (
                "fixture read must be explicitly bounded"
            )
            content = super().read(size)
            assert content is not None
            reads.append((size, len(content)))
            return content

    def monitored_open(requested: Path, mode: str, *, buffering: int) -> MonitoredFile:
        assert requested == path and mode == "rb" and buffering == 0
        return MonitoredFile(requested, mode)

    monkeypatch.setattr(Path, "open", monitored_open)
    if size <= 65536:
        verifier, token = load_fixture(str(path))
        assert verifier.verify(token) is not None
    else:
        with pytest.raises(ValueError, match="^fixture capacity$"):
            load_fixture(str(path))
    assert reads == [(65537, min(size, 65537))]


@pytest.mark.parametrize(
    "field,value",
    [
        ("iss", "https://northstar.invalid/identity/v1"),
        ("iss", "https://login.microsoftonline.com/common/v2.0"),
        ("aud", "api://northstar.invalid/mcp-backend-v1"),
        ("aud", [API_AUDIENCE]),
        ("tid", str(uuid4())),
        ("oid", str(uuid4())),
        ("azp", str(uuid4())),
        ("ver", "1.0"),
        ("roles", ["Claims.Supervisor"]),
        ("roles", ["Claims.Reviewer", "Claims.Supervisor"]),
        ("roles", []),
        ("idtyp", "app"),
        ("idtyp", ""),
        ("scp", "Claims.Review Claims.Admin"),
        ("scp", ""),
        ("case_ids", [CASE]),
        ("authority", "local_synthetic_authority"),
        ("provider", "entra"),
        ("exp", EPOCH),
        ("iat", EPOCH + 1),
        ("nbf", EPOCH - 1),
        ("exp", EPOCH + 301),
        ("exp", True),
        ("iat", float(EPOCH)),
        ("jti", "not-an-id"),
    ],
)
def test_correctly_signed_wrong_claims_fail_closed(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
    field: str,
    value: object,
) -> None:
    verifier, token = signed_mutation(signed_fixture, {field: value})
    assert verifier.verify(token) is None
    good, valid = signed_mutation(signed_fixture, {})
    assert good.verify(valid) is not None  # Same key/profile accepts legitimate control.


@pytest.mark.parametrize(
    "headers",
    [
        {"kid": "fixture-9999"},
        {"kid": "local-0001"},
        {"kid": "fixture-0001", "jku": "https://attacker.invalid/keys"},
        {"kid": "fixture-0001", "typ": "at+jwt"},
    ],
)
def test_header_key_instructions_fail_before_discovery(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
    headers: dict[str, object],
) -> None:
    verifier, token = signed_mutation(signed_fixture, {}, headers=headers)
    assert verifier.verify(token) is None


def test_wrong_key_signature_and_algorithm_confusion(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
) -> None:
    verifier, token = signed_mutation(signed_fixture, {})
    claims, _, _ = signed_fixture
    rogue = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    assert (
        verifier.verify(
            jwt.encode(claims, rogue, algorithm="RS256", headers={"kid": "fixture-0001"})
        )
        is None
    )
    assert (
        verifier.verify(
            jwt.encode(claims, b"x" * 64, algorithm="HS256", headers={"kid": "fixture-0001"})
        )
        is None
    )
    assert verifier.verify(token) is not None


def test_rotation_overlap_retirement_and_clock_rollback(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
) -> None:
    claims, key, profile = signed_fixture
    replacement = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    keys = {
        "fixture-0001": PinnedKey(key.public_key(), EPOCH, EPOCH + 300),
        "fixture-0002": PinnedKey(replacement.public_key(), EPOCH, EPOCH + 600),
    }
    now = [EPOCH]
    verifier = OfflineFixtureVerifier(profile, keys, clock=lambda: now[0])
    old = jwt.encode(claims, key, algorithm="RS256", headers={"kid": "fixture-0001"})
    new = jwt.encode(claims, replacement, algorithm="RS256", headers={"kid": "fixture-0002"})
    assert verifier.verify(old) and verifier.verify(new)
    retired = OfflineFixtureVerifier(
        profile, {"fixture-0002": keys["fixture-0002"]}, clock=lambda: EPOCH
    )
    assert retired.verify(old) is None and retired.verify(new) is not None
    assert retired.context_sha256 != verifier.context_sha256
    now[0] -= 1
    assert verifier.verify(old) is None
    now[0] += 1
    assert verifier.verify(new) is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("provider", "live_entra"),
        ("live_enabled", True),
        ("simulated", False),
        ("issuer", "https://login.microsoftonline.com/common/v2.0"),
        ("audience", "api://other"),
        ("role", "Claims.Supervisor"),
        ("algorithms", "HS256"),
    ],
)
def test_provider_configuration_cannot_enable_live_or_widen_profile(
    field: str, value: object
) -> None:
    data = json.loads((FIXTURES / "human_reviewer.json").read_text())["profile"]
    with pytest.raises(ValidationError):
        ProviderProfile.model_validate({**data, field: value})


@pytest.mark.parametrize("kind", list(IdentityClass))
def test_permission_matrix_denies_other_identity_authority(kind: IdentityClass) -> None:
    permitted = tuple(sorted(MATRIX[kind]))
    base = dict(
        grant_id=uuid4(),
        principal_id=uuid4(),
        identity_class=kind,
        case_ids=(CASE,),
        binding_sha256=CONTEXT,
        issued_at=EPOCH,
        expires_at=EPOCH + 300,
    )
    assert Grant.model_validate({**base, "permissions": permitted}).identity_class == kind
    for forbidden in set(Permission) - MATRIX[kind]:
        with pytest.raises(ValidationError):
            Grant.model_validate({**base, "permissions": (forbidden,)})


@pytest.mark.parametrize(
    "mutation", ["duplicate_cases", "duplicate_permissions", "too_long", "no_cases"]
)
def test_grant_contracts_are_bounded_and_exact(mutation: str) -> None:
    access = ApiAccess(
        ApiScope(principal=demo_sessions()["reviewer"].principal, claim_ids=(CASE,)),
        demo_sessions()["reviewer"],
    )
    data = grant_for(access).model_dump(mode="json")
    if mutation == "duplicate_cases":
        data["case_ids"] = [CASE, CASE]
    if mutation == "duplicate_permissions":
        data["permissions"] = [Permission.REVIEW, Permission.REVIEW]
    if mutation == "too_long":
        data["expires_at"] = EPOCH + 901
    if mutation == "no_cases":
        data["case_ids"] = []
    with pytest.raises(ValidationError):
        Grant.model_validate(data)


def access() -> ApiAccess:
    session = demo_sessions()["reviewer"]
    return ApiAccess(ApiScope(principal=session.principal, claim_ids=(CASE,)), session)


def test_grant_revocation_and_disablement_retain_history(ledger: Lifecycle) -> None:
    grant = grant_for(access())
    ledger.issue(grant)
    ledger.require(grant, frozenset({Permission.REVIEW}))
    ledger.revoke(grant.grant_id)
    with pytest.raises(LifecycleError):
        ledger.require(grant, frozenset({Permission.REVIEW}))
    second = grant_for(access())
    ledger.issue(second)
    ledger.disable(second.principal_id)
    with pytest.raises(LifecycleError):
        ledger.require(second, frozenset({Permission.REVIEW}))
    with pytest.raises(LifecycleError):
        ledger.issue(grant_for(access()))
    assert ledger.checkpoint().revision == 4
    assert CASE.encode() in ledger.path.read_bytes()
    assert b"ReviewSession" not in ledger.path.read_bytes()


@pytest.mark.parametrize("kind", ["expiry", "unknown", "changed", "permission", "backward_clock"])
def test_invalid_or_expired_lifecycle_access_fails(ledger: Lifecycle, kind: str) -> None:
    grant = grant_for(access())
    ledger.issue(grant)
    wanted = frozenset({Permission.REVIEW})
    if kind == "expiry":
        ledger._clock = lambda: EPOCH + 300
    if kind == "unknown":
        grant = grant.model_copy(update={"grant_id": uuid4()})
    if kind == "changed":
        grant = grant.model_copy(update={"case_ids": (OTHER,)})
    if kind == "permission":
        wanted = frozenset({Permission.PUBLISH})
    if kind == "backward_clock":
        ledger._clock = lambda: EPOCH - 1
    with pytest.raises(LifecycleError):
        ledger.require(grant, wanted)


@pytest.mark.parametrize(
    "mutation", ["garbage", "payload", "mac", "schema", "version", "context", "deleted"]
)
def test_corrupt_or_unavailable_store_never_recovers_authority(
    ledger: Lifecycle, mutation: str
) -> None:
    grant = grant_for(access())
    ledger.issue(grant)
    anchor = ledger.checkpoint()
    if mutation == "deleted":
        ledger.path.unlink()
    elif mutation == "garbage":
        ledger.path.write_bytes(b"not sqlite")
    else:
        with sqlite3.connect(ledger.path) as c:
            if mutation in {"payload", "mac"}:
                c.execute("DROP TRIGGER immutable_update")
                if mutation == "payload":
                    c.execute("UPDATE events SET payload='{}'")
                else:
                    c.execute("UPDATE events SET mac=?", ("f" * 64,))
                c.execute(
                    "CREATE TRIGGER immutable_update BEFORE UPDATE ON events "
                    "BEGIN SELECT RAISE(ABORT,'append_only'); END"
                )
            elif mutation == "schema":
                c.execute("CREATE TABLE bypass (role TEXT)")
            elif mutation == "version":
                c.execute("PRAGMA user_version=99")
            else:
                c.execute("UPDATE context SET binding=?", ("2" * 64,))
    with pytest.raises(LifecycleError):
        Lifecycle(
            ledger.path,
            context_sha256=CONTEXT,
            integrity_key=KEY,
            anchor=anchor,
            clock=lambda: EPOCH,
        )


def test_authenticated_history_and_independent_anchor_detect_rollback(
    ledger: Lifecycle, tmp_path: Path
) -> None:
    grant = grant_for(access())
    ledger.issue(grant)
    saved = ledger.path.read_bytes()
    ledger.revoke(grant.grant_id)
    anchor = ledger.checkpoint()
    ledger.path.write_bytes(saved)
    for anchor_value in (anchor,):
        with pytest.raises(LifecycleError):
            Lifecycle(
                ledger.path,
                context_sha256=CONTEXT,
                integrity_key=KEY,
                anchor=anchor_value,
                clock=lambda: EPOCH,
            )
    with pytest.raises(LifecycleError):
        ledger.require(grant, frozenset({Permission.REVIEW}))
    with pytest.raises(LifecycleError):
        Lifecycle(
            ledger.path,
            context_sha256=CONTEXT,
            integrity_key=b"z" * 32,
            anchor=anchor,
            clock=lambda: EPOCH,
        )


@pytest.mark.parametrize("alias", ["symlink", "hardlink", "public", "public_parent"])
def test_private_storage_alias_and_permissions(
    ledger: Lifecycle, tmp_path: Path, alias: str
) -> None:
    anchor = ledger.checkpoint()
    path = tmp_path / "alias.sqlite3"
    if alias == "symlink":
        path.symlink_to(ledger.path)
    elif alias == "hardlink":
        os.link(ledger.path, path)
    else:
        path = ledger.path
        (path if alias == "public" else tmp_path).chmod(0o644 if alias == "public" else 0o755)
    with pytest.raises(LifecycleError):
        Lifecycle(
            path, context_sha256=CONTEXT, integrity_key=KEY, anchor=anchor, clock=lambda: EPOCH
        )


def test_append_only_capacity_and_concurrent_revocation(tmp_path: Path, ledger: Lifecycle) -> None:
    grant = grant_for(access())
    ledger.issue(grant)
    with sqlite3.connect(ledger.path) as c:
        with pytest.raises(sqlite3.IntegrityError):
            c.execute("DELETE FROM events")
    second = Lifecycle(
        ledger.path,
        context_sha256=CONTEXT,
        integrity_key=KEY,
        anchor=ledger.checkpoint(),
        clock=lambda: EPOCH,
    )

    def revoke(lifecycle: Lifecycle) -> bool:
        try:
            lifecycle.revoke(grant.grant_id)
            return True
        except LifecycleError:
            return False

    with ThreadPoolExecutor(2) as pool:
        assert sorted(pool.map(revoke, (ledger, second))) == [False, True]
    for _ in range(63):
        ledger.issue(grant_for(access()))
    with pytest.raises(LifecycleError):
        ledger.issue(grant_for(access()))
    assert ledger.checkpoint().revision == 65


def test_wrapper_preserves_exact_inner_capability_and_case_binding(ledger: Lifecycle) -> None:
    original = access()
    inner = SyntheticAuthenticator()
    token = inner.issue(original)
    grant = grant_for(original)
    ledger.issue(grant)
    gate = LifecycleAuthenticator(inner, ledger, target="api")
    assert gate.verify(token) is None
    gate.bind(token, grant)
    assert gate.verify(token) is original
    copied = ApiAccess(original.scope, ReviewSession(original.review_session.principal))  # type: ignore[union-attr]
    copied_token = inner.issue(copied)
    gate.bind(copied_token, grant)
    # Authenticators do not assign reviewers: canonical service must reject this copy.
    assert gate.verify(copied_token) is copied
    altered = ApiAccess(
        original.scope.model_copy(update={"claim_ids": (OTHER,)}), original.review_session
    )
    with pytest.raises(LifecycleError):
        gate.bind(inner.issue(altered), grant)
    ledger.disable(original.scope.principal.principal_id)
    assert gate.verify(token) is None and gate.verify(copied_token) is None


def test_real_api_ui_revocation_and_duplicate_receipts(ledger: Lifecycle) -> None:
    fixture = demo_application(SPEC, fixtures=("valid-v1",))
    gate = LifecycleAuthenticator(fixture.authenticator, ledger, target="api")
    grants = {}
    for name in ("host", "reviewer", "supervisor"):
        original = fixture.authenticator.verify(fixture.tokens[name])
        assert original is not None
        grant = grant_for(original)
        ledger.issue(grant)
        gate.bind(fixture.tokens[name], grant)
        grants[name] = grant
    with TestClient(
        create_app(fixture.backend, authenticator=gate),
        base_url="http://127.0.0.1:8766",
        client=("127.0.0.1", 51000),
    ) as backend:
        seed(backend, fixture)
        api = ApiClient(backend)
        entry = api.queue(fixture.tokens["reviewer"]).items[0]
        sessions = Sessions(
            clock=lambda: REVIEW_NOW + timedelta(seconds=10),
            credential_valid=lambda t: gate.verify(t) is not None,
        )
        code = sessions.provision(Profile("Synthetic reviewer", fixture.tokens["reviewer"]))
        with TestClient(
            create_ui(api, sessions), base_url=ORIGIN, client=("127.0.0.1", 52000)
        ) as browser:
            enroll(browser, code)
            path = "/reviews/" + entry.entry_id
            page = browser.get(path)
            assert page.status_code == 200
            fields = action_fields(page.text, "approve_recommendation")
            assert (
                browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN}).status_code
                == 200
            )
            ledger.revoke(grants["reviewer"].grant_id)
            assert (
                browser.post(path + "/actions", data=fields, headers={"Origin": ORIGIN}).status_code
                == 401
            )
            assert (
                backend.get(
                    "/api/v1/reviews",
                    headers={"Authorization": "Bearer " + fixture.tokens["reviewer"]},
                ).status_code
                == 401
            )
            with pytest.raises(UiError):
                sessions.provision(Profile("Revoked", fixture.tokens["reviewer"]))
        detail = fixture.backend.queue.details.get(fixture.sessions["reviewer"], entry.entry_id)
        assert detail.current_case.decision is None and detail.current_case.assessment is None


@pytest.fixture(scope="module")
def approval() -> ApprovedInput:
    return asyncio.run(
        approved_fixture(SPEC, name="m21-tests", approved_outcome=AssessmentOutcome.ELIGIBLE)
    )


def guarded_host(ledger: Lifecycle, approval: ApprovedInput) -> tuple[Any, dict[str, Grant]]:
    host = demo_host((approval,))
    gate = LifecycleAuthenticator(host.authenticator, ledger, target="outcomes")
    grants = {}
    for name in ("host", "reviewer", "supervisor"):
        original = host.authenticator.verify(host.tokens[name])
        assert original is not None
        grant = grant_for(original, target="outcomes")
        ledger.issue(grant)
        gate.bind(host.tokens[name], grant)
        grants[name] = grant
    host.authority.authenticator = gate
    return host, grants


def test_revoked_outcome_duplicate_and_disabled_actor_history(
    ledger: Lifecycle,
    approval: ApprovedInput,
    tmp_path: Path,
) -> None:
    host, grants = guarded_host(ledger, approval)
    store, _, state = prepared_store(tmp_path / "case.sqlite3", approval, host)
    request = command(Action.DECIDE, "m21-decision", approval, state)
    event = store.execute(host.tokens["reviewer"], request)
    assert store.execute(host.tokens["reviewer"], request) == event
    ledger.disable(grants["reviewer"].principal_id)
    with pytest.raises(OutcomeError, match="access_denied"):
        store.execute(host.tokens["reviewer"], request)
    # New process-local authority with fresh sessions retains trusted historical identities;
    # disabled principal remains known for replay but cannot bind a current capability.
    fresh = demo_host((approval,))
    gate = LifecycleAuthenticator(fresh.authenticator, ledger, target="outcomes")
    host_access = fresh.authenticator.verify(fresh.tokens["host"])
    assert host_access is not None
    gate.bind(fresh.tokens["host"], grants["host"])
    old_access = fresh.authenticator.verify(fresh.tokens["reviewer"])
    assert old_access is not None
    with pytest.raises(LifecycleError):
        gate.bind(fresh.tokens["reviewer"], grants["reviewer"])
    fresh.authority.authenticator = gate
    recovered = OutcomeStore(store.path, fresh.authority, clock=lambda: NOW + timedelta(days=1))
    assert (
        recovered.read(fresh.tokens["host"], request.claim_id).case.decision
        == event.after.case.decision
    )


@pytest.mark.parametrize("attack", ["copied_session", "supervisor", "publication", "cross_case"])
def test_existing_outcome_authority_survives_lifecycle_composition(
    ledger: Lifecycle,
    approval: ApprovedInput,
    tmp_path: Path,
    attack: str,
) -> None:
    host, grants = guarded_host(ledger, approval)
    store, _, state = prepared_store(tmp_path / "case.sqlite3", approval, host)
    if attack == "publication":
        with pytest.raises(OutcomeError, match="operation_not_authorized"):
            store.execute(
                host.tokens["reviewer"],
                command(Action.PUBLISH, "badpub", approval, state),
                permit=host.authority.permit,
            )
    elif attack == "supervisor":
        state = store.execute(
            host.tokens["reviewer"], command(Action.DECIDE, "close-before-reopen", approval, state)
        ).after
        with pytest.raises(OutcomeError, match="supervisor_reopening_required"):
            store.execute(
                host.tokens["reviewer"], command(Action.REOPEN, "badreopen", approval, state)
            )
    elif attack == "cross_case":
        bad = command(Action.DECIDE, "badcase", approval, state).model_copy(
            update={"claim_id": OTHER}
        )
        with pytest.raises((OutcomeError, ValidationError)):
            store.execute(host.tokens["reviewer"], bad)
    else:
        original = host.authenticator.verify(host.tokens["reviewer"])
        assert original is not None
        copied = ApiAccess(original.scope, ReviewSession(original.review_session.principal))
        token = host.authenticator.issue(copied)
        host.authority.authenticator.bind(token, grants["reviewer"])
        with pytest.raises(OutcomeError, match="access_denied"):
            store.execute(token, command(Action.DECIDE, "copied", approval, state))
    assert store.read(host.tokens["host"], approval.case.claim.claim_id) == state


@pytest.mark.parametrize(
    "field,value",
    [
        ("enabled", True),
        ("live_provider", True),
        ("tls_required", False),
        ("private_ingress_required", False),
        ("direct_backend_public_access", True),
        ("forwarded_identity_trusted", True),
        ("backend_authentication", "none"),
        ("secret_source", "environment"),
        ("secret_reference", "literal-password"),
        ("backend_audience", API_AUDIENCE),
        ("cookie", {"secure": False}),
    ],
)
def test_unsafe_deployment_combinations_fail(field: str, value: object) -> None:
    config = dict(
        gateway_application=uuid4(),
        backend_application=uuid4(),
        secret_reference="kvref://northstar-offline/gateway-cert",
    )
    assert not DeploymentContract.model_validate(config).enabled
    with pytest.raises(ValidationError):
        DeploymentContract.model_validate({**config, field: value})


def test_same_gateway_backend_application_is_forbidden() -> None:
    identity = uuid4()
    with pytest.raises(ValidationError):
        DeploymentContract(
            gateway_application=identity,
            backend_application=identity,
            secret_reference="kvref://northstar-offline/key",
        )


def test_verification_logs_are_redacted(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
) -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger = logging.getLogger("m21-log-test")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    verifier, token = signed_mutation(signed_fixture, {})
    verifier._logger = logger
    assert verifier.verify(token) is not None
    assert verifier.verify(token + "untrusted-sensitive-claim") is None
    text = stream.getvalue()
    assert (
        token not in text
        and "sensitive" not in text
        and str(verifier.profile.object_id) not in text
    )
    rows = [json.loads(line) for line in text.splitlines()]
    assert len(rows) == 2 and "ok" in text and "denied" in text


@pytest.mark.parametrize(
    "mutation", ["revoked", "disabled", "corrupt", "missing", "expired", "rollback"]
)
def test_actual_restart_preserves_trusted_key_and_independent_revocation(
    tmp_path: Path,
    mutation: str,
) -> None:
    from claims_ai.security_hardening.probes import child_probe

    original = access()
    policy = VerificationPolicy(
        audience=API_AUDIENCE,
        tenant_id=uuid4(),
        application_id=uuid4(),
        subject=original.scope.principal.principal_id,
        role=IdentityRole.REVIEWER,
    )
    keys = LocalKeyRing(clock=lambda: EPOCH)
    public = keys.resolve(keys.current, EPOCH)
    assert public is not None
    pem = public.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    context = synthetic_context(policy, pem)
    credential = issue(keys, policy, (CASE,), now=EPOCH)
    grant = grant_for(original)
    if mutation == "expired":
        grant = grant.model_copy(update={"expires_at": EPOCH + 10})
    ledger = Lifecycle(
        tmp_path / "grants.sqlite3",
        context_sha256=context,
        integrity_key=KEY,
        create=True,
        clock=lambda: EPOCH,
    )
    ledger.issue(grant)
    before_bytes = ledger.path.read_bytes()
    anchor = ledger.checkpoint()

    def run(now: int = EPOCH) -> dict[str, object]:
        return child_probe(
            ledger.path,
            credential=credential,
            public_pem=pem,
            policy=policy.model_dump(mode="json"),
            integrity_key=KEY,
            grant=grant,
            anchor=anchor,
            now=now,
        )

    before = run()
    assert before == {"allowed": True, "signature_valid": True, "context_sha256": context}
    now = EPOCH
    if mutation in {"revoked", "rollback"}:
        ledger.revoke(grant.grant_id)
    if mutation == "disabled":
        ledger.disable(grant.principal_id)
    if mutation in {"revoked", "disabled", "rollback"}:
        anchor = ledger.checkpoint()
    if mutation == "rollback":
        ledger.path.write_bytes(before_bytes)
    if mutation == "corrupt":
        ledger.path.write_bytes(b"corrupted-state")
    if mutation == "missing":
        ledger.path.unlink()
    if mutation == "expired":
        now = EPOCH + 10
    after = run(now)
    assert after == {"allowed": False, "signature_valid": True, "context_sha256": context}
    assert credential.encode() not in (ledger.path.read_bytes() if ledger.path.exists() else b"")


def test_gateway_lifecycle_rechecked_on_genuine_sdk_requests(ledger: Lifecycle) -> None:
    from claims_ai.agent_tools.__main__ import demo_grant
    from claims_ai.agents.__main__ import demo_input
    from claims_ai.mcp_http.auth import SyntheticIssuer
    from claims_ai.mcp_http.contracts import VerifiedGateway
    from claims_ai.mcp_http.transport import HttpBoundary, protocol_roundtrip

    value = demo_input(SPEC, "valid-v1")
    tool_grant = demo_grant(value, "m21-gateway")
    issuer = SyntheticIssuer()
    identity = VerifiedGateway(issuer.subject, issuer.application)
    grant = Grant(
        grant_id=uuid4(),
        principal_id=identity.subject,
        identity_class=IdentityClass.GATEWAY,
        case_ids=(tool_grant.claim_id,),
        permissions=(Permission.MCP_READ,),
        binding_sha256=gateway_binding(identity, tool_grant),
        issued_at=EPOCH,
        expires_at=EPOCH + 300,
    )
    ledger.issue(grant)
    gateway = LifecycleGateway(issuer.verifier, ledger, grant, tool_grant, identity)
    credential = issuer.issue()
    assert gateway.verify(credential) == identity
    boundary = HttpBoundary(
        value, tool_grant, port=8765, gateway_subject=identity.subject, verifier=gateway
    )

    async def protocol() -> tuple[dict[str, object], int]:
        async with boundary.app.router.lifespan_context(boundary.app):
            report = await protocol_roundtrip(
                "http://127.0.0.1:8765/mcp",
                credential,
                value,
                transport=httpx2.ASGITransport(app=boundary.app),
            )
            ledger.revoke(grant.grant_id)
            async with httpx2.AsyncClient(
                transport=httpx2.ASGITransport(app=boundary.app)
            ) as client:
                rejected = await client.post(
                    "http://127.0.0.1:8765/mcp",
                    content=b"{}",
                    headers={
                        "Authorization": "Bearer " + credential,
                        "Content-Type": "application/json",
                    },
                )
            return report, rejected.status_code

    report, rejected_status = asyncio.run(protocol())
    tools, replies = report["tools"], report["replies"]
    assert isinstance(tools, list) and len(tools) == 3
    assert isinstance(replies, list) and len(replies) == 3
    assert all(reply["status"] == "ok" for reply in replies)
    assert rejected_status == 401 and gateway.verify(credential) is None
    with pytest.raises(LifecycleError):
        LifecycleGateway(
            issuer.verifier,
            ledger,
            grant.model_copy(update={"case_ids": (OTHER,)}),
            tool_grant,
            identity,
        )


def test_fixture_success_is_not_synthetic_access_authority() -> None:
    verifier, token = load_fixture(str(FIXTURES / "human_reviewer.json"))
    assert verifier.verify(token) is not None
    # Unsupported provider has no authority_kind; existing adapters refuse even a valid fixture.
    with pytest.raises((ValueError, AttributeError)):
        VerifiedCapabilities().issue(access(), token, verifier)  # type: ignore[arg-type]


def test_unanchored_reopen_and_create_over_existing_fail_closed(ledger: Lifecycle) -> None:
    with pytest.raises(LifecycleError):
        Lifecycle(ledger.path, context_sha256=CONTEXT, integrity_key=KEY, clock=lambda: EPOCH)
    original = ledger.path.read_bytes()
    with pytest.raises(FileExistsError):
        Lifecycle(
            ledger.path, context_sha256=CONTEXT, integrity_key=KEY, create=True, clock=lambda: EPOCH
        )
    assert ledger.path.read_bytes() == original


def test_signed_duplicate_json_and_missing_flow_cannot_be_identity(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
) -> None:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding

    verifier, control = signed_mutation(signed_fixture, {})
    claims, key, _ = signed_fixture
    header = jwt.utils.base64url_encode(b'{"alg":"RS256","typ":"JWT","kid":"fixture-0001"}')
    for raw in (
        json.dumps(claims)[:-1] + ',"roles":["Claims.Supervisor"]}',
        json.dumps({k: v for k, v in claims.items() if k != "scp"}),
    ):
        payload = jwt.utils.base64url_encode(raw.encode())
        message = header + b"." + payload
        signature = key.sign(message, padding.PKCS1v15(), hashes.SHA256())
        assert (
            verifier.verify((message + b"." + jwt.utils.base64url_encode(signature)).decode())
            is None
        )
    assert verifier.verify(control) is not None


def test_failing_safe_logging_denies_fixture_verification(
    signed_fixture: tuple[dict[str, Any], rsa.RSAPrivateKey, ProviderProfile],
) -> None:
    class UnavailableLogger(logging.Logger):
        def handle(self, record: logging.LogRecord) -> None:
            raise OSError("sensitive-handler-details")

    verifier, token = signed_mutation(signed_fixture, {})
    verifier._logger = UnavailableLogger("m21-unavailable", level=logging.INFO)
    assert verifier.verify(token) is None


def test_supplemental_attack_catalog_and_runtime_evidence() -> None:
    from claims_ai.adversarial.contracts import CaseResult
    from claims_ai.security_hardening.evaluation import evaluate

    report = evaluate(FIXTURES)
    assert report["counts"] == {"PASS": 25, "FAIL": 0, "NOT_TESTED": 0}
    results = report["results"]
    assert isinstance(results, list) and len(results) == 25
    assert all(CaseResult.model_validate(row).observed.execution == "RUNTIME" for row in results)
    assert report["completed_subprocesses"] == 14


def test_locked_lifecycle_denies_bound_access_without_fallback(ledger: Lifecycle) -> None:
    original = access()
    inner = SyntheticAuthenticator()
    token = inner.issue(original)
    grant = grant_for(original)
    ledger.issue(grant)
    gate = LifecycleAuthenticator(inner, ledger, target="api")
    gate.bind(token, grant)
    assert gate.verify(token) is original
    with sqlite3.connect(ledger.path) as connection:
        connection.execute("BEGIN IMMEDIATE")
        assert gate.verify(token) is None
        connection.rollback()
    assert gate.verify(token) is original


def test_api_and_outcome_resource_grants_cannot_be_interchanged(ledger: Lifecycle) -> None:
    original = access()
    inner = SyntheticAuthenticator()
    token = inner.issue(original)
    grant = grant_for(original, target="api")
    ledger.issue(grant)
    gate = LifecycleAuthenticator(inner, ledger, target="outcomes")
    with pytest.raises(LifecycleError):
        gate.bind(token, grant)
    assert gate.verify(token) is None
