# Enterprise Azure Agentic AI Claims Processing Platform

Greenfield Azure portfolio project for **fictional Northstar Insurance Group**, initially focused on motor damage claims. The business problem is fragmented claim evidence, manual policy lookup and inconsistent decision records. The objective is a production-style, reviewable workflow that assembles evidence, applies explicit policy rules and helps a claims handler reach an auditable outcome.

## Evidence status

**IMPLEMENTED AND LOCALLY TESTED:** the `claims_ai` Python foundation, Milestone 4 synthetic dataset tools and Milestone 5 offline extraction benchmark. The foundation supplies Pydantic v2 contracts, deterministic state-transition guards, local configuration, redacted JSON logging and typed protocols. The [motor-v1 corpus](data/synthetic/motor/README.md) supplies 12 development scenarios and source-linked labels; policies/coverage interpretations remain unapproved. The [benchmark](docs/quality/document-intelligence-benchmark.md) has typed interfaces and deterministic scoring; **all fixture extraction results are SIMULATED ground-truth echoes**, not OCR/vision/provider performance results.

The end-to-end application and all live Azure/Mistral/GPT integrations, coverage rules, durable persistence/audit, authentication, UI, held-out model evaluation and OpenTelemetry remain **PLANNED**. No live service comparison or cloud deployment is claimed. Domain role checks require a trusted caller context; they do not authenticate a human or persist an approval. Dataset labels and simulated responses are not model-produced facts or approved case outcomes.

**Milestone 6 implements the [structured evidence boundary](docs/architecture/structured-evidence-processing.md):** deterministic field normalization, identity/hash/source validation, actionable holds/rejections, immutable local history, idempotent retries and guarded case admission. It preserves M4 data and M5 benchmark semantics. The CLI maps SIMULATED fixture proposals while keeping original documents quarantined; no scanner or operational ingestion is claimed.

**Milestone 7 implements [draft-policy knowledge ingestion and lexical retrieval](docs/architecture/policy-knowledge-retrieval.md):** verified fixture parsing, deterministic source-linked chunks, exact claim/policy/version/date/snapshot filters and fail-closed abstentions. Token overlap is real local code over unapproved synthetic text; no semantic search, hybrid RAG, Azure AI Search implementation, retrieval-accuracy result or coverage decision is claimed.

**Milestone 3 documentation is complete:** the business process, responsibilities, requirements, traceability, risk register and authority ADR refine the baseline. No runtime files changed. The 115 passing foundation tests and package/typing results remain historical Milestone 2 evidence; they were not rerun or promoted into business-performance results by this documentation milestone.

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
| [Requirements](docs/business/requirements.md) | Stable business-to-system requirements and acceptance criteria |
| [Traceability matrix](docs/business/traceability-matrix.md) | Actual contracts/existing tests versus planned capabilities and verification |
| [Risk register](docs/business/risk-register.md) | Open risks, owners and required closure evidence |
| [Target architecture](docs/architecture/target-architecture.md) | Components, contracts, workflow and agent boundaries |
| [Authority ADR](docs/architecture/decisions/0001-decision-authority.md) | Existing code/agent/human decision boundary |
| [Security and governance](docs/architecture/security-and-governance.md) | Trust, identity, privacy and decision controls |
| [Evaluation and observability](docs/quality/evaluation-and-observability.md) | Proposed acceptance gates and operational evidence |
| [Deployment strategy](docs/deployment/deployment-strategy.md) | Services, deployment gates and cost constraints |
| [Roadmap](docs/milestones/roadmap.md) | Incremental implementation and evidence requirements |
| [Milestone 1 record](docs/milestones/milestone-1.md) | Decisions, verification, assumptions and remaining gaps |
| [Milestone 2 record](docs/milestones/milestone-2.md) | Python foundation, verification and unresolved decisions |
| [Milestone 3 record](docs/milestones/milestone-3.md) | Process/requirement refinements, checks and scope sequencing |
| [Synthetic motor corpus](data/synthetic/motor/README.md) | Scenarios, generation command, schema, provenance and limitations |
| [Milestone 4 record](docs/milestones/milestone-4.md) | Dataset implementation, tests and reproducibility evidence |
| [Document intelligence benchmark](docs/quality/document-intelligence-benchmark.md) | Offline CLI, typed extraction boundaries, scoring and limitations |
| [Milestone 5 record](docs/milestones/milestone-5.md) | Harness checks and explicitly simulated fixture results |
| [Structured evidence processing](docs/architecture/structured-evidence-processing.md) | Mapping, source/quality gates, history and admission |
| [Milestone 6 record](docs/milestones/milestone-6.md) | Evidence-boundary checks and limitations |
| [Policy knowledge retrieval](docs/architecture/policy-knowledge-retrieval.md) | Offline ingestion, lexical filtering, citations and abstentions |
| [Milestone 7 record](docs/milestones/milestone-7.md) | Draft-policy foundation, verification and remaining gaps |

