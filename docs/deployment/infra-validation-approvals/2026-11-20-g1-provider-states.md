# Infrastructure validation verification record — stage 5 condition G1 (provider states)

**Recorded:** 2026-11-20T05:19:37Z · **Reported by:** repository-owner · **Baseline:** `cd8a814`

This record resolves condition **G1** of the
[stage 5 execution-template approval](2026-11-20-execution-template.md) (SHA-256
`1d69d8bbdc82551a3fcad00f7bd6d277e08b26c4cd26a5c85dd292d0650bf8ba`, unchanged). It's a
verification record, not an approval. No entry in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) changes;
the contract stays `PREPARATION_ONLY` with `provisioning_allowed=false`. The record is immutable;
corrections need a new dated supplement.

## Owner-reported read-only results (Azure Cloud Shell, subscription `OctoCAT-Agentic-AI`)

| Resource provider | Registration state |
| --- | --- |
| `Microsoft.KeyVault` | Registered |
| `Microsoft.ManagedIdentity` | Registered |
| `Microsoft.OperationalInsights` | Registered |
| `Microsoft.Insights` | Registered |
| `Microsoft.App` | Registered |

The owner reported these as read-only queries. No UTC timestamp was reported for the queries.

## Finding

**G1 is resolved for the five providers it named.** The evidence for each provider the template
uses differs:

| Provider | Evidence | `registrationState` |
| --- | --- | --- |
| `Microsoft.KeyVault`, `Microsoft.ManagedIdentity`, `Microsoft.OperationalInsights`, `Microsoft.Insights`, `Microsoft.App` | Owner's read-only query (this record) | **Confirmed `Registered`** |
| `Microsoft.Network` | Owner-reported registration under the [stage 3 approval](2026-11-20-provider-registration-execution.md) (`NotRegistered` → `Registered`) | **Confirmed `Registered`** (earlier observation) |
| `Microsoft.Consumption` | The subscription budget's PUT and GET succeeded ([execution record](2026-11-20-subscription-budget-execution.md)) | **Unverified**: not queried |

No further provider registration approval is needed for the five confirmed providers. The
provider-registration approval's restriction stays in force: no other provider, feature or
preview registration is approved.

**Residual:** `Microsoft.Consumption`'s `registrationState` remains unverified. A successful budget
operation shows the budget API worked; it isn't a recorded registration state. If confirmation is
needed, it requires a separate read-only query.

All states are point-in-time observations. If any provider is later found `NotRegistered` (for
example, in stage 6 validate or what-if), stop for owner review; don't let a deployment register
it.

## Still open

- **G2 (blocks stage 6):** six `approved_values` remain `null`: `location`, `resource_group`,
  `include_container_environment`, `log_daily_quota_gb`, `expires_at`, `subscription_id`. That
  includes the owner decision on publishing the subscription ID. **Stage 6 stays blocked.**
- **G3:** budget end date later than `expiresAt` needs owner acceptance.
- **G4–G8:** unchanged as recorded in the stage 5 approval.

Neither repository Bicep gate changes. M22 restrictions, M23 SECURITY GATE NO-GO, M24's six
NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
