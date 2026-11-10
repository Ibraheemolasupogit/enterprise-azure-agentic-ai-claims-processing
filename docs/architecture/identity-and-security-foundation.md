# Identity and security foundation — M18

Status: implemented **offline synthetic** verification and host binding; Entra/Azure integrations are target architecture only. [M18 evidence](../milestones/milestone-18.md), [identity ADR](decisions/0002-identity-verification-and-host-authority.md), [M14](mcp-http-and-gateway.md), [M15](governed-human-review.md), [M16](governed-fastapi-application.md) and [M17](governed-reviewer-ui.md) define the acceptance boundaries. No tenant, app registration, group, role assignment or cloud resource is created.

## Target identities and trust boundaries

The proposed deployment uses one explicitly allowed Entra tenant per environment, separate resource audiences for the claims API and MCP backend, and separate confidential browser, API, gateway and processing application identities. Names and permissions below are proposals, not registered resources.

| Identity / boundary | Target requirement | Current offline implementation |
| --- | --- | --- |
| Human reviewer / supervisor → browser BFF → claims API | Tenant-specific OIDC authorization-code flow with PKCE and exact HTTPS redirect URIs. Server-held tokens, delegated review scope, authorized client application, verified tenant/object identity and exact application role. Reviewer and supervisor assignments remain independent case/task grants | One-use host enrollment and opaque local sessions; optional signed synthetic identity exchange into an existing API capability |
| Intake/processing workload → claims API | Dedicated workload identity, exact API audience and narrow intake/processing application permission. No delegated human role or recommendation-decision permission | Synthetic HOST principal and exact `Claims.Intake` policy; existing ApiScope determines permitted operations/cases |
| MCP caller → APIM → MCP backend | Gateway validates the permitted client token; backend independently verifies the gateway service identity and exact backend audience/role. Original workflow case grant is independently host-selected | Synthetic MCP machine policy and GatewayIdentityAdapter; unchanged M14 transport still requires its configured gateway subject and M11 case grant |
| Reviewer → recommendation decision | Verified human mapped to a canonical host session and explicit current M15 assignment; no token claim can construct a session, assign a case or override separation of duties | Existing canonical ReviewSession object identity, assignments, producer/fact-author separation, supervisor routing, exact snapshots and CAS remain authoritative |
| API/worker → Azure data/model services | Separate managed identities with resource-specific, minimal data-plane access; no agent secret administration, policy publication or control-plane rights | No Azure credential chain, SDK identity client, service token acquisition or model call added |
| Policy publication / operator / deployment | Separate future policy-publisher and deployment identities. Operators have health access without blanket case access; protected GitHub OIDC subjects and environments bound to deployment permissions | Design only; no new operational role, grant or API is implemented |

For the future Entra v2 profile, require an exact tenant-specific issuer and resource audience; validate signature/key trust, `tid`, `oid`, authorized client (`azp` in the selected v2 profile), token lifetime and exact configured role/permission sets. The target uses stable tenant/object mapping rather than display names/email or a subject shared across applications. Configure and verify workload token-type evidence and authorized application identities; absence of an app marker alone never proves a human. A human review session requires verified delegated flow/scope and canonical human registration. Group IDs, caller headers and JSON role fields do not substitute for that mapping. Multi-role membership needs an explicitly governed active role and separation-of-duties policy, not automatic supervisor promotion.

Managed identity authenticates a service, not a reviewer. Replacing an incoming human Authorization header with APIM's service token does not preserve human authority. Any future human API gateway path needs a separately verified delegated/OBO design; plaintext forwarded identity headers are prohibited. M14's MCP service path remains governed **read-only** and never becomes a review-action path. No claim approval, denial, payment, settlement or autonomous outcome role is introduced.

## Implemented reusable verification

`IdentityVerifier` and `KeyDiscovery` explicitly declare authority kind. `SyntheticTokenVerifier` only accepts the reserved local issuer `https://northstar.invalid/identity/v1`, host-loaded RSA keys and synthetic claims. `UnconfiguredEntraVerifier` always returns no identity and performs no discovery or fallback. A local signature, role or `authority` field cannot become proof of Entra sign-in.

The synthetic token profile has an exact claim set: `iss`, single-string `aud`, `tid`, `azp`, canonical UUID `sub`, `principal_kind`, singleton `roles`, unique bounded `case_ids`, `authority`, integer `iat`/`nbf`/`exp` and UUID `jti`. Policy pins tenant, application, subject, audience and exact role. Human roles map to the unchanged M2 reviewer/supervisor enum; HOST and MCP roles map to separate machine kinds. Duplicate JSON members, renamed/unrelated claims, extra roles, wildcard/duplicate scope, noncanonical UUIDs, booleans/floats/strings as dates and unexpected claim/header fields fail closed.

