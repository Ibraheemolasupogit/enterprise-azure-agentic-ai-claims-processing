# Milestone 1 — Project charter and architecture baseline

Status: **COMPLETE — documentation scope only**, 2026-10-30. No runtime implementation, evaluation results, simulation or deployment is claimed. Milestone 2 has not started.

## Delivered files

- [README](../../README.md): purpose, scope, planned capabilities and evidence disclaimer.
- [Project charter](../business/project-charter.md): fictional stakeholders/process, motor scope and proposed business measures.
- [Target architecture](../architecture/target-architecture.md): flow, components, planned contracts, two justified agents and deterministic boundaries.
- [Security and governance](../architecture/security-and-governance.md): trust, access, privacy, oversight and release requirements.
- [Evaluation and observability](../quality/evaluation-and-observability.md): proposed golden suite, metrics, telemetry and failure behavior.
- [Deployment strategy](../deployment/deployment-strategy.md): service mapping, Bicep/CI approach, environment/capacity gates and cost controls.
- [Roadmap](roadmap.md): incremental milestones and evidence requirements.
- This milestone record.
- [.gitignore](../../.gitignore): Python, macOS, local environment, credential and generated-output exclusions.

## Baseline decisions

1. Greenfield fictional Northstar motor damage workflow; original hackathon source was not located and will not be searched further. No training repository is treated as an imported implementation. Separate from Agentic SDLC.
2. Two bounded agents justify semantic reconciliation and reviewer explanations. Deterministic code owns policy selection, rules, calculations, authorization and transitions. Policy rules are not inferred or enforced through prompts.
3. All initial outcomes require a human; high-risk/ambiguous/adverse cases require a supervisor. No payments, autonomous rejection or real insurer integration.
4. Every assessment pins evidence hashes, policy/endorsement bundle, rule/index/model/prompt versions and provenance. Retrieval cannot widen to another policy when evidence is missing.
5. FastAPI/Container Apps with PostgreSQL, Blob, Service Bus/outbox; Foundry/Agent Framework, Document Intelligence, AI Search and governed MCP/APIM remain proposed integrations.
6. Synthetic-only evaluation and operational evidence are prerequisites for capability claims. Region, capacity, model quotas, APIM tier and costs are deployment gates, not assumed availability.

## Verification and limits

- Rechecked the workspace before writing: empty directory, no existing implementation or local instruction files. Prior discovery established no Git repository; this milestone does not initialize one.
- Checked the nine-file deliverable set, nonempty content, UTF-8, local Markdown targets/anchors, Markdown fence balance, whitespace and final newlines using standard-library/file checks.
- Reviewed consistency of synthetic-only scope, planned runtime status, agent boundaries, human approvals, policy provenance, storage/workflow design, deployment gates and roadmap status across the documents.
- Checked all nine unique external reference URLs and consulted linked Microsoft documentation for Agent Framework, Search, APIM, Foundry deployment/quota, telemetry, prompt defenses and budget behavior. These support design constraints, not subscription verification.
- Git status/repository diff checks are not available because this directory is not a Git repository. Direct whitespace checks and per-file `git diff --no-index --check` against an empty baseline passed; normal new-file difference exit codes are expected. No Markdown renderer/Mermaid runtime, executable application tests, benchmark, dependency installation, Azure call or cloud deployment was run.

## Assumptions, risks and remaining gaps

The business process, GBP motor-product scope and stakeholder roles are fictional assumptions. No policy wording, executable rules, schemas or synthetic cases exist yet; a policy owner/reviewer must approve their initial definitions. Targets are provisional, and the 60-case proposed suite cannot establish production validity.

Unresolved choices include model/SDK versions, extraction strategy/thresholds, UI technology, scanning engine, APIM tier, network/SKU compatibility, region/residency, quota, fixed-service affordability and numeric budget limits. Documentation does not prove managed identity support end to end, transaction/replay correctness, audit immutability, deletion, backup restore, safety or availability. Retention periods need approval; no regulatory compliance claim is made.

All application, agents, rules, RAG, UI, MCP/APIM, security controls, tests, telemetry, Bicep and GitHub Actions remain **PLANNED**. The next proposed work is Milestone 2 only after review. This milestone stops at the nine requested artifacts; Git operations remain manual.
