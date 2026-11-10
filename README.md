# Enterprise Azure Agentic AI Claims Processing Platform

Greenfield Azure portfolio project for **fictional Northstar Insurance Group**, initially focused on motor damage claims. The business problem is fragmented claim evidence, manual policy lookup and inconsistent decision records. The objective is a production-style, reviewable workflow that assembles evidence, applies explicit policy rules and helps a claims handler reach an auditable outcome.

## Evidence status

**IMPLEMENTED AND LOCALLY TESTED:** the `claims_ai` Python foundation, Milestone 4 synthetic dataset tools and Milestone 5 offline extraction benchmark. The foundation supplies Pydantic v2 contracts, deterministic state-transition guards, local configuration, redacted JSON logging and typed protocols. The [motor-v1 corpus](data/synthetic/motor/README.md) supplies 12 development scenarios and source-linked labels; policies/coverage interpretations remain unapproved. The [benchmark](docs/quality/document-intelligence-benchmark.md) has typed interfaces and deterministic scoring; **all fixture extraction results are SIMULATED ground-truth echoes**, not OCR/vision/provider performance results.

The bounded offline workflow, human-review service, FastAPI adapter and reviewer operations UI are implemented through M19, with synthetic identity/security and adversarial evaluation foundations. Production deployment, live Azure/Mistral/GPT integrations, approved operational coverage rules, durable persistence/audit, real authentication, production UI hosting, held-out model evaluation and OpenTelemetry remain **PLANNED**. No live service comparison or cloud deployment is claimed. Synthetic host capabilities and domain role checks do not authenticate a real human or durably persist an approval. Dataset labels and simulated responses are not model-produced facts or approved case outcomes.

**Milestone 6 implements the [structured evidence boundary](docs/architecture/structured-evidence-processing.md):** deterministic field normalization, identity/hash/source validation, actionable holds/rejections, immutable local history, idempotent retries and guarded case admission. It preserves M4 data and M5 benchmark semantics. The CLI maps SIMULATED fixture proposals while keeping original documents quarantined; no scanner or operational ingestion is claimed.

**Milestone 7 implements [draft-policy knowledge ingestion and lexical retrieval](docs/architecture/policy-knowledge-retrieval.md):** verified fixture parsing, deterministic source-linked chunks, exact claim/policy/version/date/snapshot filters and fail-closed abstentions. Token overlap is real local code over unapproved synthetic text; no semantic search, hybrid RAG, Azure AI Search implementation, retrieval-accuracy result or coverage decision is claimed.

**Milestone 8 implements [offline lexical retrieval evaluation](docs/quality/policy-retrieval-evaluation.md):** 30 versioned authored queries, independent source/citation checks, precision/recall/MRR/nDCG at declared cutoffs, policy-scope and abstention diagnostics, and reproducible reports with failures retained. Labels are **authored, not independently adjudicated or held out**. These measurements do not evaluate semantic/hybrid RAG or approve insurance policies.

**Milestone 9 implements [deterministic provisional motor rules](docs/architecture/deterministic-provisional-rules.md):** exact policy/version/date and evidence gates, explicit fictional excess/cap parameters, source-linked four-state findings and mandatory human/supervisor review requirements. The new [specification](data/rules/motor/README.md) is **unapproved**; calculations are non-binding illustrations on SIMULATED inputs. No claim approval, denial, settlement or payment is authorized. M8's four lexical failures remain unresolved.

**Milestone 10 implements the [actual Microsoft Agent Framework foundation](docs/architecture/agent-framework-foundation.md):** pinned SDK 1.23.0, a supported offline chat-client extension, one case-bound read-only tool, typed advisory outputs and deterministic host safety guards. Framework construction, function dispatch and structured parsing are real; all model responses are **SIMULATED**. No live reasoning quality or autonomous claim outcome is claimed. The [M10 record](docs/milestones/milestone-10.md) records 422 passing tests and package/reproduction evidence; the [dependency record](docs/dependencies/agent-framework.md) distinguishes exact installed APIs from planned provider integrations.

**Milestone 11 implements [governed internal agent tools](docs/architecture/governed-agent-tools.md):** three typed read-only tools backed by verified evidence, exact-version lexical retrieval and provisional rule findings. Host grants bind every call to one case snapshot; argument/provenance checks, bounded execution and safe failures preserve human/supervisor authority. Real SDK invocation is locally tested; chat responses and identity/fault assertions are **SIMULATED**. No MCP/APIM or authenticated cloud integration is claimed. See the [M11 record](docs/milestones/milestone-11.md).

