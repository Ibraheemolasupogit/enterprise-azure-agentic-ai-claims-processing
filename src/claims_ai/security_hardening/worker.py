"""Offline restart probe: trusted harness supplies public context/fresh authority via stdin.

Not a login, recovery or administration endpoint. No private signing key is needed;
old credentials are independently verified with the SAME preserved public key.
"""

import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from claims_ai.api.auth import ApiAccess
from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.__main__ import demo_sessions
from claims_ai.identity.adapters import VerifiedCapabilities
from claims_ai.identity.contracts import AuthorityKind, VerificationPolicy
from claims_ai.identity.verification import SyntheticTokenVerifier
from claims_ai.security_hardening.bindings import LifecycleAuthenticator
from claims_ai.security_hardening.contracts import Anchor, Grant
from claims_ai.security_hardening.lifecycle import Lifecycle
from claims_ai.security_hardening.providers import synthetic_context


class PreservedPublicKey:
    authority_kind = AuthorityKind.SYNTHETIC

    def __init__(self, key: rsa.RSAPublicKey) -> None:
        self.key = key

    def resolve(self, kid: str, now: int) -> rsa.RSAPublicKey | None:
        return self.key if kid == "local-0001" else None


def main() -> None:
    try:
        raw = sys.stdin.buffer.read(65537)
        if len(raw) > 65536:
            raise ValueError("probe capacity")
        data = json.loads(raw)
        public_pem = data["public_key"].encode()
        key = serialization.load_pem_public_key(public_pem)
        if not isinstance(key, rsa.RSAPublicKey):
            raise ValueError("public key required")
        policy = VerificationPolicy.model_validate(data["policy"])
        context = synthetic_context(policy, public_pem)
        verifier = SyntheticTokenVerifier(
            policy, PreservedPublicKey(key), clock=lambda: data["now"]
        )
        signed = verifier.verify(data["credential"])
        result = {
            "signature_valid": signed is not None,
            "allowed": False,
            "context_sha256": context,
        }
        if signed is None:
            raise ValueError("invalid trusted context")
        sessions = demo_sessions()
        session = sessions[data["actor"]]
        access = ApiAccess(
            ApiScope(principal=session.principal, claim_ids=tuple(data["case_ids"])), session
        )
        inner = VerifiedCapabilities()
        token = inner.issue(access, data["credential"], verifier)
        try:
            lifecycle = Lifecycle(
                Path(data["database"]),
                context_sha256=context,
                integrity_key=bytes.fromhex(data["integrity_key"]),
                anchor=Anchor.model_validate(data["anchor"]),
                clock=lambda: data["now"],
            )
            gate = LifecycleAuthenticator(inner, lifecycle, target="api")
            gate.bind(token, Grant.model_validate(data["grant"]))
            result["allowed"] = gate.verify(token) is access
        except Exception:
            pass
        print(json.dumps(result, sort_keys=True))
    except Exception:
        print('{"probe_error":true}')
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()
