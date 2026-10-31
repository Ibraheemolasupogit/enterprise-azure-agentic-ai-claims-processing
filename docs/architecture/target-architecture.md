# Target architecture

Status: **PLANNED runtime architecture**. [Milestone 2](../milestones/milestone-2.md) implements and locally tests domain contracts, in-memory transition guards, configuration, redacted logging and typed protocols. [Milestone 3 requirements](../business/requirements.md) refine business acceptance/traceability without changing contracts or this design. Azure services, live model workflows, API/UI, persistence/audit and approved operational coverage rules remain unimplemented. This is an independent greenfield design for the [charter](../business/project-charter.md).

[Milestone 4](../milestones/milestone-4.md) adds offline synthetic artifact authoring, source-linked annotations and byte/reproduction validation. These tools do not implement any processing component below: intake remains quarantined, and authored labels are not extracted facts, approved policies or operational decisions.

[Milestone 5](../milestones/milestone-5.md) adds a separate model-neutral benchmark transport and fixture-only extraction harness. Typed Azure/Mistral/GPT adapter interfaces are not live integrations; SIMULATED ground-truth echoes do not change the operational `DocumentProcessor` contract or promote quarantined evidence. No architectural authority boundary changes.

[Milestone 6](../milestones/milestone-6.md) implements the deterministic, local [structured-evidence boundary](structured-evidence-processing.md) within step 3 below: typed mapping, source/hash/ownership checks, normalization, quality holds, immutable caller-held history and guarded in-memory admission. Independent quote verification currently supports generated single-page fixtures only; other inputs stay quarantined. Original M4 cases remain unchanged and the offline demonstration admits no evidence. Intake/scanning, authenticated assertions, repository integration and durable audit remain planned. Agent, rule and human-decision authority is unchanged.

[Milestone 7](../milestones/milestone-7.md) implements an offline [draft-policy parser and lexical retriever](policy-knowledge-retrieval.md), composing existing policy/clause/citation contracts. Case-bound indexes retain verified source lines, version/effective dates and deterministic chunk IDs; exact-version/date filters, snapshot/source validation and abstentions precede token scoring. This is an unapproved fixture-authoring path, not approved policy publication/resolution or the hybrid Search component below. The Azure AI Search adapter is a protocol only. No embeddings, case policy activation, agent, coverage authority or lifecycle changes are introduced.

[Milestone 8](../milestones/milestone-8.md) measures that unchanged lexical implementation against [authored, source-pinned query expectations](../quality/policy-retrieval-evaluation.md). The offline evaluator separates engine inputs from labels and reports ranking, citation, version/scope and abstention diagnostics by compatible cohort. Labels are not independently adjudicated, and no hybrid Search, generated-answer or coverage evaluation is claimed. Architectural authority boundaries remain unchanged.

[Milestone 9](../milestones/milestone-9.md) adds a separate [provisional rule foundation](deterministic-provisional-rules.md) with exact version/source/evidence checks and explicitly fictional financial parameters. Four-state findings and non-binding integer-pence illustrations do not populate operational `Assessment`/`RuleResult` outcomes, change a case or authorize settlement. New in-memory fixtures use explicit SIMULATED scan/reviewer assertions; original M4 policies remain unapproved and unchanged. This is the user-authorized offline exception for provisional experimentation; the approved-policy/rule publication gate, human/supervisor guards and operational deployment boundaries below remain intact. M8's four lexical failures remain unresolved.

## Logical components and data flow

[Milestone 10](../milestones/milestone-10.md) implements a genuine [Microsoft Agent Framework review foundation](agent-framework-foundation.md) using installed core SDK 1.23.0 and a supported SIMULATED offline client. One argument-free, read-only tool exposes a single host-validated packet; the real framework dispatches it and parses typed output. Host code rechecks M6/M9 evidence/findings and exact M7 citations before execution, then enforces output provenance, bounded execution and human/supervisor routing. This assistant occupies the existing policy-explanation responsibility; rules, version resolution, authorization and lifecycle changes remain outside it. Live reasoning, evidence reconciliation, providers and durable orchestration remain planned. The [dependency record](../dependencies/agent-framework.md) records actual APIs/versions. The diagram below remains the target service architecture, not a deployed system.

