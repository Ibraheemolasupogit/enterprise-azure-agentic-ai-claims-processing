# Milestone 17 — Governed claims reviewer operations UI

Status: **COMPLETE within the offline reviewer-UI scope**. Minimal server-rendered operations interface over the unchanged M16 FastAPI contracts and M15 recommendation authority. Offline synthetic cases only; no real identity, cloud deployment, live inference or insurance outcomes. Verification date: 2026-11-10.

## Framework and files

Eight modules under `src/claims_ai/reviewer_ui/`: application/routes, browser guards, typed API consumer, bounded sessions/tickets, escaped views/style, explicit host setup, CLI demonstration and package initializer. No existing runtime module is modified. New focused [UI tests](../../tests/test_reviewer_ui.py), [architecture/security guide](../architecture/governed-reviewer-ui.md) and nested [M17 constraints](../../requirements/m17-constraints.txt). Updated optional dependency metadata, MANIFEST, Makefile, README, current architecture/security, traceability and roadmap. Existing untracked M16 constraint/provenance files are preserved.

Existing FastAPI 0.162.2, Starlette 1.10.0, httpx2 2.16.0 and Uvicorn 0.54.0 are reused; **zero new distributions**. Streamlit is absent and unnecessary for this bounded queue/detail/forms scope. Standard-library escaping/CSS avoids an additional UI/session stack, JavaScript, template engine or remote asset dependency.

## Implemented experience and authority

Host-code enrollment, assigned reviewer/supervisor dashboards, source-linked detail, uncertainty/trust indicators, exact binding/audit inspection, explicit action forms and typed event receipts/errors. All four M15 actions are exercised through actual M16 requests. M16 retains the reviewer's first-case-only scope; the supervisor sees only assigned/scoped tasks. An early-blocked workflow without a reviewable task is not fabricated into a UI recommendation.

Host-issued one-use enrollment maps to a fixed existing API capability; browser role/case inputs cannot authorize. Codes expire in five minutes, UI sessions in 15 monotonic minutes. Cookie rotation, CSRF, exact local origin/peer checks, hash-only enrollment/cookie lookups and finite stores guard the local session boundary. API bearer capabilities never reach the browser. Session possession is simulated identity, not proof of a real human.

Action tickets retain the full exact M15 task/evidence/policy/rule/case binding and review revision on the server. UUID idempotency/If-Match, original duplicate decisions and host timestamps pass to M16/M15. Every retry is reauthorized by the API. Concurrent identical submissions return one event; incompatible actions have one winner. Rendering choices never grant supervisor authority or make a missing recommendation approvable.

The UI labels provisional/simulated/untrusted information and never treats recommendation approval as claim approval. No final outcome, settlement, payment, assignment, invalidation or policy-publication control exists. No existing policy rule, lifecycle, agent, orchestration, M14 security boundary or M15/M16 service is replaced.

## Verification and evidence

| Verification | Result |
| --- | --- |
| Final complete source pytest | **878 passed in 263.29 seconds**: 814 existing plus 64 UI cases, including the new slow-response regression |
| Final independent installed-wheel pytest | **878 passed in 268.78 seconds**, no warnings, against the same corrected runtime bytes |
| UI regressions | 63 focused cases passed in 42.36 seconds before the final capacity correction; the new slow-response and existing capacity/partial-response regressions then passed together. Final full suites include **64 UI cases** plus all 814 earlier cases |
| Ruff / strict mypy | Lint and formatting pass; strict mypy passes across **111 source/test Python files** |
| Dependencies | `pip check` passes; all **37** nested M17/M16/M13/M10 pins match; **zero new distributions** |
| Package/import checks | Offline wheel and source distribution; **89 runtime Python modules plus `py.typed`** match source and the independent installation; normal isolated installed UI import succeeds outside the repository without `PYTHONPATH`; `ui` extra declares the existing Uvicorn dependency |
| API contract | Existing M16 OpenAPI 3.1.0/nine paths unchanged; reviewer action requires Idempotency-Key and If-Match and the existing full ReviewDecision; no role/reviewer identity fields are introduced |
| Reproduction | Two source runs and one independent installed-wheel run produce byte-identical JSON reports and all four corresponding sanitized HTML captures |
| Preservation | All **161** reference data files, every existing runtime/test module and historical M1–M16 milestone record match the starting snapshot; supplied M14/M15/M16 report/schema hashes match; existing untracked M16 dependency files are unchanged |
| Documentation | All **418** local links resolve and **20** named M17 traceability test references exist |

