# APIM governance reference — M14

Status: **reference artifacts with static validation and local Bicep compilation only**. No Azure login, deployment, Entra token, APIM policy execution or service cost occurred. Documentation was checked on 2026-10-31; tenant capacity, actual prices and runtime interoperability remain unverified. See [HTTP trust boundaries](../architecture/mcp-http-and-gateway.md).

## Verified platform documentation

Microsoft documents external MCP Streamable HTTP/SSE with MCP 2025-06-18 or later, across Developer/Basic/Standard/Premium and their v2 tiers. Workspaces are unsupported. The reference selects only three tools and does not rely on prompts/resources. Response-body policy inspection and global frontend-response payload logging must be disabled to preserve streaming. [External MCP guidance](https://learn.microsoft.com/en-us/azure/api-management/expose-existing-mcp-server).

The MCP management surface uses API version `2025-09-01-preview` or later. [Management guidance](https://learn.microsoft.com/en-us/azure/api-management/manage-mcp-servers-rest-api) and the [ARM API schema](https://learn.microsoft.com/en-us/azure/templates/microsoft.apimanagement/2025-09-01-preview/service/apis) support a passthrough MCP API with `transportType: streamable`; the template uses the schema's endpoint array. Preview schema compilation is not resource-provider acceptance or a compatibility guarantee.

## Separate authentication hops

Inbound client authentication is an APIM requirement: validate the configured Entra tenant, client application, gateway audience and `Claims.Read` application role. A subscription requirement is supplementary, never authorization. The reference is app-only; delegated user/OBO scopes and case assignments need a separate approved design. [Entra token policy](https://learn.microsoft.com/en-us/azure/api-management/validate-azure-ad-token-policy).

APIM-to-backend authentication uses a different audience and the gateway's system-assigned managed identity with least-privilege backend application permission. Remove client Authorization and forged context headers before generating the backend credential. The backend must independently validate the gateway service token and obtain a trusted workflow/case grant; neither token possession nor a claim-ID header proves case permission. Policy editors can exercise the gateway identity, so restrict and review publishing rights. [Managed-identity policy](https://learn.microsoft.com/en-us/azure/api-management/authentication-managed-identity-policy).

## Reference controls and evidence

| Artifact/control | Implemented reference | Verification limit |
| --- | --- | --- |
| [XML policy](../../infra/apim/mcp-policy.xml) | Tenant/app/audience/role pins; validated-identity rate key; exact RPC/tool allow-list; fail-closed malformed envelope; forged-header deletion; separate backend MI | XML/invariant and mutation tests; C# expressions and actual gateway status mapping unexecuted |
| Request limits | 16 KiB APIM size guard plus strict backend actual-byte bound | APIM documents size validation using Content-Length; local backend tests reject misleading lengths; no live gateway/body interoperability result |
| Throttling | 12 requests/60 seconds per validated client object/API; local backend independent 12/60 counter | Local 429/window tests only; APIM distributed limiting is approximate, not a hard global security budget |
| Diagnostics | No payload reads, no trace/events, four request/response capture limits zero, no header/IP capture, no-store and sanitized errors | Static checks only; inherited/global diagnostics, sampling, retention and privileged tracing require future review |
| [Bicep](../../infra/apim/reference.bicep) | Existing APIM only, HTTPS backend, subscriptions, named identifiers, policy and zero-payload diagnostic reference | Actual Bicep compilation; no provisioning, identity assignment, DNS, logger or private network configuration |

References: [content limits](https://learn.microsoft.com/en-us/azure/api-management/validate-content-policy), [rate limiting](https://learn.microsoft.com/en-us/azure/api-management/rate-limit-by-key-policy). Client JSON bodies remain untrusted; APIM filtering is defense in depth, while unchanged M11 validation authorizes every read. Review inherited `<base />` policies and global diagnostics before any future publication; API-level settings do not certify the entire service.

Both `deploymentEnabled` and `prerequisitesVerified` default false. All new resources require both gates; the supplied [dev parameters](../../infra/apim/reference.dev.bicepparam) keep them false. IDs/audiences/host/logger are conspicuous non-secret placeholders. The parameters describe environment candidates, not provisioned service properties: APIM is `existing`, so region/tier selection does not move or resize it. Use separate instances/identities/grants and reviewed parameters for dev/test/prod. There is no deployment script, public-ingress creation or automatic authorization.

Static validation rejects selected security regressions; it is not a policy engine or full Bicep parser. Actual compilation used official Bicep **0.48.1 (cec7951cf6)**, temporary macOS arm64 binary SHA-256 `62cd5958c62fa1b738e9b69f24799fabddb90ed83fdb7d6d2563dde376ce479d`, verified against [official release metadata](https://github.com/Azure/bicep/releases/tag/v0.48.1). `make apim-compile` built both templates without warnings/errors. Compiler output is local and ignored by Git.

## Capacity, location and costs

| Topic | Verified constraint / remaining decision |
| --- | --- |
| Tier | MCP tier support is documented above; Developer is for nonproduction and lacks an SLA. Standard v2 is the candidate, not an approved purchase. Consumption is outside this reference. |
| Network | Standard v2 supports inbound private endpoints plus outbound VNet integration; Premium v2 offers further network options. Select private DNS, approved backend ingress and egress, and disable public access only after private access is validated. VNet/region/subscription restrictions require design review. [Private endpoints](https://learn.microsoft.com/en-us/azure/api-management/private-endpoint), [v2 networking](https://learn.microsoft.com/en-us/azure/api-management/v2-service-tiers-overview). |
| Region/capacity | UK South and West Europe are proposals only. Check tier/feature availability, subscription quotas and actual allocatable capacity before procurement; a listed region is not a reservation. No tenant/subscription capacity was queried. [Service limits](https://learn.microsoft.com/en-us/azure/api-management/service-limits). |
| Residency | Policy wording, evidence, replicas, logs, backups and support access require an approved geography/data-flow inventory. Do not infer residency compliance from a region name; review selected service terms and dependencies. This requirement remains unverified, not a compliance claim. |
| Independent quotas | Foundry model deployment availability, model tokens/requests, Document Intelligence, Search, Container Apps and APIM limits are independent. A working SDK or APIM tier does not establish regional model quota. No quota was requested. |
| Cost | APIM v2 unit charges, request overage, private networking/DNS, bandwidth, backend compute and telemetry are separate risks. A portfolio gateway can incur fixed idle charges. No current currency/region quote was available from the public price page; no numeric monthly estimate is asserted. [Pricing](https://azure.microsoft.com/en-us/pricing/details/api-management/). |

Planning estimate: `monthly budget = 730 × quoted hourly gateway units + quoted request overage + private networking/DNS + compute + storage/egress + telemetry`. Fill each term from a dated regional quote, include taxes/currency and preview/tier assumptions, then approve a ceiling before deployment. Budget alerts are not hard spending stops; use small nonproduction capacity, log retention/ingestion caps, invocation limits, model budgets and explicit teardown. **Actual spending for this milestone: zero cloud operations.**

Deployment prerequisites remain: approved budget and region/residency, supported APIM tier/API version, private gateway/backend networking and DNS, reviewed global policies/diagnostics, real Entra applications/roles and MI permission, production backend JWT verifier, trusted expiring/revocable case-grant service, policy expression tests against a future authorized APIM instance, and operational lifecycle checks for the future production backend. The local loopback protocol report is reviewed in M14 with explicit shutdown-evidence limits; it does not establish these cloud prerequisites. M14 does not authorize these actions.