[Milestone 11](../milestones/milestone-11.md) extends the same assessment responsibility with [governed internal tools](governed-agent-tools.md), not another agent. Real SDK functions read verified evidence, exact-version clauses and provisional deterministic findings through local service methods. A trusted host grant binds case/fingerprint/correlation and permissions; each tool validates scope before reads and validates result provenance before release. Final drafts retain M10 validation and human/supervisor controls. These internal controls do not implement authentication, MCP/APIM or the target cloud tool gateway.

```mermaid
flowchart TD
    User[Authenticated intake and reviewer UI] --> API[FastAPI case API]
    API --> DB[(PostgreSQL case state and audit)]
    API --> Blob[(Blob evidence quarantine)]
    DB --> Relay[Transactional outbox relay]
    Relay --> Queue[Service Bus work queue]
    Queue --> Worker[Container Apps workflow worker]
    Blob --> Scan[Isolated file validation and malware scan]
    Scan --> Clean[(Blob accepted evidence)]
    Clean --> Worker
    Worker --> DI[Document Intelligence]
    Worker --> AF[Agent Framework bounded steps]
    AF --> Models[Microsoft Foundry models]
    Worker --> Rules[Policy resolver and deterministic rules]
    AF --> Tools[Typed tool authorization boundary]
    Tools --> Search[AI Search approved policy index]
    Tools --> Gateway[APIM governed MCP tools]
    Gateway --> Services[Synthetic policy and case-read services]
    Worker --> DB
    API --> Review[Human review and supervisor escalation]
    Review --> API
    Indexer[Approved policy ingestion and embedding] --> Search
    Indexer --> Policy[(Versioned policy artifacts in Blob)]
    Policy --> Rules
```

OpenTelemetry spans/logs/metrics from API, relay, workers, model/tool calls and dependencies will export to Application Insights. The protected audit ledger is separate from sampled operational telemetry.