Only `RS256`, `typ=at+jwt` and a bounded local `kid` are allowed. Header-supplied `jku`, `jwk`, `x5u`, `crit` or alternative algorithms are rejected before discovery. The resolved key must be an RSA public-key object of at least 2048 bits. The pinned PyJWT 2.15.1 and cryptography 50.0.2 packages already exist; no dependencies are added. Typed claims and actual signature verification both run. A correctly signed credential with the wrong issuer/audience/role still fails.

Expiry is exclusive: `iat <= now < exp`, `nbf == iat`, lifetime at most 300 seconds, zero clock skew in this synthetic profile. No wall-clock rounding grace is added. Clock rollback/invalid clock values latch the verifier closed; transient verification/discovery exceptions deny that request. No raw failure text reaches callers or logs.

## Authentication does not create authorization

The host calls `VerifiedCapabilities.issue` with the signed credential, configured verifier and **independently constructed ApiAccess**. Principal and exact case tuple must match; human access must contain an existing ReviewSession. The adapter never deserializes or creates a human session from claims. M15 still rejects a copied, otherwise identical session. Signature verification alone cannot assign a task, broaden case access or enable HOST/MCP/agent/model review.

The host exchange yields a 43-character opaque capability. JWTs never enter browser fields/cookies, URLs or the API's bearer wire profile. No token-exchange/login/administration endpoint is added; the API's existing 256-byte Authorization/header/body budgets are unchanged. On **every** API use, the adapter verifies the original signed credential again and checks equality with its host-bound identity. Rotation, expiry, token/principal revocation and failed discovery therefore invalidate existing capabilities; duplicate review receipts cannot bypass this recheck. Existing M15 authorizations still run afterward.

The default M16 `SyntheticAuthenticator` now uses the same bounded opaque-capability store: 64 active records, absolute 900-second monotonic expiry, collision rejection and host revocation. Bad/rolled-back monotonic clocks close the store until restart. The signed adapter's opaque receipt lives at most 300 monotonic seconds and additionally depends on JWT/key/revocation validity. These are distinct synthetic profiles; the signed adapter is exercised in M18, while existing M16/M17 demonstrations retain their documented opaque host profile with the new expiry check.

The M17 host now checks underlying credential validity during enrollment and session use. Host-only methods can terminate one UI cookie or all current UI sessions/enrollment codes for a profile. This does not revoke the underlying API capability or prevent later explicit host reprovisioning; revoke that capability or signed verifier to disable access. Failed profile validation clears related sessions/codes. Codes remain one-use/five minutes, active UI sessions 15 absolute monotonic minutes, with existing CSRF, rotation, form-ticket and capacity checks. The earliest API/identity expiry can end a UI session sooner.

## Rotation, revocation and discovery model

| Control | Offline enforcement | Production requirement |
| --- | --- | --- |
| Key publication/rotation | In-memory local discovery; four retained keys, eight generations per process, fresh 2048-bit RSA/65537, no `kid` reuse within the ring. Keys valid for 600 wall-clock seconds; new key becomes current while old keys can overlap | Trusted tenant-specific discovery; atomic cache publication, validated HTTPS/certificates, approved issuers/key usage/algorithms and bounded cache size/age |
| Retirement/unknown key | Host retirement immediately removes a key; all credentials signed by it fail. Unknown/expired keys fail without a fetch or alternate verifier | Planned overlap bounded by token lifetime; immediate compromise retirement; no attacker-driven URL or unbounded unknown-key refresh storm |
| Token revocation | Per-verifier set of 64 UUID `jti` values, retained for process lifetime. Exhaustion closes the verifier instead of evicting revocations | Shared durable revocation/session state and cross-worker invalidation; approved retention and continuous-access policy integration require real validation |
| Principal disable | Host closes that configured verifier; all capabilities using it fail | Central tenant/object disable mapped to every relevant verifier/session and host grant; no claim of global directory revocation from one local instance |
| Process restart / outage | Keys, tokens, capabilities, UI state and review audit disappear; no import/recovery path. Verification failure never falls back to another authority | Durable trusted revocation/key lifecycle and recovery procedures; fail closed when trusted discovery expires or cannot be established |

