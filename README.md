# Enterprise Azure Agentic AI Claims Processing Platform

Greenfield Azure portfolio project for **fictional Northstar Insurance Group**, initially focused on motor damage claims. The business problem is fragmented claim evidence, manual policy lookup and inconsistent decision records. The objective is a production-style, reviewable workflow that assembles evidence, applies explicit policy rules and helps a claims handler reach an auditable outcome.

## Evidence status

**IMPLEMENTED AND LOCALLY TESTED: Milestones 1–2**, comprising the architecture baseline and a `claims_ai` Python foundation: Pydantic v2 contracts, deterministic state-transition guards, local configuration, redacted JSON logging and typed service protocols. Unit tests use hand-authored synthetic contract examples, not an approved policy corpus or golden evaluation dataset. See the [Milestone 2 evidence](docs/milestones/milestone-2.md) for commands, results and limitations.

The end-to-end application and all Azure/AI integrations, coverage rules, durable persistence/audit, authentication, UI, golden evaluation and OpenTelemetry remain **PLANNED**. No agent/service integration is implemented or simulated. No performance benchmark or cloud deployment is claimed. Domain role checks require a trusted caller context; they do not authenticate a human or persist an approval.

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
| [Milestone 2 record](docs/milestones/milestone-2.md) | Python foundation, verification and unresolved decisions |

## Local Python foundation

Python **3.12** is the initial supported minor version (`>=3.12,<3.13`); broader support requires testing. Runtime dependencies are Pydantic v2 and pydantic-settings only. There is no API server or service entry point yet.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
make check
make package
```

`make check` runs Ruff format/lint, strict mypy and pytest. `make format` formats source/tests. Tests explicitly load `src`; package installation is verified separately. `make package` builds a wheel and source distribution in ignored `dist/`, using installed setuptools without downloading build dependencies. Reinstall the package after edits when using the non-editable setup above; unit tests always exercise the current source.

Settings use `CLAIMS_AI_` environment variables with local/test-only defaults. See [.env.example](.env.example); dotenv loading requires an explicit `Settings(_env_file=...)` path. No credentials or external endpoints are supported. The 10 MiB configurable document limit is a setting only until ingestion exists.

Domain validation checks synthetic identifiers, object references, document/evidence hashes, policy-version metadata and caller-supplied evidence checklists. It does not scan files, verify artifact bytes, resolve policy coverage or approve fictional insurance rules. Structured logging emits approved event names and allowlisted operational fields; arbitrary payloads and exception text are suppressed. Do not send raw model dumps or validation-error payloads to other loggers.

Git setup and all commits/pushes remain manual. **Milestone 3 has not started.**
