"""Verified identity is necessary, never sufficient: host grants and M15 sessions stay separate."""

from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic

from claims_ai.api.auth import ApiAccess
from claims_ai.human_review.contracts import PrincipalKind
from claims_ai.identity.capabilities import Capabilities
from claims_ai.identity.contracts import API_AUDIENCE, MCP_AUDIENCE, AuthorityKind, VerifiedIdentity
from claims_ai.identity.verification import IdentityVerifier
from claims_ai.mcp_http.contracts import VerifiedGateway


@dataclass(frozen=True)
class BoundIdentity:
    access: ApiAccess = field(repr=False)
    credential: str = field(repr=False)
    verifier: IdentityVerifier = field(repr=False)
    identity: VerifiedIdentity = field(repr=False)


class VerifiedCapabilities:
    """Host-only exchange into the existing 43-character API boundary; no new login endpoint."""

    def __init__(self, *, timer: Callable[[], float] = monotonic) -> None:
        self._store: Capabilities[BoundIdentity] = Capabilities(timer=timer)

    def issue(self, access: ApiAccess, credential: str, verifier: IdentityVerifier) -> str:
        identity = verifier.verify(credential)
        if (
            verifier.authority_kind != AuthorityKind.SYNTHETIC
            or identity is None
            or identity.authority_kind != AuthorityKind.SYNTHETIC
            or identity.claims.aud != API_AUDIENCE
            or identity.principal != access.scope.principal
            or identity.claims.case_ids != access.scope.claim_ids
            or identity.principal.kind not in {PrincipalKind.HUMAN, PrincipalKind.HOST}
            or identity.principal.kind == PrincipalKind.HUMAN
            and access.review_session is None
        ):
            raise ValueError("identity does not match independent host access")
        return self._store.issue(BoundIdentity(access, credential, verifier, identity), ttl=300)

    def verify(self, token: str) -> ApiAccess | None:
        binding = self._store.resolve(token)
        if binding is None:
            return None
        try:
            if (
                binding.verifier.authority_kind != AuthorityKind.SYNTHETIC
                or binding.verifier.verify(binding.credential) != binding.identity
            ):
                return None
            return binding.access
        except Exception:
            return None

    def revoke(self, token: str) -> None:
        self._store.revoke(token)


@dataclass(frozen=True)
class GatewayIdentityAdapter:
    verifier: IdentityVerifier = field(repr=False)
    case_ids: tuple[str, ...]

    def verify(self, credential: str) -> VerifiedGateway | None:
        try:
            identity = self.verifier.verify(credential)
            if (
                self.verifier.authority_kind != AuthorityKind.SYNTHETIC
                or identity is None
                or identity.authority_kind != AuthorityKind.SYNTHETIC
                or identity.claims.aud != MCP_AUDIENCE
                or identity.principal.kind != PrincipalKind.MCP
                or identity.claims.case_ids != self.case_ids
            ):
                return None
            return VerifiedGateway(identity.claims.sub, identity.claims.azp)
        except Exception:
            return None
