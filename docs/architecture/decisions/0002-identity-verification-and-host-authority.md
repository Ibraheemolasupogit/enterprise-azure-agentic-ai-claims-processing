# ADR-0002 — Separate verified identity from host-owned review authority

Status: accepted for the offline M18 foundation; production Entra/hosting remains planned. See [identity architecture](../identity-and-security-foundation.md) and [ADR-0001](0001-decision-authority.md).

## Context

M14 authenticates a synthetic gateway before independently checking a case grant. M15 accepts only canonical host-session objects and task assignments. M16/M17 expose those services with synthetic opaque capabilities and browser enrollment. A correctly signed token must not replace those independent authorization controls, and offline tests must not be presented as live Entra enforcement.

## Decision

Use explicit provider-kind verification/discovery interfaces with an offline local authority and an unavailable Entra seam. Pin the synthetic issuer, audience, application, tenant, subject, role, token type and key algorithm. Bound local key rotation/revocation and reject unknown keys without network discovery. Keep real-provider token profiles separate from synthetic claim formats.

Exchange a verified synthetic identity into an existing short opaque API capability only through trusted host code and an independently supplied ApiAccess. Retain the actual canonical ReviewSession; never create one from token claims. Reverify the original credential on every capability use. Preserve all M15 assignment, separation-of-duties, supervisor, snapshot, replay and concurrency guards and M14's independent case grant.

Give default API capabilities absolute expiry, expose host-only UI session termination and validate underlying credentials in the demo host. Keep existing loopback transports and request limits. Production secure-cookie/TLS requirements are a separate target contract, not an enabled network profile. Audit only approved status and correlation metadata.

## Consequences

No dependency, live identity, role provisioning, transport redesign or new outcome authority is required. Unknown/expired/revoked credentials and unavailable discovery fail closed. Keys, tokens, revocations and sessions remain bounded volatile memory; restart, cross-worker revocation, Entra discovery, real identity, private ingress and durable audit require later authorized work. Request-start revocation does not cancel already admitted operations. The trusted host/OS remains capable of replacing code/private state or misdelivering a human capability.