**Milestone 12 implements the [deterministic offline claims workflow](docs/architecture/deterministic-claims-workflow.md):** intake, evidence, exact-version policy retrieval, provisional findings, existing governed agent synthesis and mandatory human/supervisor routing. Bounded retries, immutable correlated records and validated caller-held checkpoints support offline replay/recovery. Chat and scan/identity/reviewer assertions remain **SIMULATED**. Successful advisory processing leaves the operational case ASSESSING; no approved assessment, claim outcome or durable cloud workflow is created. See the [M12 record](docs/milestones/milestone-12.md).

**Milestone 13 implements the [governed local MCP server](docs/architecture/governed-mcp-server.md):** genuine MCP SDK stdio initialization/discovery/invocation over the three existing read-only tools. A private host-provided startup context binds one process to one case; RPC arguments/metadata never grant access. Native and Microsoft Agent Framework MCP clients execute real protocol calls with typed results. No model, network listener, APIM, production authentication or claim decision is supplied. See the [M13 record](docs/milestones/milestone-13.md).

**Milestone 14 implements the [local MCP HTTP boundary](docs/architecture/mcp-http-and-gateway.md)** and [APIM governance reference](docs/deployment/apim-governance-reference.md): real SDK Streamable HTTP tested through in-process ASGI, synthetic pinned-key gateway credentials plus independent host case grants, bounded requests and unchanged governed reads. XML policy safeguards and Bicep compilation are checked; Entra/APIM enforcement remains design only. **M14 is complete within its local foundation scope:** the supplied external loopback report records successful real TCP execution; shutdown evidence and its limits are documented. See [M14 evidence](docs/milestones/milestone-14.md). M8's four failures remain unresolved.

**Milestone 15 implements [governed synthetic human review](docs/architecture/governed-human-review.md):** an assigned case/task queue and read-only detail view over semantically verified M12 checkpoints, explicit recommendation approval/rejection, evidence requests and supervisor escalation. Host-registered human sessions, producer/fact-author separation, exact snapshot/version guards, process-local CAS and immutable audit events protect the offline boundary. Approving a recommendation creates no insurance outcome or settlement authority. Missing recommendations cannot be approved; adverse/ambiguous/high-risk/conflicting work requires an assigned supervisor. See [M15 evidence](docs/milestones/milestone-15.md). Real authentication and durable audit remain planned; the M16 adapter and M17 UI are described below. M12's timing-dependent retry limitation is preserved.

**Milestone 16 implements the [offline FastAPI application](docs/architecture/governed-fastapi-application.md):** registered-bundle intake, existing M12 processing, status/advisory reads and assigned M15 review endpoints. Typed contracts, ephemeral synthetic host capabilities, exact case scope, idempotency/revision preconditions, bounded bodies/responses/concurrency and redacted correlated errors protect the adapter. Local readiness is separate from unconfigured Azure dependencies. Genuine TestClient/OpenAPI evidence establishes ASGI execution; no TCP hosting, real Entra, arbitrary uploads, durable outcome commit or M17 UI is claimed. See [M16 evidence](docs/milestones/milestone-16.md) and [dependency provenance](docs/dependencies/fastapi.md).

**Milestone 17 implements the [reviewer operations UI](docs/architecture/governed-reviewer-ui.md):** assigned synthetic queues, source-linked detail, uncertainty and supervisor routing, explicit advisory actions and safe receipts/errors over the existing M16 endpoints. Server-rendered FastAPI/HTML/CSS reuses installed dependencies; no Streamlit, JavaScript or new distribution is needed. One-use host enrollment and bounded server-held sessions/tickets preserve API authority and exact review snapshots. See [M17 evidence](docs/milestones/milestone-17.md). HTML/protocol captures establish real UI/API ASGI execution; browser-pixel, TCP, real identity and production accessibility verification remain outstanding.

**Milestone 18 implements the [identity/security foundation](docs/architecture/identity-and-security-foundation.md):** reusable offline verification/discovery interfaces, exact signed synthetic claims, bounded RSA key rotation/revocation and independent host binding into existing API/MCP authority. Default API capabilities now expire; UI sessions can recheck and revoke underlying access. Canonical M15 sessions, assignments and supervisor guards remain required. Real Entra is explicitly unconfigured; managed identity, Key Vault, private networking and secure production cookies remain target architecture. See [M18 evidence](docs/milestones/milestone-18.md) and [identity ADR](docs/architecture/decisions/0002-identity-verification-and-host-authority.md).