## Local Python foundation

Python **3.12** is the initial supported minor version (`>=3.12,<3.13`); broader support requires testing. Runtime dependencies are Pydantic v2 and pydantic-settings only. There is no API server or service entry point yet.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
make check
make package
```

`make check` runs Ruff format/lint, strict mypy and pytest. `make format` formats source/tests. Tests explicitly load `src`; package installation is verified separately. `make package` builds a wheel and source distribution in ignored `dist/`, using installed setuptools without downloading build dependencies. Reinstall the package after edits when using the non-editable setup above; unit tests always exercise the current source.

Verify the checked-in dataset with `make dataset-check`. To generate a fresh copy without installing anything else:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.dataset generate --output /tmp/northstar-motor-v1 --seed 20261030
```

The output path must not already exist. The [corpus guide](data/synthetic/motor/README.md) documents exact reproduction and safe handling of malicious fixture text. Standard-library PDF/PNG rendering adds no dependency to the application.

Run the offline extraction harness with a new output filename:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.benchmark --corpus data/synthetic/motor/v1 --output outputs/benchmarks/fixture.json
```

This emits versioned JSON for 75 unique documents/335 field labels, preserving duplicate scenario references. Results are **SIMULATED**, grouped by media/document/capability profile, with unavailable latency/token/cost metadata left null. `--pdf-only` tests unsupported-image handling on the fixture; no vendor adapter is executed. See the [scoring guide](docs/quality/document-intelligence-benchmark.md#scoring-methodology--field-v1). `make benchmark-check` runs its focused tests.

Settings use `CLAIMS_AI_` environment variables with local/test-only defaults. See [.env.example](.env.example); dotenv loading requires an explicit `Settings(_env_file=...)` path. No credentials or external endpoints are supported. The 10 MiB configurable document limit is a setting only until ingestion exists.

Generate a deterministic evidence-validation report with a new output filename:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.evidence --corpus data/synthetic/motor/v1 --output outputs/evidence/processing.json
```

All original documents remain quarantined; the report contains proposals/issues and no case admission. The library's accepted/admitted paths are separately tested with explicit synthetic scan assertions and simulation opt-in. `make evidence-check` runs those focused tests; `make check` includes them. Confidence remains uncalibrated, and conflicts require human review rather than automatic fact replacement.

Run the draft-policy lexical demonstration with a new output filename:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.knowledge --corpus data/synthetic/motor/v1 --output outputs/knowledge/draft-lexical.json
```

This emits `OFFLINE_SYNTHETIC` clause/citation and abstention records. The draft-policy index preserves quarantine and approval status; exclusions are quoted candidates only. `make knowledge-check` runs focused parsing, filtering, citation, scope and outage tests. Azure search is a protocol, and no policy is activated or attached to a case.

Domain validation checks synthetic identifiers, object references, document/evidence hash metadata, policy-version metadata and caller-supplied evidence checklists. It does not scan files, resolve policy coverage or approve fictional insurance rules. Dataset validation additionally checks fixture bytes against hashes/source renderings; it is not live upload validation or malware scanning. Structured logging emits approved event names and allowlisted operational fields; arbitrary payloads and exception text are suppressed. Do not send raw model dumps or validation-error payloads to other loggers.

Git setup and all commits/pushes remain manual. **Milestone 8 has not started.** Historical milestone records preserve their original scope; the current [roadmap](docs/milestones/roadmap.md) reflects the approved policy-knowledge Milestone 7.
