# Incremental roadmap

This roadmap implements the greenfield master brief expressed in the [README](../../README.md) and [charter](../business/project-charter.md). It does not inherit a hackathon challenge sequence and is separate from Agentic SDLC work. Only Milestone 1 is delivered; **Milestones 2–10 are PLANNED and not started**. Each milestone ends with reviewable evidence and an explicit status update.

| Milestone | Scope and expected deliverables | Exit evidence |
| --- | --- | --- |
| 1 — Charter and architecture baseline | Business scope, architecture/security, evaluation/deployment strategies, roadmap and `.gitignore` | Document/link/consistency checks; no runtime claims |
| 2 — Contracts, synthetic fixtures and local skeleton | Versioned claim/evidence/policy/assessment/review schemas; initial fictional policy/rule fixtures; FastAPI skeleton; local persistence/state contracts and configuration | Schema validation, fixture provenance, state/idempotency and deterministic unit tests; no Azure required |
| 3 — Evidence ingestion | Quarantine/scan boundary, upload validation, immutable hashes, extraction adapters and photo-evidence contracts; initial outbox/worker processing | Valid/invalid file tests, provenance checks, restart/replay tests; label stubs simulated and distinguish later authorized Document Intelligence/model tests |
| 4 — Version-aware RAG and rules | Approved policy ingestion, immutable index versions, hybrid retrieval adapter, exact policy resolver and executable rule packs | Policy/endorsement date boundaries, retrieval filters/recall and arithmetic/unknown-fact tests; no model-owned rules |
| 5 — Bounded agent workflows | Agent Framework orchestration, evidence reconciliation and policy explanation; typed tools and model adapters | Tool/output validation, bounded execution, abstention and comparison to simpler baselines; pinned versions |
| 6 — Human review and case outcomes | Reviewer UI, evidence correction, supervisor routing, stale-write protection, audited outcomes | Human approval/override and case reopening tests; no autonomous final decisions |
| 7 — Governed tools and security hardening | MCP/APIM adapter/contracts, Entra authorization, managed-identity design, least privilege, injection defenses and threat model | Local negative/security tests; later cloud identity/gateway evidence explicitly separate; no deployed bypass |
| 8 — Reproducible quality and operations | Held-out golden suite, evaluation manifests, OpenTelemetry instrumentation, dashboards/alert definitions, fault-injection and incident/recovery runbooks | Reported counts/results, safety gates, redaction, replay and dependency-failure evidence |
| 9 — Governed Azure deployment | Bicep, protected GitHub Actions/OIDC, environment separation, compatibility/quota matrix and approved budgets | Authorized deployment only: reviewed infrastructure plan, actual service integration/identity tests, smoke checks and cost evidence |
| 10 — Readiness and portfolio evidence | End-to-end synthetic demonstration, restore/recovery exercise, architecture reconciliation, limitations and teardown plan | Traceable implemented/tested/simulated/planned matrix; evaluation, security and operational reports; no unsupported production-readiness claim |

Security, tests, provenance, basic telemetry and cost limits start with their first relevant component; later milestones deepen them rather than defer all controls. No milestone is complete solely because code exists. Actual Azure calls in any milestone require separate deployment/spending authorization; local progress uses explicitly labeled simulations where necessary.

Working definitions: **IMPLEMENTED** means an artifact/code path exists; **TESTED** adds a named environment and recorded checks/results; **SIMULATED** means a stub or injected scenario exercised a contract without proving the live dependency; **PLANNED** means intended only. Track capability and environment separately; documentation completion never promotes runtime status.

Next proposed action, after Milestone 1 review: implement Milestone 2 locally with synthetic contracts, approved fictional policy examples and deterministic tests. Git initialization/connection/commits remain manual and separate. No Milestone 2 files are created by Milestone 1.
