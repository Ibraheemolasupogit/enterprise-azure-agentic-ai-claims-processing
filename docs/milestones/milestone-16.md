# Milestone 16 — Governed FastAPI claims application foundation

Status: **COMPLETE within the offline application-foundation scope**. Genuine version-one FastAPI ASGI application over M12 processing and M15 review, bounded typed HTTP contracts, synthetic host capabilities, strict case isolation and safe failures. No M17 UI, real Entra authentication, Azure hosting or insurance-outcome authority. Verification date: 2026-11-10.

## Files and scope

- Eight-module [API package](../../src/claims_ai/api/__init__.py): typed contracts, ephemeral synthetic auth, application adapter, outer ASGI guards, genuine FastAPI factory/routes, explicit host fixtures and reproducible CLI.
- New [API integration/security tests](../../tests/test_api.py), [architecture](../architecture/governed-fastapi-application.md), [dependency/API record](../dependencies/fastapi.md), nested M16 constraints and verified wheel manifest. Updated optional packaging metadata, MANIFEST, Makefile, README, current architecture/security, traceability and roadmap.
- Existing M2 lifecycle, M9 policy/rules, M12 workflows, M14 HTTP transport and M15 review implementation are reused without modification. Existing structured logging gains one allowlisted `api_request` event; no payload logging is added. Only FastAPI 0.162.2 and annotated-doc 0.0.5 are new distributions.
- The approved M16 scope implements registered synthetic bundle intake and the existing safe services. Arbitrary uploads, malware scanning, durable persistence/outbox and authenticated production intake remain deferred. No datasets, evaluation labels/results, new agent or RAG implementation are introduced.

## Actual endpoints and controls

Seven `/api/v1` operations cover intake, processing, status, advisory, assigned queue/detail and recommendation actions; public liveness/readiness and `/openapi.json` provide local metadata. Swagger/Redoc pages are disabled. Typed requests reuse M2 Claim and M15 ReviewDecision. Host-owned original bytes, workflow grants, policies, rule packs, canonical human sessions and assignment plans never come from HTTP request bodies.

Opaque 256-bit synthetic capabilities resolve through a bounded host hash registry; default authentication denies all. API case scope intersects actual M15 assignment. Producer/fact-author separation, supervisor requirements and exact task/evidence/policy/rule/revision bindings remain enforced by M15 on every action and duplicate. There is no outcome, assignment, credential issuance or settlement endpoint. Recommendation approval leaves the claim ASSESSING; explicit evidence requests reuse M2 through M15.

Actual-byte JSON/header/response limits, exact local Host/Origin/peer checks, spoof/proxy rejection, in-flight capacity, UUID request correlation, no-store/nosniff and allowlisted structured logging guard the HTTP boundary. Errors suppress framework details, payloads and exception text. Required UUID idempotency keys and strong revision headers protect writes; processing failures/cancellation retain bounded tombstones instead of restarting uncertain work. Partial host review preparation is not published to API readers/actions.

Readiness separates local startup/service/synthetic-auth configuration from external Azure dependencies, which remain `NOT_CONFIGURED_NOT_PROBED` and never ready. TestClient/ASGI execution is not represented as TCP, TLS, APIM enforcement or production hosting.

## Verification

| Verification | Result |
| --- | --- |
| Complete source pytest suite | **814 passed in 212.97 seconds**: 729 existing cases plus 85 API integration/security cases |
| Independent installed-wheel pytest suite | **814 passed in 223.50 seconds**, Python isolated mode, separately installed package target ahead of source, pytest source-path setting replaced with that target |
| API security/contract coverage | All 85 cases passed in both complete suites; real TestClient exercises processing/review, roles, cross-case isolation, supervisor/no-draft constraints, exact bindings, replay, stale revisions, concurrent mutation, cancellation/outage tombstones, partial-publication failure, malformed/oversized/timed-out requests, spoofed headers, origins/peers, response limits, readiness and redacted errors/logging |
| Ruff / strict mypy | Lint and formatting pass; strict mypy passes across **102 source/test files** |
| Dependency closure | `pip check` passes; all **37** nested M16/M13/M10 pinned installed versions match; only FastAPI and annotated-doc added |
| Packaging | Offline wheel and source distribution; all **81 Python runtime modules plus `py.typed`** verified against source and separate installed target; optional API dependencies retained |
| OpenAPI | Actual generated OpenAPI **3.1.0**, **9 paths**, **242 resolved local references**; FastAPI model and component/actual-response JSON-schema checks pass; security and required headers are tested |
| Evidence reproducibility | Two source API demonstrations and one independent installed-wheel demonstration are byte-identical; their three separately generated OpenAPI documents are also byte-identical |
| Documentation checks | **404** local links resolve and all **15** named M16 traceability test references exist |

The API demonstration contains **14** actual HTTP scenarios, including intake/process replay, assigned review, recommendation approval, unauthorized access, forbidden MCP principal and stale preconditions. Report files are `outputs/api/m16-verified-a.json`, `m16-verified-b.json` and `m16-wheel-verified.json`; SHA-256 **`287c2dc709f2fdaee562022f43c26e8743c3cda13073a923d76d4f6c84738c60`**. Schema files are `outputs/api/m16-openapi-a.json`, `m16-openapi-b.json` and `m16-wheel-openapi.json`; SHA-256 **`090228f5352ea6152a644325133831e0126f0a3becc1793d7699553185f1eb95`**. Reports explicitly identify TestClient ASGI rather than TCP, simulated M12 model execution, ephemeral synthetic identity, preserved human authority and zero Azure/live-model/autonomous-outcome operations.

Artifacts are in `outputs/packages/m16/`. The full installed-wheel suite imports application/test modules from the independent package target; historical CLI reproduction tests retain their deliberate source-launch paths. The M16 CLI is separately executed from outside the repository against the independent installed target and produces identical evidence. Runtime bytes are checked again after documentation-only package metadata finalization; no editable installation or `PYTHONPATH` is required for a normal installed import.

The focused suite found and corrected an ASGI response-limit interaction: raising during FastAPI's response send was remapped to a generic 500. The outer buffer now records overflow, waits for route completion and sends a sanitized 503 before any bytes are released. The regression verifies capacity handling using the real app; the router's safe 405 `Allow` header is also retained. No security budget, timeout or baseline expectation was relaxed.

## Limits and acceptance boundary

All stores, receipt tombstones, identity tokens and M15 audit heads are process-local and non-durable. A same-user host can replace code/private memory or misdeliver a human capability; this does not prove human identity. No signed/durable audit, crash recovery, distributed CAS, multiworker/cross-event-loop storage, live Azure dependency probing or denial telemetry retention is claimed. Failed review preparation can retain an unpublished M15 memory entry; this is not a durable transaction/rollback guarantee. Failed processing has no public recovery endpoint in this scope.

M8 Q-007/Q-012/Q-015/Q-029 remain unresolved. M12's cooperative deadlines and timing-dependent retry/report histories are unchanged. Added API modules and the logging enum extend the existing whole-package fingerprint, so future M12/review task IDs change by design; historical artifacts are preserved. M15's synthetic identity and persistence limitations remain. No live APIM or Entra enforcement is inferred from schema/static/local tests.

No Azure operations/spending, live model calls, autonomous outcomes, M17 UI, commits or pushes. **Stop after M16 for review.**
