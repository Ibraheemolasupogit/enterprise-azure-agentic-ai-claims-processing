# Infrastructure validation approval record — Stage 1 findings and network

**Recorded:** 2026-11-20T00:20:17Z · **Approver:** repository-owner · **Baseline:** `f2370f1`

This record is the evidence for the `network` approval in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) (checklist
stage 1). It also records Stage 1 findings that **don't yet** satisfy `region_capacity` or
`identity_rbac`. It's an immutable record: any change needs a new dated record. The contract
stays `PREPARATION_ONLY` with `provisioning_allowed=false`, and **no Azure action is authorised
by this record**.

## Read-only Cloud Shell findings (owner-reported, 2026-11-20)

The owner ran the read-only Stage 1 query block in Azure Cloud Shell and reported these results.
Raw command output isn't retained in the repository, so they're **owner-reported**, not
independently reproduced.

| Check | Reported result |
| --- | --- |
| Subscription `OctoCAT-Agentic-AI` | Enabled |
| `Microsoft.Network` registration | NotRegistered |
| UK South support for the five regional types (VNet, NSG, user-assigned identity, Key Vault, Log Analytics workspace) | All supported |
| Resource groups in subscription | 1 |
| Existing virtual networks | 0 |
| Network quota API (`az network list-usages`, `uksouth`) | `SubscriptionHasNoUsages` |
| Signed-in principal | User principal holding Owner |
| Policy assignments, including inherited (`--disable-scope-strict-match`) | Empty |
| Resource locks | Empty |
| Temporary group `rg-claims-infraval-uks-tmp01` | Absent |
| `NetworkWatcherRG` | Absent |
| Network Watcher instances | None |

## Network Watcher — Option A (owner-approved)

Microsoft Learn states that creating a virtual network automatically enables Network Watcher in
that region, placing the instance in a resource group named `NetworkWatcherRG`, and that this
"doesn't affect your resources or associated charge". Under Option A:

- **Permitted:** automatic creation of `NetworkWatcherRG` and `NetworkWatcher_uksouth` is a
  known side effect of creating the validation VNet. It's outside the seven approved resources
  and outside `rg-claims-infraval-uks-tmp01`.
- **Before/after evidence:** before-state = both absent (above). After deployment and again
  after teardown, record whether `NetworkWatcherRG` and `NetworkWatcher_uksouth` exist, with
  timestamps.
- **No automatic deletion:** teardown never deletes `NetworkWatcherRG` or the watcher. Removing
  them would need a separate owner decision.
- **No paid features:** no flow logs, traffic analytics, connection monitor, packet capture or
  other billable Network Watcher capability is enabled.
- **No opt-out:** the subscription-wide `DisableNetworkWatcherAutocreation` feature isn't
  registered.

## Approval — `network` (requirements met)

The owner approves the validation network plan:

- one new isolated virtual network `10.71.0.0/16` with a single `/23` subnet delegated to
  `Microsoft.App/environments`; no peering, gateway, public IP, ingress or private endpoint;
- the NSG denies inbound Internet traffic and Internet egress and has no inbound allow rules
  (checked offline against the compiled template);
- no existing VNets, so there's no address-space conflict;
- no policy assignments or locks reported that would restrict deployment or block teardown;
- the dedicated resource group doesn't exist yet;
- Network Watcher handled under Option A above.

`Microsoft.Network` registration is **not** part of this approval. It's checklist stage 3
(`provider_registration`) and still pending.

## Not met — remains PENDING

- **`region_capacity`.** UK South support and the resource-group count are established, but
  **live network quota isn't**. The quota API returned `SubscriptionHasNoUsages` because
  `Microsoft.Network` is unregistered. Following the owner's instruction, default limits aren't
  treated as live quota availability. It can be completed after stage 3 registration, by
  re-running `az network list-usages --location uksouth` and confirming VNet and NSG headroom.
- **`identity_rbac`.** A User principal holding Owner is reported. Still missing: the
  deny-assignment query result; whether Owner is a direct, active assignment rather than
  group-based or only PIM-eligible; and an explicit deployer decision (the owner deploys
  personally from Cloud Shell, with no service principal, federated credential or secret).
  Owner is broader than this validation needs; acknowledging that is part of the decision.

All `approved_values` and `execution` fields remain `null`. Neither Bicep deployment gate
changes. M22 restrictions, M23 SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25
OFFLINE COMPLETE are unchanged.