**Milestone 19 implements the [AI threat model and adversarial harness](docs/architecture/ai-threat-model-and-adversarial-testing.md):** 88 authored synthetic cases exercise workflow, SDK/tools, MCP, API/UI, human-review and identity boundaries. The original report remains **79 PASS / 1 FAIL / 8 NOT_TESTED**. Authorized [F-001/F-002 remediation](docs/milestones/milestone-19-remediation.md) adds independent source-bound MCP consumption and working-directory-independent CLI output protection; the unchanged catalog now records **80 PASS / 0 FAIL / 8 NOT_TESTED**. Live-model semantic resilience and production controls remain untested; historical findings and reports are preserved.

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
| [Retrieval evaluation methodology](docs/quality/policy-retrieval-evaluation.md) | Metric definitions, cohort denominators, integrity checks and limitations |
| [Authored retrieval queries](data/evaluation/policy-retrieval/README.md) | Frozen relevance/citation expectations and provenance |
| [Milestone 8 record](docs/milestones/milestone-8.md) | Measured offline results, failures and verification |
| [Provisional rule specification](data/rules/motor/README.md) | Fictional parameters, source provenance and 23 new synthetic scenarios |
| [Deterministic rule architecture](docs/architecture/deterministic-provisional-rules.md) | Policy/evidence gates, findings, arithmetic and human authority |
| [Milestone 9 record](docs/milestones/milestone-9.md) | Rule checks, boundaries, reproduction and limitations |
| [Agent Framework foundation](docs/architecture/agent-framework-foundation.md) | Actual SDK execution, host boundaries, typed tools and simulated client limitations |
| [Agent Framework dependencies](docs/dependencies/agent-framework.md) | Verified SDK APIs and exact tested runtime versions |
| [Milestone 10 record](docs/milestones/milestone-10.md) | Bounded offline integration, checks and remaining live-model limitations |
| [Governed agent tools](docs/architecture/governed-agent-tools.md) | Typed internal reads, host grants, scope/provenance checks and bounded SDK dispatch |
| [Milestone 11 record](docs/milestones/milestone-11.md) | Tool contract/security checks, offline reproduction and limitations |
| [Deterministic workflow](docs/architecture/deterministic-claims-workflow.md) | Six-stage orchestration, immutable records, bounded retry and checkpoint recovery |
| [Milestone 12 record](docs/milestones/milestone-12.md) | Workflow safety/integration checks, offline reproduction and limitations |
| [Governed MCP server](docs/architecture/governed-mcp-server.md) | Genuine stdio protocol, three read-only tools and trusted host context |
| [MCP dependencies](docs/dependencies/mcp.md) | Verified compatible APIs, exact runtime pins and official wheel provenance |
| [Milestone 13 record](docs/milestones/milestone-13.md) | Client/server tests, framework MCP execution and residual limitations |
| [Milestone 14 record](docs/milestones/milestone-14.md) | HTTP protocol/security tests, real TCP report and static APIM reference |
| [Governed human review](docs/architecture/governed-human-review.md) | Synthetic assignments, advisory-only actions, exact snapshot binding and immutable local audit |
| [Milestone 15 record](docs/milestones/milestone-15.md) | Human-review security, concurrency, packaging and reproduction evidence |
| [FastAPI application](docs/architecture/governed-fastapi-application.md) | Versioned endpoints, host scope, idempotency and HTTP safety |
| [Milestone 16 record](docs/milestones/milestone-16.md) | API/OpenAPI security, packaging and production limitations |
| [Reviewer operations UI](docs/architecture/governed-reviewer-ui.md) | Host enrollment, assigned cases, source detail and explicit recommendation actions |
| [Milestone 17 record](docs/milestones/milestone-17.md) | UI/API security, reproducible HTML/protocol and package evidence |
| [Identity/security foundation](docs/architecture/identity-and-security-foundation.md) | Synthetic verification/rotation/revocation and separate Entra/workload target architecture |
| [Milestone 18 record](docs/milestones/milestone-18.md) | Identity negative tests, unchanged authority, offline protocol/package evidence and production gaps |
| [AI threat model / adversarial evaluation](docs/architecture/ai-threat-model-and-adversarial-testing.md) | Attack paths, runtime evidence, open MCP finding and untested production scopes |
| [Milestone 19 record](docs/milestones/milestone-19.md) | Evaluation counts, regression/package checks, preserved evidence and acceptance limits |

## Local Python foundation

