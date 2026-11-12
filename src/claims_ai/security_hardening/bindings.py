"""Opt-in host composition at existing API/UI, outcome and MCP verification boundaries."""

from dataclasses import dataclass, field
from hashlib import sha256
from typing import Literal

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.api.auth import ApiAccess, Authenticator
from claims_ai.human_review.contracts import PrincipalKind
from claims_ai.mcp_http.auth import GatewayVerifier
from claims_ai.mcp_http.contracts import VerifiedGateway
from claims_ai.models import ReviewerRole
from claims_ai.rules.specification import digest
from claims_ai.security_hardening.contracts import Grant, IdentityClass, Permission
from claims_ai.security_hardening.lifecycle import Lifecycle, LifecycleError


def access_binding(access: ApiAccess, target: Literal["api", "outcomes"]) -> str:
    return digest({"target": target, "scope": access.scope.model_dump(mode="json")})


def required(
    access: ApiAccess, target: Literal["api", "outcomes"], grant: Grant
) -> frozenset[Permission]:
    scope, kind = access.scope, grant.identity_class
    if scope.principal.principal_id != grant.principal_id or scope.claim_ids != grant.case_ids:
        raise LifecycleError()
    if access_binding(access, target) != grant.binding_sha256:
        raise LifecycleError()
    if scope.principal.kind == PrincipalKind.HUMAN:
        supervisor = scope.principal.role == ReviewerRole.SUPERVISOR
        if kind != (IdentityClass.SUPERVISOR if supervisor else IdentityClass.REVIEWER):
            raise LifecycleError()
        if access.review_session is None:
            raise LifecycleError()
        permissions = {Permission.REVIEW if target == "api" else Permission.OUTCOME}
        if supervisor:
            permissions.add(Permission.SUPERVISE)
    elif scope.principal.kind == PrincipalKind.HOST and target == "outcomes":
        if kind != IdentityClass.PUBLISHER or scope.can_intake or scope.can_process:
            raise LifecycleError()
        permissions = {Permission.PUBLISH}
    elif scope.principal.kind == PrincipalKind.HOST and target == "api":
        if kind != IdentityClass.WORKLOAD or not (scope.can_intake or scope.can_process):
            raise LifecycleError()
        permissions = set()
        if scope.can_intake:
            permissions.add(Permission.INTAKE)
        if scope.can_process:
            permissions.add(Permission.PROCESS)
    else:
        raise LifecycleError()
    return frozenset(permissions)


@dataclass(frozen=True)
class AccessBinding:
    access: ApiAccess = field(repr=False)
    grant: Grant


class LifecycleAuthenticator:
    """No recovery of credentials: host binds fresh inner access to an existing ledger grant.

    Canonical session/assignment/permit checks remain in the existing application.
    Separate instances/resources prevent publication grants becoming intake authority.
    """

    def __init__(
        self, inner: Authenticator, lifecycle: Lifecycle, *, target: Literal["api", "outcomes"]
    ):
        if target not in {"api", "outcomes"}:
            raise LifecycleError()
        self.inner, self.lifecycle, self.target = inner, lifecycle, target
        self._bindings: dict[str, AccessBinding] = {}

    def bind(self, token: str, grant: Grant) -> None:
        access = self.inner.verify(token)
        if access is None or len(self._bindings) >= 64:
            raise LifecycleError()
        self.lifecycle.require(grant, required(access, self.target, grant))
        self._bindings[sha256(token.encode()).hexdigest()] = AccessBinding(access, grant)

    def verify(self, token: str) -> ApiAccess | None:
        try:
            if not isinstance(token, str) or len(token) > 8192:
                return None
            bound = self._bindings.get(sha256(token.encode()).hexdigest())
            if bound is None or self.inner.verify(token) is not bound.access:
                return None
            self.lifecycle.require(bound.grant, required(bound.access, self.target, bound.grant))
            return bound.access
        except Exception:
            return None


def gateway_binding(identity: VerifiedGateway, tool_grant: ToolGrant) -> str:
    return digest(
        {
            "subject": str(identity.subject),
            "application": str(identity.application_id),
            "tool_grant": tool_grant.model_dump(mode="json"),
        }
    )


class LifecycleGateway:
    def __init__(
        self,
        inner: GatewayVerifier,
        lifecycle: Lifecycle,
        grant: Grant,
        tool_grant: ToolGrant,
        identity: VerifiedGateway,
    ) -> None:
        if (
            grant.identity_class != IdentityClass.GATEWAY
            or grant.principal_id != identity.subject
            or grant.case_ids != (tool_grant.claim_id,)
            or grant.binding_sha256 != gateway_binding(identity, tool_grant)
        ):
            raise LifecycleError()
        self.inner, self.lifecycle, self.grant, self.identity = inner, lifecycle, grant, identity

    def verify(self, credential: str) -> VerifiedGateway | None:
        try:
            if self.inner.verify(credential) != self.identity:
                return None
            self.lifecycle.require(self.grant, frozenset({Permission.MCP_READ}))
            return self.identity
        except Exception:
            return None
