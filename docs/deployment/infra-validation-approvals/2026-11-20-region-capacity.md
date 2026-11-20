# Infrastructure validation approval record — region and capacity

**Recorded:** 2026-11-20T00:39:42Z · **Approver:** repository-owner · **Baseline:** `41fd2b9`

This record is the evidence for the `region_capacity` approval in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) (checklist
stage 1). It's an immutable record. The contract stays `PREPARATION_ONLY` with
`provisioning_allowed=false`, and **no Azure action is authorised by this record**.

## Completion criterion (recorded earlier)

The [Stage 1 findings record](2026-11-20-stage1-findings-and-network.md) left `region_capacity`
pending only for live network quota. It stated it could be completed "after stage 3
registration, by re-running `az network list-usages --location uksouth` and confirming VNet and
NSG headroom". Default limits weren't to be treated as live quota.

## Evidence

| Requirement | Evidence | Source |
| --- | --- | --- |
| Subscription | `OctoCAT-Agentic-AI`, Enabled | Owner-reported, 2026-11-20 |
| Region | `uksouth`, within the template's allowed regions | Approved scope; compiled template |
| Type support in UK South | All five regional types supported (VNet, NSG, user-assigned identity, Key Vault, Log Analytics workspace) | Owner-reported provider metadata ([findings](2026-11-20-stage1-findings-and-network.md)) |
| SKU offering in UK South | Key Vault Standard and Log Analytics pay-as-you-go ingestion meters listed for `uksouth` | Azure Retail Prices API, 2026-11-19 |
| **Live network quota** | `VirtualNetworks` **0 / 1,000**; `NetworkSecurityGroups` **0 / 5,000**; the validation needs one of each | Owner-reported live `list-usages` after registration ([execution record](2026-11-20-provider-registration-execution.md), SHA-256 `f1ffc2b39d2e5c61e4895825f0f0292809f926db242f44d27bc4c0f449b309d2`) |
| Resource groups | 1 in subscription; the validation adds one | Owner-reported count; documented limit 980 |

## Approval — `region_capacity` (criterion met)

The owner approves region and capacity for the seven-resource validation in `uksouth` on the
evidence above. The recorded completion criterion, live VNet and NSG headroom, is met.

## Not covered and not marked satisfied

- **Key Vault, Log Analytics workspace and user-assigned identity quotas** weren't live-checked.
  No documented regional limit for them was found, and they weren't part of the recorded
  criterion. This is a residual risk: ARM validation and what-if (stage 6) would surface a quota
  or capacity refusal before any provisioning.
- **Capacity at deployment time** isn't guaranteed by a quota reading.
- **Provider-registration execution item 5** (no resource group or resource created;
  `NetworkWatcherRG` still absent) and the before/after timestamps **weren't reported**. They
  remain open in the execution record and don't affect this approval's criterion.

Stage 1 is complete with this approval. `budget`, `execution_template`, `cloud_validation`,
`provisioning`, `teardown` and `evidence` remain pending. All `approved_values` and `execution`
fields remain `null`. Neither Bicep deployment gate changes. M22 restrictions, M23 SECURITY GATE
NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
