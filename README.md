# Enterprise Azure Agentic AI Claims Processing Platform

Greenfield Azure portfolio project for **fictional Northstar Insurance Group**, initially focused on motor damage claims. The business problem is fragmented claim evidence, manual policy lookup and inconsistent decision records. The objective is a production-style, reviewable workflow that assembles evidence, applies explicit policy rules and helps a claims handler reach an auditable outcome.

## Evidence status

**IMPLEMENTED: Milestone 1 documentation and `.gitignore` only.** All application, AI, security, evaluation, telemetry and deployment capabilities below are **PLANNED**. No executable application, tests, synthetic dataset, measured performance or cloud deployment exists. No simulated execution is claimed. Architecture verification is not runtime validation.

The original Microsoft Claims Processing Hackathon source was not located. This is independently engineered, informed by lessons from that context; it does not continue the hackathon challenge roadmap. It is separate from the Agentic SDLC portfolio repository. No reference application was imported, and no further source search is planned.

## Initial scope and planned capabilities

- Synthetic first-party motor damage claims: claim forms, policy schedules/wordings, repair estimates and vehicle photographs.
- Azure Document Intelligence and multimodal extraction into versioned claim/evidence contracts with source provenance.
- Microsoft Foundry models and Microsoft Agent Framework for bounded evidence reconciliation and policy explanation.
- Azure AI Search hybrid RAG constrained to the applicable policy version; deterministic coverage rules outside prompts.
- Typed tools, governed MCP/APIM integration and authenticated human review with auditable case outcomes.
- Entra ID, managed identities, least privilege, privacy controls and prompt-injection defenses.
- Synthetic golden cases, reproducible evaluation, OpenTelemetry/Application Insights and failure engineering.
- FastAPI and Container Apps, with proposed Bicep, GitHub Actions and cost controls.

Only fictional policies, people, identifiers, documents and generated/non-identifying vehicle imagery may be used. No production insurance data, automated payment, binding underwriting, autonomous rejection or fraud adjudication is in scope. Every initial case outcome requires an authorized human reviewer.

## Baseline documents

| Document | Purpose |
| --- | --- |
| [Project charter](docs/business/project-charter.md) | Business scope, stakeholders and proposed outcomes |
| [Target architecture](docs/architecture/target-architecture.md) | Components, contracts, workflow and agent boundaries |
| [Security and governance](docs/architecture/security-and-governance.md) | Trust, identity, privacy and decision controls |
| [Evaluation and observability](docs/quality/evaluation-and-observability.md) | Proposed acceptance gates and operational evidence |
| [Deployment strategy](docs/deployment/deployment-strategy.md) | Services, deployment gates and cost constraints |
| [Roadmap](docs/milestones/roadmap.md) | Incremental implementation and evidence requirements |
| [Milestone 1 record](docs/milestones/milestone-1.md) | Decisions, verification, assumptions and remaining gaps |

There are no setup or run commands yet. Git initialization and all commits/pushes remain manual. Milestone 2 has not started.
