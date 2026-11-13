# Required cloud adapters — not implemented

This is a requirements/acceptance contract, not an adapter implementation or permission to contact a service. All seven adapter states in [the foundation contract](../../../deployment/contract.json) are NOT_IMPLEMENTED. No cloud SDK/driver/exporter is added. Any future dependency proposal must record exact versions, full closure, Linux hashes/licences, vulnerability review and isolated installation before implementation. Current M22 pins stay unchanged.

## Cloud host and identity/session binding

Add a separate explicitly configured hosting profile; do not loosen M14/M16/M17 loopback/Host/Origin/proxy checks globally or bind their demo launchers publicly. Require approved hostnames, TLS, a trusted ingress/proxy boundary, secure HttpOnly `__Host-` UI cookies, CSRF/origin checks, original request byte/response/concurrency limits and bounded genuine dependency-readiness checks. UI-to-API transport must make actual authenticated HTTP calls rather than imply TestClient is cloud transport. A successful liveness probe is not dependency/identity readiness.

Real Entra verification must use the selected provider/token-flow semantics, exact tenant/issuer/audience/client, allowed algorithms and trusted bounded discovery/rotation. Do not reuse the fixture's artificial exact claim set as a live verifier, convert a validated fixture into `VerifiedIdentity`, or fall back to synthetic credentials. Human delegated sign-in and app-only workload identity remain distinct. Review token transport/header limits explicitly; do not forward a JWT through an opaque-capability path that cannot accept it or simply widen every default limit.

Map actual verified human identity to independently trusted canonical sessions and current case/task assignments. The shared session/revocation design must explain process restart, cookie expiry, fresh canonical object creation and multiple replicas. A stored JSON role/session or an equal copy cannot replace M15 canonical authority. Persist only approved session metadata under an explicit schema; credentials/tokens/cookies/private keys remain outside case/audit payloads. Retained historical actors are evidence, never current grants. Claims, traces, tools, model output or operator/deployer identities cannot assign reviewers, make human outcomes or create publication permits.

MCP has two authentication hops: client to APIM and APIM MI to backend with separate audiences/app permissions. Remove spoofed identity/grant/forwarded headers before backend credential generation. The backend independently verifies the service token and a trusted, current case-bound ToolGrant. The three reads remain the whole tool surface. A subscription key, MI token or gateway role alone does not supply case scope. No automatic user/OBO design is invented by the app-only M14 policy.

Required future tests: legitimate real user/workload controls; wrong issuer/tenant/audience/client/role; human-machine confusion; expiry/rotation/discovery failure; copied sessions; cross-case access; revoked duplicates after restart; grant/trace/header forgeries; direct-backend bypass; secure cookies, CSRF and real UI/API/MCP TLS/streaming. Failures must deny without sensitive claim/token logging.

## PostgreSQL durability and authority

Preserve M20's transactional semantics: case projection, assessment/decision, canonical assignment, audit, receipt and outbox updates must commit atomically or roll back. Exact expected revisions/bindings and current authorization precede duplicate receipt lookup; competing writers have one winner. A lost acknowledgement returns the same authorized receipt, not a second decision. Never turn M9 provisional findings or M15 recommendation approval into an operational assessment/publication.

Define a new explicit cloud schema/version and a reviewed compatibility protocol. SQLite's exact DDL/triggers, FULL/DELETE journal, file ownership checks and process-local locks are not a PostgreSQL adapter. Database identity must be schema-scoped and incapable of creating application human authority. Establish Entra database administration separately; none is supplied by the Bicep. No password/shared-key fallback is allowed.

Retain original byte-bearing approved sources, hashes/versions, independent principal/source registry, current grant checks and externally protected rollback anchors/integrity context. An anchor stored only alongside the database it is meant to validate is not independent. Define whether revocation is admission-only or atomic through business commit; current M21 cross-store checks do not establish global atomic revocation. Any stronger guarantee requires an explicit shared-transaction/version fence and concurrency evidence.