Python **3.12** is the initial supported minor version (`>=3.12,<3.13`); broader support requires testing. Base runtime dependencies are Pydantic v2 and pydantic-settings; the optional `agents` extra adds the pinned framework core and msgspec. The `mcp` extra includes those plus the genuine MCP SDK and the framework's required tenacity dependency. The optional `api` extra adds minimal pinned FastAPI support; `ui` reuses it and the existing pinned Uvicorn server. The optional `identity` extra reuses the already pinned PyJWT/cryptography packages for signed local verification. No live provider extra is included. `claims_ai.api.app.create_app` is an offline ASGI factory with deny-all defaults; production hosting and real authentication remain future work.

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -c requirements/m19-constraints.txt '.[dev,mcp,ui,identity]'
make check
make package
```

`make check` runs Ruff format/lint, strict mypy and pytest. `make format` formats source/tests. Tests explicitly load `src`; package installation is verified separately. `make package` builds a wheel and source distribution in ignored `dist/`, using installed setuptools without downloading build dependencies. Reinstall the package after runtime edits when using the non-editable setup above; source tests exercise current source and the packaging regression independently checks installed imports. On this managed macOS filesystem, hidden editable `.pth` files are skipped by Python; use the non-editable installation above rather than relying on editable discovery. See the M14 record for the verified diagnosis.

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

Evaluate the unchanged lexical retriever against authored expectations:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.retrieval_eval --output outputs/retrieval-eval/lexical-v1.json
```

Use a new output filename. Reports are labeled `OFFLINE_LEXICAL` and separate answerable, no-answer, safety, invalid-query and simulated technical-failure cohorts. Empty relevance sets do not enter ranking averages; outages cannot count as correct no-answers. `make retrieval-eval-check` runs focused metrics, leakage, citation, scope, malformed-label and reproduction tests. See M8 evidence for actual scores and four observed authored-expectation failures; independent relevance review remains outstanding.

Run the separate provisional rule demonstration:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.rules --output outputs/rules/provisional-v1.json
```

Use a new output filename. Reports label `OFFLINE_PROVISIONAL` findings and SIMULATED evidence/scan/reviewer assertions; they contain no final outcomes or settlement authority. The CLI generates new fixtures in memory and preserves all M4 cases and M7/M8 retrieval behavior. `make rules-check` runs focused binding, provenance, arithmetic and oversight checks. No additional dependency is required.

Run the genuine framework with its explicitly simulated offline client:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.agents --output outputs/agents/offline-v1.json
```

Use a new output filename. The six-case report includes review, adverse escalation, missing evidence, injected data, unsupported requests and a forbidden tool. Only validated case-bound packets can be read; outputs must preserve deterministic findings, citations and human/supervisor authority. `make agents-check` runs the focused SDK and safety tests. See the architecture guide for cooperative timeout limits and the distinction between tested framework mechanics and untested live model behavior.

Exercise the same assessment role with governed service-backed internal tools:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.agent_tools --output outputs/agent-tools/offline-v1.json
```

Use a new output filename. This ten-case demonstration covers authorized reads, adverse review, missing evidence, unauthorized/cross-case requests, wrong versions, malformed/forbidden calls, injected notes and a simulated retrieval outage. Host grants are synthetic assertions, not authentication tokens. `make agent-tools-check` runs focused real-SDK tool contract and security checks.

Run the complete offline advisory workflow:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.workflow --output outputs/workflow/offline-v1.json
```

Use a new output filename. Seven cases cover an advisory draft, missing evidence, a simulated retrieval outage, injected document content, adverse/high-risk escalation and serialized checkpoint resume. JSON includes full synthetic execution records; checkpoints are local caller-held artifacts, not signed or durable audit. `make workflow-check` runs focused workflow tests. The architecture guide documents trusted-input recovery and the separation between advisory tasks and operational outcomes.

Run real local MCP stdio clients against the governed server:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.mcp_server demo --output outputs/mcp/offline-v1.json
```

Use a new output filename. Native SDK and Agent Framework MCP clients each discover and call all three tools. Negative cases cover missing context, cross-case requests, wrong versions, forged authorization arguments and repeated calls. The host creates private temporary context files; standalone `serve` without context remains denied. `make mcp-check` runs protocol/security tests.

Run the real SDK HTTP protocol in-process, without a network listener:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.mcp_http demo --mode asgi --output outputs/mcp-http/offline-v1.json
make mcp-http-check
make apim-static-check
```

