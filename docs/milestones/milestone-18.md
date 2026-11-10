# Milestone 18 — Identity and security foundation

Status: **COMPLETE within the offline identity/security-foundation scope**. Production-oriented identity/trust design with bounded offline synthetic enforcement. No live Entra provider, cloud deployment, identity provisioning or autonomous insurance outcome. Verification date: 2026-11-10.

## Scope and files

The explicit M18 request supersedes the previous roadmap's proposed version-aware RAG/rules milestone. No RAG/rule work or M19 implementation is included.

Seven modules under `src/claims_ai/identity/`: contracts/provider distinctions, reusable opaque capabilities, local signing-key discovery/rotation, strict signed verification/revocation, independent host-bound API/MCP adapters, offline evidence CLI and initializer. New [identity/security tests](../../tests/test_identity.py), [architecture/threat model](../architecture/identity-and-security-foundation.md), [ADR-0002](../architecture/decisions/0002-identity-verification-and-host-authority.md) and nested M18 constraints.

Narrow existing changes: API synthetic capabilities gain absolute expiry/revocation; API verification receives request correlation; M14's legacy verifier gains exact single audience, strict integer/time/header checks; UI sessions gain optional credential checks and host termination, with the existing host wiring them in; existing UI seeding accepts a host credential override; structured logging gains one allowlisted event. Domain/lifecycle, rules, workflow, M15 authorizations/audit, API routes/OpenAPI, UI screens and MCP transport remain unchanged. Packaging, Makefile, README, architecture/security, traceability and roadmap are updated. Existing untracked M16/M17 dependency records are preserved.

## Implemented controls and target separation

Only host-loaded RSA/RS256 synthetic credentials are verified. Exact issuer/audience/tenant/application/subject/role, canonical UUIDs, human/machine kind, bounded unique case scope, strict integer dates, maximum 300-second lifetime and exclusive expiry are enforced. Duplicate JSON, extra/renamed claims, header-supplied keys/URLs, algorithm confusion, unknown/retired/weak keys and unconfigured real providers fail closed.

The host must independently bind verified identity to ApiAccess and its canonical M15 session; signature alone grants no case or action authority. The API wire token stays opaque/43 characters and its 256-byte Authorization limit is unchanged. Every use rechecks the original identity/key/revocation; M15 then checks assignment, supervisor, separation of duties and exact task/evidence/policy bindings. MCP has a distinct audience/machine role and retains its independent host case grant. No human review method is added to tools.

The default opaque API profile now expires after 900 monotonic seconds. UI enrollment/session validity can end earlier with underlying identity/capability expiry or revocation. Host-only cookie/profile termination does not impersonate or revoke an unrelated actor. Key rotation permits bounded overlap; retirement invalidates credentials; token revocation capacity exhaustion closes the verifier. Target-only secure-cookie/TLS requirements do not enable a live production transport.

The Entra architecture specifies human delegated and workload identities, role/claim requirements, audiences, trusted discovery, managed identities, Key Vault, private ingress/egress, session/revocation and audit requirements. `UnconfiguredEntraVerifier` returns no identity and makes no network call. No tenant/app/group/role exists as a result of M18. Live APIM enforcement remains distinct from static XML checks.

## Verification