1. The API authorizes case access, issues a scoped upload path and creates a case with an idempotency key. Uploaded files remain quarantined until type/size, parser and malware checks succeed. A proposed isolated scanning worker must be proven before any model reads a file; unscannable files require review.
2. PostgreSQL commits case changes and outbox events atomically. A relay publishes work; workers tolerate duplicate delivery through step keys, optimistic case revisions and persisted checkpoints. Blob upload completion is verified and hashed before processing; orphan uploads expire by lifecycle policy.
3. Document Intelligence extracts text, layout and fields. A Foundry multimodal step describes visible photo evidence when needed. Normalization validates types, currencies, dates and evidence references; missing fields remain unknown rather than guessed.
4. Deterministic policy resolution uses the synthetic policy register, policy schedule, loss date and endorsements. It must produce one authoritative policy-version bundle. Missing, overlapping or conflicting mappings block assessment and require review.
5. The policy index stores approved clauses with product, jurisdiction, policy ID/version, endorsement, effective interval, page/section, artifact hash and chunk ID. Server-generated filters restrict **both keyword and vector retrieval** to the resolved bundle and authorized scope. Vector queries use prefiltering; no unfiltered fallback is allowed. Empty results cause abstention. Hybrid search combines keyword and vector retrieval ([Microsoft documentation](https://learn.microsoft.com/en-us/azure/search/hybrid-search-overview)); [filter behavior](https://learn.microsoft.com/en-us/azure/search/vector-search-filters) requires explicit configuration.
6. Code evaluates a separately approved, versioned rule pack against validated facts. Results are `eligible`, `ineligible` or `undetermined`, each with rule IDs and evidence references. Coverage dates, exclusions, required evidence, excesses and limits live in code/data rules, never in prompts. Money uses decimal/minor-unit arithmetic. Uncertain facts yield `undetermined`; rule-pack/policy mismatch blocks processing.
7. A reviewer receives the facts, cited clauses, rule trace, draft explanation, uncertainties and escalation reasons. Every initial outcome requires a human action. Adverse, ambiguous, conflicting, injection-flagged or unsupported cases require supervisor review. Human overrides preserve the original assessment and require reasons and evidence.

Policy publication is a separate authorized pipeline: approve artifacts and rule mappings, validate version metadata, index immutable chunks, evaluate retrieval, then activate an index version. Each assessment pins an index version; reindexing cannot silently change an existing recommendation.

## Agent versus code boundaries

[Microsoft Agent Framework](https://learn.microsoft.com/en-us/agent-framework/overview/) is the proposed library for explicit workflows and bounded model/tool steps. PostgreSQL remains the authoritative durable case state; framework checkpoint compatibility and restart behavior require testing. Foundry supplies model inference; hosted-agent deployment is not assumed.

| Proposed agent | Why an agent is justified | Allowed behavior and limits |
| --- | --- | --- |
| Evidence reconciliation agent | Forms, estimates, narratives and photos can describe the same event inconsistently; semantic comparison helps surface contradictions that field validation alone misses. | Read case-scoped evidence through typed tools; propose fact candidates, discrepancies and requests for evidence. Cannot certify truth, change canonical facts or decide coverage. |
| Policy explanation agent | Reviewers need a concise synthesis of applicable clauses, validated facts and rule results, including conflicting evidence. | Retrieve only the resolved policy bundle; draft cited explanations and unresolved questions. Cannot select policy versions, invent rules, override results or approve outcomes. |

Each agent has bounded tool calls, tokens and wall time, schema-validated output and separate instructions/tool grants. A deterministic workflow orders them; no free-running supervisor agent is required. OCR, authorization, retrieval filters, calculations, routing, retries and persistence are ordinary code. Agent necessity must be compared against a simpler non-agent baseline during evaluation; remove complexity if it provides no measurable benefit.

[ADR-0001](decisions/0001-decision-authority.md) records this existing authority boundary. The [requirements traceability matrix](../business/traceability-matrix.md) distinguishes implemented contract/local guards from planned agents, authorization and durable workflow enforcement. Claimant, operator and compliance/audit responsibilities do not add values to the implemented `ReviewerRole` enum.

Typed tools will include `get_case_evidence`, `retrieve_policy_clauses` and `get_rule_assessment`. Schemas will bound arguments/results and carry provenance. Authorization derives case scope from the authenticated workflow, never a model-provided identity. MCP exposes selected read-only synthetic service operations behind APIM; private SDK adapters serve extraction/search. Both paths enforce the same grants. There is no agent tool for final decision, arbitrary HTTP, shell, SQL or file access.

## Contracts and case lifecycle

The table defines the target contracts. Milestone 2 supplies foundation models and validation; Milestone 6 verifies supplied artifact bytes and generated source quotes locally. General document indexing, authenticated artifact/scan assertions, policy approval/resolution, service-produced assessments and durable review/audit enforcement require later milestones. A transition or evidence admission returns validated in-memory snapshots for future atomic persistence, not evidence of a persisted outcome.

| Contract | Required information |
| --- | --- |
| Claim | Schema version, synthetic case/policy IDs, loss timestamp/timezone, vehicle reference, narrative, claimed amount/currency and case revision |
| Evidence | Evidence ID, artifact hash, media type, source page/bounding region or image reference, extraction method/version, observed value, normalized value, confidence and validation flags |
| Policy bundle | Schedule/wording/endorsement IDs and hashes, effective interval, applicable version, index version and approved rule-pack version |
| Assessment | Input snapshot hashes, model/deployment/prompt/tool versions, rule results, clause/evidence references, uncertainty flags and proposed routing |
| Review/outcome | Assessment revision, reviewer identity/role, approved facts, outcome/reason, overrides, timestamps and append-only audit event IDs |

Confidence scores are not calibrated probabilities. Define thresholds from the synthetic evaluation set. Record concise evidence-backed rationales, not hidden chain-of-thought.

Lifecycle: `received → validating → extracting → assessing → awaiting_review → closed`. Branches are `awaiting_evidence`, `quarantined` and `processing_failed`; recoveries re-enter through explicit authorized transitions. Supervisor review is an assignment within `awaiting_review`. Closing requires an authorized reviewer, current case revision and persisted audit event. Evidence/policy/rule changes invalidate prior assessments and reopen review; agents cannot close cases.

The minimum reviewer UI will show original evidence, corrections, citations, rule trace and approval/override history. Its UI technology is deferred. See [security](security-and-governance.md), [evaluation](../quality/evaluation-and-observability.md) and [deployment](../deployment/deployment-strategy.md) for cross-cutting requirements.
