# Infrastructure validation approval record — scope amendment: one subscription-level budget

**Recorded:** 2026-11-20T01:11:18Z · **Approver:** repository-owner · **Baseline:** `bfe89e6`

This record amends the `scope` approval in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json). On
recording, the `scope` approval's evidence reference moves from the original scope record to this
record. The **original record is preserved unchanged** and remains incorporated by reference:
[2026-11-20 scope and cost exposure](2026-11-20-scope-and-cost-exposure.md), SHA-256
`ccfa1bab06bed7065f7339a417b4b487e4e6541245c7c9b10beedcfec356cd4f`. It's still the evidence for the
`cost_exposure` approval. This record is immutable; any further change needs a new dated record.
The contract stays `PREPARATION_ONLY` with `provisioning_allowed=false`, and **no Azure action is
authorised by this record**.

## Approved scope after amendment

1. **Unchanged — the seven-resource in-group deployment** approved in the original record:
   network security group, virtual network, user-assigned managed identity, Key Vault, Log
   Analytics workspace, Key Vault diagnostic setting and resource-group budget, deployed only into
   `rg-claims-infraval-uks-tmp01` from `infra/azure-validation/main.bicep`. The Container Apps
   environment stays disabled, the subscription is `OctoCAT-Agentic-AI`, the region is `uksouth`,
   and the maximum execution window is 2 hours. The template is unchanged.
2. **Added — exactly one subscription-scope object outside that group:**

| Property | Approved value |
| --- | --- |
| Type | `Microsoft.Consumption/budgets` (Cost Management; no charge) |
| Scope | Subscription `OctoCAT-Agentic-AI` |
| Name | `infraval-uks-tmp01-budget` |
| Filter | `dimensions: { name: "ResourceGroupName", operator: "In", values: ["rg-claims-infraval-uks-tmp01"] }`, the form used by Microsoft's Azure Quickstart `create-budget` template and the Azure Verified Modules `sub-scope` budget module |
| Purpose | Cost alerts that exist **before** provisioning and persist **after** deletion of the group |

No other object outside the group is added. `NetworkWatcherRG` remains governed separately by
Network Watcher Option A in the [Stage 1 network record](2026-11-20-stage1-findings-and-network.md).

## Conditions

- **Outside the existing plans.** The subscription budget isn't deployed by the template, so it's
  not part of the what-if (which still expects exactly seven in-group `Create`s). It's outside the
  fail-closed teardown plan, which acts only inside the dedicated group and never deletes it.
- **Creation needs a separate owner approval.** This amendment authorises the object's inclusion
  in scope, not its creation. Its values (amount, currency, notification alias, thresholds, dates)
  are **unresolved** and belong to the stage 4 `budget` approval.
- **Deletion needs a separate owner approval.** The budget is retained for the +24 h and +72 h
  post-teardown cost monitoring, or until its approved expiry (end date), whichever the owner
  approves. It's then either explicitly deleted under that approval or auto-deleted at expiry.
- **Unchanged:** the validator and both Bicep deployment gates (`@allowed([false])`). All
  `approved_values` and `execution` fields remain `null`. M22 restrictions, M23 SECURITY GATE
  NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
