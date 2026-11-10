"""Opaque ephemeral synthetic credentials; this module performs no Entra/OAuth/JWT work."""

import re
import secrets
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.contracts import PrincipalKind, ReviewSession


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

    def __init__(self) -> None:
        self._tokens: dict[str, ApiAccess] = {}

    def issue(self, access: ApiAccess) -> str:
        if len(self._tokens) >= 64:
            raise ValueError("synthetic credential capacity exceeded")
        token = secrets.token_urlsafe(32)
        self._tokens[sha256(token.encode()).hexdigest()] = access
        return token

    def revoke(self, token: str) -> None:
        self._tokens.pop(sha256(token.encode()).hexdigest(), None)

    def verify(self, token: str) -> ApiAccess | None:
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", token) is None:
            return None
        return self._tokens.get(sha256(token.encode()).hexdigest())
