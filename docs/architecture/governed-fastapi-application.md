# Governed FastAPI application — M16

Status: implemented offline ASGI application and genuine FastAPI TestClient integration. No socket hosting, Entra authentication, Azure dependency readiness or operational claim outcome is established by M16. [M17](governed-reviewer-ui.md) separately supplies an offline browser presentation over these unchanged contracts. See [M16 evidence](../milestones/milestone-16.md) and [dependency provenance](../dependencies/fastapi.md).

## Existing authority behind a typed adapter

The factory `claims_ai.api.app.create_app` supplies a version-one application with deny-all authentication and no cases/services by default. The CLI explicitly constructs a synthetic host configuration and uses FastAPI's actual TestClient; importing the package never starts a listener, loads fixtures or issues credentials.

Host-owned `HostBundle` objects contain original M12 request bytes, workflow grants/limits and M15 human assignment plans. Bundles must begin at M2 RECEIVED/revision 1. HTTP intake accepts a bundle identifier and an exactly matching M2 `Claim`. This is admission of registered synthetic bundles, not arbitrary file upload, malware scanning, operational evidence admission or client-authorized policy selection. Clients cannot supply documents, scan assertions, policies, rules, workflow grants, roles or assignments. Unregistered cases remain unavailable.

Processing calls the existing M12 runner and independently replays its checkpoint using M12 `execution_key`/`restore` before publishing results. M15 admits the resulting advisory or complete-context supervisor exception and performs host-configured assignments through its existing public service methods. No rule, transition, agent or review authorization implementation is copied into the API. Successful advisory work remains ASSESSING. Evidence requests alone reuse M15's existing M2 transition; recommendation actions never approve, deny, close, pay or settle a claim.

## HTTP contracts

| Method/path | Request and precondition | Response |
| --- | --- | --- |
| GET `/health/live` | Public local metadata | 200 liveness; no dependency health assertion |
| GET `/health/ready` | Public local metadata | 200/503 typed local readiness, startup/service/auth configuration and explicit Azure `NOT_CONFIGURED_NOT_PROBED` |
| GET `/openapi.json` | Public schema within the local host/origin profile | OpenAPI 3.1; Swagger/Redoc pages are disabled, with no CDN requirement |
| POST `/api/v1/claims` | Host case scope/intake permission; `IntakeRequest`; UUID `Idempotency-Key`; `If-None-Match: *` | 201 typed intake receipt; strong ETag is application revision |
| POST `/api/v1/claims/{claim_id}/process` | Host case scope/processing permission; expected exact case revision/hash; UUID key; strong quoted `If-Match` application revision | 200 synchronous processing receipt with actual M12 state, or sanitized failure |
| GET `/api/v1/claims/{claim_id}/status` | Explicit case scope | Current API projection, case/application revision, workflow correlation and optional review ID; no outcome authority |
| GET `/api/v1/claims/{claim_id}/advisory` | Case scope; humans additionally require canonical M15 assignment | Typed M12 task, provisional findings and available draft; an absent draft remains absent |
| GET `/api/v1/reviews` | Registered synthetic human/M15 session and API case scope | Assigned summaries only; bounded `limit` 1–16, `offset` 0–64; unknown/duplicate query keys rejected |
| GET `/api/v1/reviews/{entry_id}` | Canonical M15 assignment intersected with API scope | Existing typed M15 detail and ETag review revision; untrusted-content labels preserved |
| POST `/api/v1/reviews/{entry_id}/actions` | Existing `ReviewDecision`, exact path/binding/task; UUID key equals action ID; quoted `If-Match` equals expected review revision | Existing immutable M15 event; duplicate receipt retains its original event ETag |

Review actions remain `approve_recommendation`, `reject_recommendation`, `request_additional_evidence` and `escalate_to_supervisor`. M15 enforces distinct fact/producer authors, source references, rationale/time, all snapshot/version fields, supervisor routing and forbidden transitions. The API exposes no assignment, invalidation, credential issuance, policy publication, claim outcome or settlement endpoint. Agents, MCP clients and simulated model principals cannot access protected application operations.

An authorized exact duplicate returns the original logical operation receipt, not a refreshed status representation. Read the status/detail endpoint before a later operation. A review duplicate always reaches M15 again: current assignment, host invalidation and canonical session are checked before its receipt is returned. HTTP caching cannot preserve revoked review authority.

## Synthetic identity and request boundaries

