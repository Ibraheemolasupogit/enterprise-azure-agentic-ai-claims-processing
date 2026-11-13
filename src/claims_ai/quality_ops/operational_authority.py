"""Synthetic acceptance-host composition using unchanged M20/M21 authority interfaces."""

from uuid import UUID, uuid5

from claims_ai.human_review.contracts import PrincipalKind
from claims_ai.models import ReviewerRole
from claims_ai.outcomes.demo import DemoHost
from claims_ai.security_hardening.bindings import LifecycleAuthenticator, access_binding
from claims_ai.security_hardening.contracts import Grant, IdentityClass, Permission
from claims_ai.security_hardening.lifecycle import Lifecycle, LifecycleError

EPOCH = 1800000000
CONTEXT = "8" * 64
INTEGRITY = b"M" * 32  # Known synthetic acceptance context, not a production credential.
NS = UUID("22222222-2222-4222-8222-222222222222")


def issue_grants(host: DemoHost, lifecycle: Lifecycle) -> dict[str, Grant]:
    grants = {}
    for name in ("host", "reviewer", "supervisor"):
        access = host.authenticator.verify(host.tokens[name])
        if access is None:
            raise ValueError("independent host access unavailable")
        principal = access.scope.principal
        kind = IdentityClass.REVIEWER
        permissions: tuple[Permission, ...] = (Permission.OUTCOME,)
        if principal.kind == PrincipalKind.HOST:
            kind, permissions = IdentityClass.PUBLISHER, (Permission.PUBLISH,)
        elif principal.role == ReviewerRole.SUPERVISOR:
            kind, permissions = IdentityClass.SUPERVISOR, (Permission.OUTCOME, Permission.SUPERVISE)
        grant = Grant(
            grant_id=uuid5(NS, name),
            principal_id=principal.principal_id,
            identity_class=kind,
            case_ids=access.scope.claim_ids,
            permissions=permissions,
            binding_sha256=access_binding(access, "outcomes"),
            issued_at=EPOCH,
            expires_at=EPOCH + 300,
        )
        lifecycle.issue(grant)
        grants[name] = grant
    bind_current(host, lifecycle, grants)
    return grants


def bind_current(host: DemoHost, lifecycle: Lifecycle, grants: dict[str, Grant]) -> None:
    gate = LifecycleAuthenticator(host.authenticator, lifecycle, target="outcomes")
    for name in ("host", "reviewer", "supervisor"):
        try:
            gate.bind(host.tokens[name], grants[name])
        except LifecycleError:
            if name != "reviewer":
                raise
    host.authority.authenticator = gate