| Verification | Result |
| --- | --- |
| Focused identity/security | **97 passed in 13.18 seconds**, including actual API/UI authorization, exact claims, revocation, expiry, canonical-session/case isolation and valid-signature confusion vectors |
| Existing focused API/UI/MCP regression | **197 passed in 123.16 seconds**; existing routes, review authority, UI and MCP behavior retained |
| Complete source pytest | **975 passed in 254.11 seconds**: 878 earlier cases plus 97 identity/security cases |
| Independent installed-wheel pytest | **975 passed in 275.62 seconds**, no warnings; Python isolated mode, separate installed target ahead of source and pytest source path replaced by that target |
| Ruff / strict mypy | Lint and formatting pass; strict mypy passes across **119 source/test Python files** |
| Dependencies | `pip check` passes; all **37** nested M18/M17/M16/M13/M10 pins match; **zero new distributions**. Optional identity extra declares the already installed PyJWT/cryptography pins |
| Packaging/import | Offline wheel and source distribution; all **96 Python runtime modules plus `py.typed`** match source and the independent installation. Normal isolated installed identity import succeeds outside the repository without `PYTHONPATH` |
| Existing API/APIM contracts | Current generated M16 OpenAPI is byte-identical to historical schema. APIM XML/Bicep invariant checks pass in **STATIC_ONLY_NOT_APIM_ENFORCEMENT** mode; templates/defaults remain unchanged |
| Reproducibility | Two source demonstrations and one independent installed-wheel demonstration produce byte-identical 15-scenario reports; no JWT, signing key, cookie, capability or code is serialized |
| Preservation/documentation | All **161** reference data files, existing tests and historical milestone records match their starting bytes; **23** earlier report/schema artifacts and existing untracked M16/M17 dependency records are unchanged. **441** local links resolve and **20** named M18 test references exist |

Reports: `outputs/identity/m18-verified-a.json`, `m18-verified-b.json` and `m18-verified-wheel.json`; common SHA-256 **`4a706e2ec18a56b9fd66181e9754735c78987a27f0cb9f9d1ff44e641ed3819a`**. `outputs/identity/m18-reproduction-verification.json` records equality. Reports label synthetic authority, real in-process API/UI/MCP ASGI rather than TCP, volatile storage and zero Azure/network/live-provider/model/autonomous-outcome operations. Socket connection and binding attempts are counted and prohibited in the complete demonstration regression.

Package artifacts are under `outputs/packages/m18/`; `package-verification.json` records archive/source/installed-byte checks and artifact hashes. Independent tests share the pinned dependency environment. Historical CLI reproduction tests retain deliberate source-launch paths; the M18 CLI is separately launched outside the repository against the independent package target and produces identical evidence. No editable installation is relied on.

The cryptographic negatives use valid RSA signatures for duplicate-member/header vectors and a manually constructed HMAC/public-key confusion vector: installed PyJWT itself refuses to construct that insecure HMAC token. The duplicate-member regression confirms PyJWT's default last-value interpretation would otherwise validate before asserting rejection by the stricter profile. Network-forbidden tests count attempted connections in addition to raising, so a caught networking exception cannot produce a false pass. A correctly signed 1024-bit key is deliberately rejected; its expected issuer-side warning is asserted.

The M14 external TCP report is preserved as historical M14 evidence. M18's stricter legacy authentication file changes that profile's processor fingerprint; the old report is not represented as fresh TCP verification of M18 authentication. Current M18 protocol evidence is ASGI only, with no network calls.

## Limits and acceptance boundary

All issuers, keys, grants, revocations, sessions and audit remain synthetic/process-local. Revocation is scoped to configured verifier/capability instances; directory-wide invalidation, durable/shared revocation, multiple workers, recovery and active-request cancellation are not proved. Entra signature/tenant discovery, delegated/OBO flows, conditional access, managed identity, Key Vault rotation, TLS/secure cookies, private networking and APIM runtime enforcement are target requirements only. No SDK credential chain or network discovery is activated.

The host/OS and resolver code remain trusted; a stolen/misdelivered human capability is not proof of real human identity. M15's canonical sessions and case assignments remain required. M8 Q-007/Q-012/Q-015/Q-029, M12 timing-dependent retry/report reproducibility, M15 volatile audit/persistence and M17 browser/accessibility limitations remain unchanged. Future task fingerprints change as source modules are added; earlier datasets/evaluations/reports remain preserved.

No Azure operations/spending, live external identity/network/model calls, autonomous claim approval/denial/payment/settlement, M19, staging, commits or pushes. **Stop after M18 for review.**