`SyntheticAuthenticator` issues random 256-bit opaque capabilities only through host code, retains a bounded SHA-256 lookup registry and supports host revocation. It performs no Entra/OAuth/JWT verification. Default `DenyAll` and absent services never report local readiness. Tokens, `ApiAccess`, sessions and `HostBundle` are not request models or OpenAPI components. A future Entra adapter must map verified identities to independently trusted case assignments and existing canonical M15 sessions; caller claims/headers cannot construct those capabilities.

The ASGI boundary checks exact IPv4 loopback peer/server/Host and optional same-origin values; it rejects forwarded headers and identity/grant-shaped headers. There is no proxy trust or CORS grant. Default authority is `127.0.0.1:8766`, a profile identifier rather than evidence of socket execution. Both ASGI tuple/list server representations are normalized without relaxing the host/port match.

Default limits: 16 KiB actual request bytes, 16 KiB/64 decoded headers, a five-second cooperative body-read timeout, eight in-flight requests, 16 case bundles/records and 128 intake/process receipts. Request bodies must be uncompressed JSON objects for POST; duplicate members, non-finite values, malformed UTF-8/JSON and batch roots are rejected before FastAPI parsing. Received bytes are counted independently of `Content-Length`. GET bodies and query credentials are rejected. Only bounded review pagination accepts query arguments.

JSON responses are buffered with an 8 MiB limit before any response bytes are sent; overflow becomes a sanitized 503. This is a non-streaming API profile and does not wrap or change M14's MCP transport. Decoded-header/framework allocations and blocking Python are not an adversarial resource sandbox. In-flight exhaustion returns 429 with `Retry-After`; no distributed or global rate-limit claim is made.

Every response supplies no-store, nosniff and a UUID `X-Correlation-ID`; a valid caller UUID traces that HTTP request only and cannot replace M12/M15's host-bound workflow correlation. Invalid correlation inputs are never echoed. Existing structured logging records the allowlisted `api_request` event, correlation and approved status only. No URL/query, header, token, body, rationale, validation details or raw exception is logged by this boundary.

## Failures, idempotency and storage limits

Errors use typed `ErrorResponse` with a fixed code and request correlation. Missing required key/revision headers return 428; malformed contracts 422; unsupported content 415; oversized input 413; body timeout 408; absent/invalid credentials 401; forbidden principal/action 403; unavailable/unassigned cases/reviews 404; changed duplicates/forbidden states 409; stale binding/application preconditions 412; unavailable processing/review services 503; unexpected failures 500. Framework validation/HTTP details are suppressed. Legitimate 405 responses retain the router's `Allow` header.

Intake/process receipts are bounded and scoped to canonical principal, operation/resource and UUID key, with a hash of the normalized typed request and revision precondition. Authorization precedes receipt lookup. A process-local async lock serializes mutations. Processing reserves a failure tombstone and advances the application revision before invoking M12. An unexpected failure or cancellation leaves a failed record/receipt; retries cannot restart unknown partial work. M12's own bounded technical retries remain unchanged. There is no public API recovery/reprocessing operation for a failed record.

A review entry is exposed only after M15 admission and every host assignment succeeds. If preparation fails partway, the M15 memory journal may retain an orphan audit entry, but API queue/detail/action routes cannot expose it. This is conservative publication control, not a cross-store durable transaction or rollback guarantee. M15 remains the owner of review CAS/audit. Host changes outside this adapter still require M15 invalidation; the API status is its last local projection, not a live shared-store subscription.

All records, receipt tombstones, sessions and audit heads disappear on process exit. Multiple worker processes, cross-event-loop sharing, durable denial/audit retention, outbox/recovery, real identity, trusted ingress/TLS, file scanning, arbitrary uploads and operational outcomes remain planned. This API layer contains no UI; the separate M17 presentation consumes these contracts. M8's four lexical failures and M12's timing-dependent retry/reproduction limitation remain unresolved; neither timeouts nor expected history are weakened.

## Reproduction

```sh
make api-check
PYTHONPATH=src .venv/bin/python -m claims_ai.api --output outputs/api/new-api.json --openapi-output outputs/api/new-openapi.json
```

Use new paths outside reference data. The report explicitly labels `FASTAPI_TESTCLIENT_ASGI_NOT_TCP`, ephemeral synthetic identity, simulated existing M12 model execution, volatile storage and zero Azure/live-model/autonomous-outcome operations. No M17 UI or live APIM/Entra enforcement is implied by OpenAPI or TestClient success.
