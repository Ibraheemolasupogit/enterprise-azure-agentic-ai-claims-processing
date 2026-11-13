# Deployment strategy

Status: **M23 Stage A offline definitions implemented; Azure execution remains unapproved.** Gated Bicep, container/build contracts and workflow definitions now exist. No Azure account/subscription access, live quota checks, resources, deployments or spending have occurred. All service/SKU choices require later verification. See the [target architecture](../architecture/target-architecture.md).

## Proposed service mapping

| Service | Intended responsibility |
| --- | --- |
| Container Apps + Azure Container Registry | FastAPI API, workflow/outbox/scanning workers and later reviewer UI; immutable image digests and bounded scaling |
| Microsoft Foundry | Approved multimodal/chat and embedding deployments; models/versions selected after evaluation and capacity checks |
| Azure Document Intelligence | Document OCR/layout/field extraction; choose prebuilt/layout/custom approach from synthetic evidence |
| Azure AI Search | Versioned policy clause index, keyword/vector hybrid retrieval and enforced metadata filters |
| Blob Storage | Quarantined/accepted synthetic evidence, immutable policy artifacts and controlled audit exports |
| Azure Database for PostgreSQL Flexible Server | Case state, review history, rule/policy metadata, transactional outbox and audit ledger |
| Service Bus | Background work delivery, bounded retries and dead-letter handling |
| API Management | Govern selected MCP tools/REST operations; authentication, throttling and trace correlation |
| Entra ID + managed identities + Key Vault | User/workload identity, narrow grants and exceptional secret storage |
| Application Insights + Log Analytics/Azure Monitor | OpenTelemetry destination, dashboards and operational alerts |
| Azure AI Content Safety, where supported | Prompt-injection detection as an additional control, subject to evaluation |

Agent Framework is an application dependency, not a separate service commitment. No dedicated hosted-agent service, GPU compute or provisioned model capacity is required by this baseline. Malware scanning is a required worker capability whose engine and operational limits remain unselected.

## Bicep and environment approach

Later Bicep modules will separate identity/RBAC, networking/DNS, data, messaging, AI/search, APIM, compute and monitoring/budgets. Environment parameters select region, SKUs, resource names, limits and tags; never contain secrets. Validate templates, run a reviewed `what-if`, then deploy only with explicit authorization and a spending ceiling. Role-assignment deployment privileges must be separated from runtime identities.

Local development uses synthetic fixtures and explicit service stubs. Azure dev/test environments have distinct identities, stores, queues, indexes, Foundry projects/deployments and budget tags; prefer separate subscriptions, otherwise separate resource groups with access boundaries. Prod is a future reference configuration, not a real-insurer deployment promise. Never share case data, secrets or writable indexes between environments.

GitHub Actions is planned only after manual Git/repository setup. CI will lint/test, scan secrets/dependencies/images, evaluate synthetic regressions and validate Bicep. Environment-protected deployment jobs will use OIDC, reviewed infrastructure changes, pinned actions and immutable image digests. Record deployment manifests and smoke-test results. Use Container Apps revisions for application rollback; schema migrations require compatibility/restore planning, and policy/index/rule versions activate together. Rollback cannot silently reinterpret closed cases.

## Region, quota and APIM lessons recorded as constraints

These are planning lessons from the project brief and documented platform constraints, **not failures observed in this repository**:

- A preferred region does not establish model support, subscription access, quota or live capacity. UK South is a candidate preference only; no region is selected. Before provisioning, record service/SKU support, model/version/deployment type, TPM/RPM, Document Intelligence limits, Search vector capacity, Container Apps quota, PostgreSQL capacity and APIM availability in a compatibility matrix. [Foundry quota guidance](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/quotas-limits) describes quota/rate limits; quota allocation does not prove a deployment will succeed.
- Model resource location and inference-processing geography are different decisions. Global and data-zone deployments have different routing boundaries; a UK resource location alone must not be described as UK-only inference. Approve residency and permitted fallback regions/types before deployment ([deployment types](https://learn.microsoft.com/en-us/azure/foundry/foundry-models/concepts/deployment-types)). No automatic cross-region/model fallback: each candidate needs evaluation and governance approval.
- APIM availability depends on tier, region and supported MCP features. Current documentation lists classic Developer/Basic/Standard/Premium and Basic/Standard/Premium v2 for MCP management; do not assume Consumption support. MCP resources/prompts and workspace support have documented limitations. Recheck [APIM MCP availability](https://learn.microsoft.com/en-us/azure/api-management/mcp-server-overview) before SKU selection. Developer is a possible nonproduction option only, not a production availability claim.
- If a required service is unavailable or unaffordable, pause cloud deployment or use a clearly labeled local simulation. Do not bypass the gateway in a deployed environment or label simulated integration as tested Azure behavior.

Documentation was consulted for this baseline on 2026-10-30. It cannot verify actual subscription eligibility, prices, regional supply, permission grants or deployment success.

## Cost controls and operational gates

Approve a GBP monthly budget and per-run model/page caps before paid work; no amount is approved yet. Plan owner/environment/expiry tags, staged provisioning, lowest compatible nonproduction SKUs, bounded replicas/concurrency, token/tool/page/upload limits, embedding deduplication and telemetry retention/sampling. Scale compute down where supported; Search, APIM, database and other fixed resources can continue billing while idle. Document teardown/restore procedures and verify residual billable resources after authorized cleanup.

Use budget alerts at proposed 50/80/100% thresholds plus application usage limits and a model-work kill switch. [Azure budgets](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets) notify; they do not stop consumption. Pricing estimates must include fixed service charges, inference, extraction, storage, telemetry and network traffic; no cost figure is claimed here.

Cloud entry requires approved region/quota matrix, spend ceiling, identity/network design, synthetic dataset and release tests. Cloud exit requires smoke/security/recovery evidence, restore exercise, operational owner and reviewed cost/retention records. There is no multi-region availability or recovery-time claim until demonstrated.

## M23 Stage A implementation boundary

[The offline foundation](../milestones/milestone-23-stage-a.md) supplies [modular Bicep](../../infra/azure/README.md), separate disabled dev/test/prod parameters, private API/UI/MCP targets, permanently disabled deployment workflow, local static/build/smoke contracts and [dated unverified matrices](m23/README.md). Required data/identity/telemetry adapters, Linux artifact review, actual GitHub environment protection/OIDC, Monitor private link and private-network interoperability remain missing. The templates cannot be enabled by their parameters; Stage B requires a separately reviewed change and explicit Azure/spending authorisation.

The smallest future slice is synthetic-only dev, registered fixtures, advisory human review and three read-only MCP tools. It does not enable arbitrary uploads, operational policy rules, new outcome endpoints or live Foundry/Document Intelligence/Search/model services. [Adapter requirements](m23/adapter-requirements.md) preserve current human authority and atomic audit/outbox. [Lifecycle gates](m23/lifecycle-and-approvals.md) separately govern cloud validation, provisioning, deployment, migration/restore/rollback and teardown. Local Bicep compilation and static checks are not the roadmap's actual Azure integration/cost exit evidence. M24 remains unstarted.