For a terminal permitting local sockets, replace `--mode asgi` with `--mode loopback` and use a new output filename. The latter binds only `127.0.0.1` on an ephemeral port, issues an in-memory synthetic credential, calls all three tools and stops; it is not a deployable backend. The supplied external report verifies that socket path; this sandbox still restricts binding. Shutdown evidence is qualified in the M14 record. No credential/key is written in either report. [APIM reference commands](infra/apim/README.md) compile templates without deployment.

Domain validation checks synthetic identifiers, object references, document/evidence hash metadata, policy-version metadata and caller-supplied evidence checklists. It does not scan files, resolve policy coverage or approve fictional insurance rules. Dataset validation additionally checks fixture bytes against hashes/source renderings; it is not live upload validation or malware scanning. Structured logging emits approved event names and allowlisted operational fields; arbitrary payloads and exception text are suppressed. Do not send raw model dumps or validation-error payloads to other loggers.

Run the synthetic human-review demonstration with a new output filename:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.human_review --output outputs/review/offline-v1.json
make review-check
```

Six cases cover recommendation approval, rejection, supervisor escalation/handling, evidence request, stale evidence and unauthorized access. Existing M12 simulated advisory preparation runs once; review admission/actions make no model calls. Storage and synthetic identities are explicitly local and non-durable. Evidence requests reuse M2; recommendation actions never close or settle a claim.

Run the genuine offline API/OpenAPI demonstration with two new output filenames:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.api --output outputs/api/offline-v1.json --openapi-output outputs/api/openapi-v1.json
make api-check
```

The host explicitly registers original synthetic bundles and human assignments. Clients cannot publish policies/grants, select reviewers, upload arbitrary documents or finalize claims. Failed or cancelled processing retains a volatile failure receipt instead of restarting uncertain work. M8's four failures, M12 timing sensitivity and M15 persistence limitations remain.

Run the offline synthetic reviewer UI:

```sh
.venv/bin/python -m claims_ai.reviewer_ui serve
```

Open the printed local `/login` URL and use a host-delivered one-time reviewer or supervisor code. Use separate browser profiles/private windows for simultaneous identities. The host seeds existing simulated cases through M16; browsers cannot choose roles/cases or supply API grants. Codes expire after five minutes; UI sessions expire after 15. Restarting loses all in-memory work. Approval means advisory recommendation approval only.

```sh
make ui-check
PYTHONPATH=src .venv/bin/python -m claims_ai.reviewer_ui demo --output outputs/ui/new-report.json --html-dir outputs/ui/new-html
```

Use new paths outside reference data. The report exercises all four actions, replay, stale review revisions, missing recommendations, supervisor enforcement and case isolation through actual UI/API requests. Four sanitized HTML captures have redacted nonces/tickets and disabled submission buttons; they are offline evidence, not live authenticated pages or screenshots. See the architecture guide for volatile storage, fixed synthetic audit time and browser/accessibility limitations.

Run the offline identity/security demonstration:

```sh
make identity-check
PYTHONPATH=src .venv/bin/python -m claims_ai.identity --output outputs/identity/new-report.json
```

Use a new output outside reference data. The report exercises real API/UI requests and genuine MCP SDK reads with a separate synthetic machine audience. Verification, host/session binding, key overlap/retirement, revocation and expiry remain local; no signing key, JWT, cookie or capability is recorded. The default opaque API profile has a 15-minute absolute lifetime; signed capabilities depend additionally on their shorter token/key validity. UI sessions may therefore end earlier. Live Entra, TLS, discovery, managed identity, Key Vault and APIM enforcement are not enabled.

Run the offline adversarial evaluation:

```sh
make adversarial-check
PYTHONPATH=src .venv/bin/python -m claims_ai.adversarial --output outputs/adversarial/new-report.json
```

Use a new output path. After [targeted remediation](docs/milestones/milestone-19-remediation.md), the corrected catalog exits **0** with **80 PASS / 0 FAIL / 8 NOT_TESTED**; genuine failed criteria still produce exit **2**. Eight live/production scopes remain NOT_TESTED. SDK/output guards are real, with simulated model behavior; in-process HTTP is not TCP or browser evidence. Original M19 reports, fixtures, M4–M9 data and M8 failures are preserved.

Git setup and all commits/pushes remain manual. **Milestones 1–19 are delivered within their recorded local/reference scopes.** Historical milestone records preserve their original scope; the current [roadmap](docs/milestones/roadmap.md) records delivered capabilities and planned later work. M20 has not started. The former M18 RAG/rules proposal is deferred; the approved M18 scope is identity/security, and the approved M19 scope is adversarial evaluation rather than additional agent implementation.
