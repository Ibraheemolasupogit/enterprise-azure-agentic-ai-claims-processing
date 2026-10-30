# Incremental roadmap

This roadmap implements the greenfield master brief expressed in the [README](../../README.md) and [charter](../business/project-charter.md). It does not inherit a hackathon challenge sequence and is separate from Agentic SDLC work. **Milestones 1–2 are delivered within their recorded scope; Milestones 3–10 are PLANNED and not started.** Each milestone ends with reviewable evidence and an explicit status update.

| Milestone | Scope and expected deliverables | Exit evidence |
| --- | --- | --- |
| 1 — Charter and architecture baseline | Business scope, architecture/security, evaluation/deployment strategies, roadmap and `.gitignore` | Document/link/consistency checks; no runtime claims |
| 2 — Python engineering foundation | Versioned claim/evidence/policy/assessment/review models; deterministic transitions; local settings/redacted logs; typed protocols; packaging and quality tooling | Local unit tests, lint/format, strict typing and package checks; synthetic examples only; no API, persistence or policy engine |
| 3 — Evidence ingestion | FastAPI/local persistence skeleton deferred from initial M2 plan; quarantine/scan boundary, upload validation, immutable hashes, extraction adapters and photo-evidence contracts; initial outbox/worker processing | Valid/invalid file tests, provenance checks, restart/replay tests; label stubs simulated and distinguish later authorized Document Intelligence/model tests |
| 4 — Version-aware RAG and rules | Approved policy ingestion, immutable index versions, hybrid retrieval adapter, exact policy resolver and executable rule packs | Policy/endorsement date boundaries, retrieval filters/recall and arithmetic/unknown-fact tests; no model-owned rules |
| 5 — Bounded agent workflows | Agent Framework orchestration, evidence reconciliation and policy explanation; typed tools and model adapters | Tool/output validation, bounded execution, abstention and comparison to simpler baselines; pinned versions |
| 6 — Human review and case outcomes | Reviewer UI, evidence correction, supervisor routing, stale-write protection, audited outcomes | Human approval/override and case reopening tests; no autonomous final decisions |
| 7 — Governed tools and security hardening | MCP/APIM adapter/contracts, Entra authorization, managed-identity design, least privilege, injection defenses and threat model | Local negative/security tests; later cloud identity/gateway evidence explicitly separate; no deployed bypass |
| 8 — Reproducible quality and operations | Held-out golden suite, evaluation manifests, OpenTelemetry instrumentation, dashboards/alert definitions, fault-injection and incident/recovery runbooks | Reported counts/results, safety gates, redaction, replay and dependency-failure evidence |
| 9 — Governed Azure deployment | Bicep, protected GitHub Actions/OIDC, environment separation, compatibility/quota matrix and approved budgets | Authorized deployment only: reviewed infrastructure plan, actual service integration/identity tests, smoke checks and cost evidence |
| 10 — Readiness and portfolio evidence | End-to-end synthetic demonstration, restore/recovery exercise, architecture reconciliation, limitations and teardown plan | Traceable implemented/tested/simulated/planned matrix; evaluation, security and operational reports; no unsupported production-readiness claim |

Security, tests, provenance, basic telemetry and cost limits start with their first relevant component; later milestones deepen them rather than defer all controls. No milestone is complete solely because code exists. Actual Azure calls in any milestone require separate deployment/spending authorization; local progress uses explicitly labeled simulations where necessary.

Working definitions: **IMPLEMENTED** means an artifact/code path exists; **TESTED** adds a named environment and recorded checks/results; **SIMULATED** means a stub or injected scenario exercised a contract without proving the live dependency; **PLANNED** means intended only. Track capability and environment separately; documentation completion never promotes runtime status.

The approved Milestone 2 request narrowed delivery to the Python foundation, deferring the initially proposed FastAPI skeleton and concrete persistence to Milestone 3. Policy examples/rule execution require fictional policy approval before Milestone 4. This is a sequencing change, not a change to architectural decisions; see the [Milestone 2 record](milestone-2.md).

Next proposed action, after Milestone 2 review: plan Milestone 3 ingestion and local API/persistence contracts. No Milestone 3 implementation has started. Git setup/connection/commits remain manual and separate.
