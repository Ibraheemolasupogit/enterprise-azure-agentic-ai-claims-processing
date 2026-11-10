"""Real M18 verifiers and host exchanges; ephemeral credentials never enter evidence."""

import hmac
import json
from hashlib import sha256
from uuid import UUID, uuid5

import jwt

from claims_ai.adversarial.application import observed
from claims_ai.adversarial.contracts import AttackCase, Observation
from claims_ai.api.auth import ApiAccess, SyntheticAuthenticator
from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.__main__ import demo_sessions
from claims_ai.identity.adapters import VerifiedCapabilities
from claims_ai.identity.capabilities import Capabilities
from claims_ai.identity.contracts import API_AUDIENCE, IdentityRole, VerificationPolicy
from claims_ai.identity.keys import LocalKeyRing
from claims_ai.identity.verification import SyntheticTokenVerifier, issue

EPOCH = 1_800_000_000
NAMESPACE = UUID("19191919-1919-4919-8919-191919191919")
CASE = "NS-CLM-12345678"


def identity_probe(case: AttackCase) -> Observation:
    session = demo_sessions()["reviewer"]
    access = ApiAccess(ApiScope(principal=session.principal, claim_ids=(CASE,)), session)
    if case.attack in {"cap_expired", "cap_revoked", "capacity"}:
        now = [0.0]
        authority = SyntheticAuthenticator(timer=lambda: now[0])
        if case.attack == "capacity":
            store = Capabilities[str]()
            for _ in range(64):
                store.issue("bounded-synthetic-value")
            denied = False
            try:
                store.issue("must-not-evict")
            except ValueError:
                denied = True
            return observed(
                {"capacity_rejected": denied, "accepted_before_limit": 64},
                "Actual host capability store budget; not a distributed DoS test.",
            )
        token = authority.issue(access)
        before = authority.verify(token) is access
        if case.attack == "cap_expired":
            now[0] = 900
        else:
            authority.revoke(token)
        return observed(
            {"initially_valid": before, "verified": authority.verify(token) is not None}
        )
    keys = LocalKeyRing(clock=lambda: EPOCH)
    policy = VerificationPolicy(
        audience=API_AUDIENCE,
        tenant_id=uuid5(NAMESPACE, "tenant"),
        application_id=uuid5(NAMESPACE, "app"),
        subject=session.principal.principal_id,
        role=IdentityRole.REVIEWER,
    )
    verifier = SyntheticTokenVerifier(policy, keys, clock=lambda: EPOCH)
    token = issue(keys, policy, (CASE,), now=EPOCH, token_id=uuid5(NAMESPACE, case.case_id))
    if case.attack in {"wrong_issuer", "wrong_audience", "spoof_role", "expired"}:
        payload = jwt.decode(token, options={"verify_signature": False})
        if case.attack == "wrong_issuer":
            payload["iss"] = "https://attacker.invalid/issuer"
        elif case.attack == "wrong_audience":
            payload["aud"] = "api://attacker.invalid/resource"
        elif case.attack == "spoof_role":
            payload["roles"] = ["Claims.Supervisor"]
        else:
            payload["exp"] = EPOCH
        token = keys.sign(payload)
    public = keys.resolve(keys.current, EPOCH)
    if public is None:
        raise ValueError("local public key unavailable")
    if case.attack == "forged":
        parts = token.split(".")
        parts[2] = ("A" if parts[2][0] != "A" else "B") + parts[2][1:]
        token = ".".join(parts)
    elif case.attack == "key_confusion":
        signing = b".".join(
            jwt.utils.base64url_encode(json.dumps(value).encode())
            for value in (
                {"alg": "HS256", "typ": "at+jwt", "kid": keys.current},
                jwt.decode(token, options={"verify_signature": False}),
            )
        )
        from cryptography.hazmat.primitives import serialization

        der = public.public_bytes(
            serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo
        )
        token = (
            signing + b"." + jwt.utils.base64url_encode(hmac.new(der, signing, sha256).digest())
        ).decode()
    cryptographic_valid = False
    try:
        jwt.decode(
            token,
            public,
            algorithms=["RS256"],
            options={
                "verify_aud": False,
                "verify_exp": False,
                "verify_nbf": False,
                "verify_iat": False,
            },
        )
        cryptographic_valid = True
    except jwt.PyJWTError:
        pass
    initially_valid = verifier.verify(token) is not None
    if case.attack == "revoked":
        verifier.revoke_token(uuid5(NAMESPACE, case.case_id))
    if case.attack == "retired_key":
        old = keys.current
        keys.rotate()
        keys.retire(old)
    if case.attack == "scope_expansion":
        token = issue(keys, policy, (CASE, "NS-CLM-87654321"), now=EPOCH)
        denied = False
        try:
            VerifiedCapabilities().issue(access, token, verifier)
        except ValueError:
            denied = True
        return observed(
            {"valid_identity": verifier.verify(token) is not None, "host_exchange_denied": denied},
            "A signed identity cannot enlarge an independently constructed ApiScope.",
        )
    return observed(
        {
            "verified": verifier.verify(token) is not None,
            "cryptographic_valid": cryptographic_valid,
            "initially_valid": initially_valid,
        },
        (
            "Actual PyJWT/RSA signature and M18 policy/revocation checks; no "
            "token or key hash is retained."
        ),
    )