Required future tests: independent concurrent writers; stale CAS; before/after commit crashes; lost acknowledgements; audit-write failure; exporter plus SQL failure; corruption/coherent rollback against an independent current anchor; revoked identity duplicate denial after fresh recovery; missing/incompatible schema/source/key/principal rejection. Audit sampling is forbidden. Cloud/PITR/power-loss/distributed guarantees remain NOT_TESTED until actually exercised.

## Blob evidence and policy artifacts

Use per-environment private containers, Entra data-plane permissions, HTTPS, no public access/shared keys and exact case/document ownership. Treat version ID, immutable bytes and SHA-256 as explicit provenance. Quarantine unverified content; an upload or a storage scan flag is not evidence admission or a policy owner's approval. The minimum slice uses pre-registered synthetic fixtures only; no arbitrary user upload, live malware scanner or real customer data path is supplied.

Blob and SQL are not one transaction. Specify the ordering: store/verify an immutable byte version before a SQL commit references it, enforce retention/permissions preventing premature removal, and handle orphaned blobs separately. Never acknowledge a business state referencing unverified/missing bytes. Corrected evidence creates a new version and invalidates stale assessments/assignments; do not overwrite original evidence to make replay pass. Policy/rule/index activation must remain exact-version and independently approved.

Required future tests: wrong case/version/hash, missing/deleted/changed bytes, cross-container permissions, failed writes before SQL commit, orphan cleanup, denied unverified admission and restore of exact source versions. Retention, soft delete, legal hold and backup expiry are owner decisions; template retention candidates are not approval.

## Service Bus and transactional outbox

The relay reads only committed SQL outbox entries and sends a bounded metadata envelope with a stable audit/event ID, exact source/version bindings and safe correlation. Publishing is not a human decision. Consumer effects must use durable deduplication/idempotency; broker duplicate detection is defense in depth and does not establish distributed exactly-once delivery.

Persist M20's finite application retry budget and dead state across restarts/redelivery. Broker `maxDeliveryCount=3` does not replace the application budget or permit multiplying it by retries at every layer. Use bounded lock/renewal, deadlines, backoff and DLQ escalation; never reset attempts through a new host/process. Complete/acknowledge only after the intended durable local effect. Neither delivery metadata nor a replayed message restores current human/session/grant authority.

Required future tests: queue outage/throttle; duplicate/reordered delivery; lock expiry; relay death before send/after send/before ack; consumer death before/after effect; exhausted retries/DLQ surviving restart; corrupt/out-of-scope envelope and revoked current authority. External notifications/payments remain excluded.

## Cloud observability and network integration

Reuse M22 manual SDK instrumentation, allowlisted fields, bounded cardinality and safe exception handling. A cloud exporter must be separately reviewed and installed; no resource configuration or imported SDK may auto-enable export. Define bounded buffers/flush deadlines/drop counters, private Monitor ingestion/DNS, retention/caps, alert owner/action routing and safe shutdown. Monitor Private Link Scope/DNS/collector and executable cloud alert rules/action groups are not supplied by current workspace/component definitions.

Never export source documents, evidence/narratives, prompts/responses, JWTs/cookies/keys, identity claims, signed URLs or arbitrary baggage/errors. Inspect actual Azure query results and diagnostic inheritance for leakage, including API Management global settings. Telemetry loss must be visible and cannot change a business decision or erase mandatory audit; M21 mandatory safe identity logging failure remains fail-closed. Test actual positive/negative alerts and separately approved notification delivery; local snapshot threshold tests are not cloud notification evidence.

Private CA DNS, platform egress, APIM private-endpoint/public-disable sequencing and PostgreSQL private endpoint support require actual approved environment validation. No manual DNS guess, public endpoint, broad internet egress or direct-backend route may be used as a shortcut.

## Quality and scope

All M22 v1 candidates remain PENDING_REVIEW; no independent quality result or blind benchmark is released. Review the separate independent packet/exposure assessment and authenticate real adjudication before future scoring. A narrow infrastructure-only test requires an explicit owner-approved scope exception preserving NOT_TESTED quality metrics; it is not a quality-release waiver. Keep model/OCR/Search capabilities unavailable, existing policy rules provisional, and actual insurance authority false. No M24 readiness claim follows.
