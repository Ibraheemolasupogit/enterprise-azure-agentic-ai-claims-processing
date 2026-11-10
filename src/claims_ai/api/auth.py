"""Opaque ephemeral synthetic credentials; this module performs no Entra/OAuth/JWT work."""

from collections.abc import Callable
from dataclasses import dataclass
from time import monotonic
from typing import Protocol

from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.contracts import PrincipalKind, ReviewSession
from claims_ai.identity.capabilities import Capabilities


@dataclass(frozen=True, eq=False)
class ApiAccess:
    scope: ApiScope
    review_session: ReviewSession | None = None

    def __post_init__(self) -> None:
        ApiScope.model_validate(self.scope)
        if self.review_session is not None and (
            self.scope.principal.kind != PrincipalKind.HUMAN
            or self.scope.principal != self.review_session.principal
        ):
            raise ValueError("review session must match the canonical synthetic human")


class Authenticator(Protocol):
    def verify(self, token: str) -> ApiAccess | None: ...


class DenyAll:
    def verify(self, token: str) -> None:
        return None


class SyntheticAuthenticator:
    """Host-only issuance, finite hash registry and explicit revocation; never an API endpoint."""

    def __init__(self, *, timer: Callable[[], float] = monotonic) -> None:
        self._store: Capabilities[ApiAccess] = Capabilities(timer=timer)

    def issue(self, access: ApiAccess) -> str:
        return self._store.issue(access)

    def revoke(self, token: str) -> None:
        self._store.revoke(token)

    def verify(self, token: str) -> ApiAccess | None:
        return self._store.resolve(token)