Authorization is evaluated at request start and again for existing M15 assignment/snapshot checks. Revocation does not promise cancellation of work already admitted, instantaneous global propagation, atomic identity-and-case transactions or protection from a trusted OS user replacing private memory/code. Host-loaded resolver/verifier implementations are trusted code, not an untrusted plugin sandbox. Key retirement can invalidate other principals sharing that key; refresh requires explicit host-issued credentials and independent grants.

## Cookies, CSRF, transport and secrets

The implemented browser profile remains exact IPv4 loopback **HTTP** with HttpOnly, SameSite=Strict, host-only path `/` cookies, exact Origin/Host/peer checks, CSRF nonces and no proxy trust. It does not enable Entra, TLS, remote origins or secure production cookies. No UI/API/MCP transport is redesigned. `ProductionCookieRequirements` is a tested **target-only** contract requiring `__Host-` naming, Secure, HttpOnly, Strict, path `/`, no Domain and TLS; it is not a selectable deployed UI profile. Future BFF hosting also needs exact redirect/CSRF/logout/session fixation checks, HSTS and trusted-ingress validation before exposure.

Signing keys and credentials remain ephemeral private memory; no key, JWT, capability, enrollment code, browser cookie or secret is written to M18 evidence. Do not place tokens in URLs, local storage, source, environment dumps, logs or generated reports. Future secrets/certificates require Key Vault with separate least-privilege runtime and rotation administration. Entra verification public keys come from trusted Entra discovery, not an arbitrary Key Vault signing key or token header. Managed identity is preferred for service access where supported; no automatic Azure credential chain is activated offline.

Future private ingress, private endpoints/DNS and egress allowlists must be validated for the selected service/tier. Restrict direct backend ingress to the approved gateway/BFF path, retain backend identity/case checks and disable blind forwarded-header trust. Network isolation does not grant reviewer authority. Key Vault, Entra, APIM, managed identity, private networking and TLS enforcement remain unprovisioned and untested live.

## Audit, evidence and threat assumptions

Verification emits the existing redacted JSON format with an allowlisted identity-verification event and fixed success/denied status only. API verification inherits its validated request UUID correlation. No claims, subject, role list, token, key, URL, payload or exception text is recorded. An exception raised by the logging call denies verification; handler delivery/retention is not acknowledged. These events are not a retained security audit: durable denial telemetry, incident correlation, signing/retention and approved operator access remain production requirements. M15's accepted-action audit still records canonical actors and exact snapshot bindings in its original immutable, process-local journal.

Attacker assumptions include arbitrary HTTP/form/JWT inputs, spoofed role/case headers, wrong/expired/revoked tokens, signed-but-unapproved claim combinations, header key/algorithm confusion, cross-case attempts, stale/replayed actions and unavailable key discovery. The local host, key publication, API grants, canonical session delivery and OS remain trusted. Host compromise, stolen synthetic human capability, durable replay across restored state, live Entra/conditional-access behavior and adversarial production ingress are outside this evidence. No synthetic identity proves that a real human acted.

The [M18 evidence](../milestones/milestone-18.md) records actual ASGI API/UI and genuine MCP Streamable HTTP SDK execution with socket calls blocked in a test. No network/provider call, real browser/TLS/tenant verification or live APIM enforcement is inferred. Existing APIM XML remains a statically validated reference. M8's four failures, M12 timing-dependent retry/reproduction and M15/M17 volatile storage/accessibility limitations remain. Added identity modules extend whole-package fingerprints and future task IDs; historical artifacts are preserved.

## Reproduction and future references

```sh
make identity-check
PYTHONPATH=src .venv/bin/python -m claims_ai.identity --output outputs/identity/new-report.json
```

Use a new output outside reference data. Full environment: `.[dev,mcp,ui,identity]` constrained by [M18](../../requirements/m18-constraints.txt), retaining the prior 37 pins. No package download is needed for the current environment. M18 supersedes the older roadmap's planned RAG/rules scope by explicit user instruction; that work remains deferred, with no M19 implementation.

Future implementation references, **not fetched or validated online in this offline milestone**: [Microsoft identity platform](https://learn.microsoft.com/en-us/entra/identity-platform/), [workload identities](https://learn.microsoft.com/en-us/entra/workload-id/workload-identities-overview), [managed identities](https://learn.microsoft.com/en-us/entra/identity/managed-identities-azure-resources/overview), [Key Vault security](https://learn.microsoft.com/en-us/azure/key-vault/general/security-features). Tenant/token semantics, service support, permissions and deployment assumptions require separate authorized live verification.
