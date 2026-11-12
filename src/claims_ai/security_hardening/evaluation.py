"""M19-compatible supplemental attack evidence; historical catalog/reports stay unchanged."""

import json
import tempfile
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid5

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from claims_ai.adversarial.contracts import Catalog, Observation, Verdict, score
from claims_ai.api.auth import ApiAccess
from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.__main__ import demo_sessions
from claims_ai.identity.contracts import API_AUDIENCE, IdentityRole, VerificationPolicy
from claims_ai.identity.keys import LocalKeyRing
from claims_ai.identity.verification import issue
from claims_ai.security_hardening.bindings import access_binding
from claims_ai.security_hardening.contracts import Grant, IdentityClass, Permission
from claims_ai.security_hardening.lifecycle import Lifecycle
from claims_ai.security_hardening.probes import child_probe
from claims_ai.security_hardening.providers import (
    OfflineFixtureVerifier,
    PinnedKey,
    load_fixture,
    synthetic_context,
)
from claims_ai.workflow.engine import code_fingerprint

EPOCH = 1800000000
CASE = "NS-CLM-12345678"
NS = UUID("21212121-2121-4121-8121-212121212121")


def restart_observation(variant: str, completed: list[bool] | None = None) -> Observation:
    session = demo_sessions()["reviewer"]
    access = ApiAccess(ApiScope(principal=session.principal, claim_ids=(CASE,)), session)
    policy = VerificationPolicy(
        audience=API_AUDIENCE,
        tenant_id=uuid5(NS, "tenant"),
        application_id=uuid5(NS, "client"),
        subject=session.principal.principal_id,
        role=IdentityRole.REVIEWER,
    )
    keys = LocalKeyRing(clock=lambda: EPOCH)
    key = keys.resolve(keys.current, EPOCH)
    assert key is not None
    pem = key.public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    context = synthetic_context(policy, pem)
    credential = issue(keys, policy, (CASE,), now=EPOCH)
    integrity_key = b"T" * 32  # Explicit local test context; never used for runtime credentials.
    grant = Grant(
        grant_id=uuid5(NS, "restart-grant"),
        principal_id=session.principal.principal_id,
        identity_class=IdentityClass.REVIEWER,
        case_ids=(CASE,),
        permissions=(Permission.REVIEW,),
        binding_sha256=access_binding(access, "api"),
        issued_at=EPOCH,
        expires_at=EPOCH + (10 if variant == "expired" else 300),
    )
    with tempfile.TemporaryDirectory(prefix="northstar-m21-") as directory:
        ledger = Lifecycle(
            Path(directory) / "lifecycle.sqlite3",
            context_sha256=context,
            integrity_key=integrity_key,
            create=True,
            clock=lambda: EPOCH,
        )
        ledger.issue(grant)
        saved = ledger.path.read_bytes()
        anchor = ledger.checkpoint()

        def probe(now: int = EPOCH, signing_context: bytes = integrity_key) -> dict[str, object]:
            response = child_probe(
                ledger.path,
                credential=credential,
                public_pem=pem,
                policy=policy.model_dump(mode="json"),
                integrity_key=signing_context,
                grant=grant,
                anchor=anchor,
                now=now,
            )
            if completed is not None:
                completed.append(True)
            return response

        before = probe()
        now = EPOCH
        after_key = integrity_key
        if variant in {"revoked", "rollback"}:
            ledger.revoke(grant.grant_id)
        if variant == "disabled":
            ledger.disable(grant.principal_id)
        if variant in {"revoked", "disabled", "rollback"}:
            anchor = ledger.checkpoint()
        if variant == "corrupt":
            ledger.path.write_bytes(b"corrupt")
        if variant == "missing":
            ledger.path.unlink()
        if variant == "expired":
            now += 10
        if variant == "rollback":
            ledger.path.write_bytes(saved)
        if variant == "wrong_context":
            after_key = b"U" * 32
        after = probe(now, after_key)
    return Observation(
        execution="RUNTIME",
        facts={
            "positive_before": before["allowed"] is True,
            "signature_valid_after": after["signature_valid"] is True,
            "allowed_after": after["allowed"] is True,
            "preserved_context": before["context_sha256"] == after["context_sha256"] == context,
        },
        evidence_note="Two actual isolated subprocesses; same token/public key and profile; "
        "fresh independent host session/capability, lifecycle checked before access. "
        "No private RSA key is passed or regenerated in either child.",
    )


def evaluate(root: Path) -> dict[str, object]:
    manifest = json.loads((root / "manifest.json").read_bytes())
    if manifest["format"] != "m21-fixtures-v1" or set(manifest["files"]) != {
        "attacks.json",
        *(k.value + ".json" for k in IdentityClass),
    }:
        raise ValueError("untrusted fixture manifest")
    for name, expected in manifest["files"].items():
        if sha256((root / name).read_bytes()).hexdigest() != expected:
            raise ValueError("fixture integrity mismatch")
    catalog = Catalog.model_validate_json((root / "attacks.json").read_bytes())
    template, fixture_token = load_fixture(str(root / "human_reviewer.json"))
    fixture_claims = jwt.decode(fixture_token, options={"verify_signature": False})
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = OfflineFixtureVerifier(
        template.profile,
        {"fixture-0001": PinnedKey(private.public_key(), EPOCH, EPOCH + 600)},
        clock=lambda: EPOCH,
    )
    control = jwt.encode(
        fixture_claims, private, algorithm="RS256", headers={"kid": "fixture-0001"}
    )
    results = []
    completed: list[bool] = []
    for case in catalog.cases:
        try:
            if case.attack == "restart_lifecycle":
                observation = restart_observation(case.payload, completed)
            elif case.attack == "signed_profile_mutation":
                data = json.loads(case.payload)
                headers = {"kid": "fixture-0001"}
                if data["variant"] == "key-url":
                    headers["jku"] = "https://attacker.invalid/keys"
                signing_key = (
                    rsa.generate_private_key(public_exponent=65537, key_size=2048)
                    if data["variant"] == "wrong-key"
                    else private
                )
                malicious = jwt.encode(
                    {**fixture_claims, **data["changes"]},
                    signing_key,
                    algorithm="RS256",
                    headers=headers,
                )
                if data["variant"] == "algorithm-confusion":
                    malicious = jwt.encode(
                        fixture_claims, b"x" * 64, algorithm="HS256", headers=headers
                    )
                observation = Observation(
                    execution="RUNTIME",
                    facts={
                        "accepted": verifier.verify(malicious) is not None,
                        "legitimate_control": verifier.verify(control) is not None,
                    },
                    evidence_note="Actual signature and typed profile checks; negative claims "
                    "are signed by the same pinned key except explicit key/algorithm attacks.",
                )
            else:
                raise ValueError("unsupported authored attack")
        except Exception:
            observation = Observation(
                execution="NOT_EXECUTED",
                facts={},
                harness_error=True,
                unavailable_reason="Offline probe setup/execution failed; no protection claim.",
                evidence_note="Raw exceptions and credentials omitted.",
            )
        results.append(score(case, observation))
    counts = {v.value: sum(r.verdict == v for r in results) for v in Verdict}
    return {
        "format": "m21-security-supplement-v1",
        "simulated": True,
        "runtime_sha256": code_fingerprint(),
        "fixture_manifest_sha256": sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "counts": counts,
        "results": [r.model_dump(mode="json") for r in results],
        "completed_subprocesses": len(completed),
        "external_identity_calls": 0,
        "azure_operations": 0,
        "live_entra": "DISABLED",
        "production_security": "NOT_TESTED",
        "historical_m19_catalog_changed": False,
    }