Final reports: `outputs/ui/m17-verified-a.json`, `m17-verified-b.json` and `m17-verified-wheel.json`; common SHA-256 **`58926daeb71893b327bf0a81c1be78836e90b126149391d82562a0e7cc0d3aa0`**. Each records **12 actual UI/API protocol scenarios** and zero Azure operations, live model calls or autonomous outcomes. UI source fingerprint: **`b3a5ed32fb412453136d8e1e0b2fe175920486fdc81dff0fee4cb402a552fafa`**.

Captures are under `outputs/ui/m17-html-a/`, `m17-html-b/` and `m17-html-wheel/`. `outputs/ui/m17-reproduction-verification.json` records the four common HTML hashes and report equality. These are real rendered HTML responses with escaped content, redacted CSRF/ticket values and disabled submit buttons, not hand-authored screen mockups. The exception capture has no recommendation; it does not fabricate an agent draft. Normal installed imports succeed; CLI evidence uses explicit source and independent package targets outside the repository.

Package artifacts are under `outputs/packages/m17/`. Independent tests use Python isolated mode and a separate wheel installation ahead of source, with pytest's source path replaced by that installation; they share the verified dependency environment. Historical CLI reproduction tests deliberately retain their source-launch paths. The M17 CLI is separately launched from outside the repository against the independent target; its evidence matches source exactly. No editable-import assumption is used.

The initial focused run found a test assumption about queue order: selecting the second item did not always select another claim because the existing queue sorts by entry identity. The corrected isolation regression selects the actual second claim ID; it verifies identical safe 404 pages for unknown/unassigned cases. Review routing presentation was also checked after escalation so the current supervisor requirement is shown even when the original task requested an ordinary reviewer.

A final boundary review identified a real capacity gap: the in-flight slot was released before buffered response sending, so eight slow response consumers did not stop a ninth admitted request. A focused regression reproduced HTTP 200 where 429 was required. The slot now remains held through response completion, with release in an outer `finally` on success, disconnect or cancellation. The new slow-response regression and existing processing-capacity/partial-response failure cases pass together (three tests, 0.17 seconds). Final full suites below supersede the earlier 877-test runs and include this correction.

The reproducible report uses actual FastAPI UI and M16 TestClient ASGI requests, not HTTP-shaped stubs or TCP. HTML captures cover reviewer queue, supervisor queue, detailed sources and missing-recommendation supervisor triage. CSRF/ticket values are redacted and submit buttons disabled. Native browser preview was attempted but usable browser automation was unavailable while the browser was active; **no screenshot, rendered-pixel verification, real browser submission or live TCP verification is claimed**. The HTML and protocol captures provide the practical offline evidence.

## Acceptance boundary and production requirements

Session, enrollment, view/ticket, review state, audit and receipt stores are bounded process memory. Absolute session expiry is independent of the fixed synthetic M15 action/audit clock. API credentials remain host-held until host revocation; ending a UI session does not revoke the underlying host capability. In-progress requests are authorized at request time; no distributed revocation, crash recovery, cross-store transaction or multiworker guarantee is claimed. Server-side TestClient transport is an explicit offline adapter, not deployed authentication/ingress.

Host enrollment delivery, TLS/secure production cookies, real Entra mapping, durable storage/audit/outbox, recovery, security telemetry, original artifact access and full browser/accessibility/usability verification remain outstanding. Native semantic controls, labels/focus/status/captions and responsive CSS are structurally tested; no WCAG certification or screen-reader/mobile audit is claimed. The OS user remains trusted and can replace code/private memory or share a capability.

M4–M9 reference data and earlier evidence are preserved. M8's four retrieval failures, M12 timing-dependent retry/report reproducibility and M15 memory limitations remain unresolved. New UI modules change future whole-package execution fingerprints by design without changing historical artifacts. No Azure access/spending, live model call, new agent, M18 implementation, staging, commit or push. **Stop after M17 for review.**
