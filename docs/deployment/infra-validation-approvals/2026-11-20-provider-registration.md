# Infrastructure validation approval record — Microsoft.Network provider registration

**Recorded:** 2026-11-20T00:31:39Z · **Approver:** repository-owner · **Baseline:** `6e1dd68`

This record is the evidence for the `provider_registration` approval in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) (checklist
stage 3). It's an immutable record: any change needs a new dated record. The contract stays
`PREPARATION_ONLY` with `provisioning_allowed=false`.

## Approval — `provider_registration`

The owner explicitly approves registering the **`Microsoft.Network`** resource provider in the
**`OctoCAT-Agentic-AI`** subscription.

- **Purpose:** to make live virtual network and network security group quota checks possible
  (`az network list-usages --location uksouth`), so `region_capacity` (stage 1) can be evidenced.
  Before registration the quota API returned `SubscriptionHasNoUsages`.
- **Who and how:** the owner, personally, in Azure Cloud Shell with existing interactive
  authentication (per the `identity_rbac` approval), using exactly:
  `az provider register --namespace Microsoft.Network --wait`.
- **Scope:** this one namespace only. The other six required namespaces were already reported as
  Registered. No other provider, feature or preview registration is approved. In particular,
  the `DisableNetworkWatcherAutocreation` feature isn't registered (Network Watcher Option A).
- **Effect:** registration is a free, subscription-level enablement. It creates no resources,
  incurs no charge by itself and grants **no deployment**. It persists after teardown and isn't
  reversed by it.

## Evidence to capture when the owner performs it

1. Before: `az provider show -n Microsoft.Network --query registrationState -o tsv` (expected
   `NotRegistered`), with a UTC timestamp.
2. The registration command's exit status.
3. After: the same query (expected `Registered`), with a UTC timestamp.
4. The live quota check for `region_capacity`:
   `az network list-usages --location uksouth --query "[?name.value=='VirtualNetworks' || name.value=='NetworkSecurityGroups'].{name:name.value,used:currentValue,limit:limit}" -o table`.
5. Confirmation that no resource group or resource was created (`az group list --query "length(@)"`
   unchanged; `NetworkWatcherRG` still absent).

**Stop conditions:**
- registration fails or doesn't reach `Registered`;
- any prompt asks to register another namespace or feature;
- any resource or resource group appears as a result;
- a policy or lock blocks the operation.

## Not approved by this record

`region_capacity` **remains PENDING** until live VNet and NSG quota from step 4 is recorded and
reviewed. `budget`, `execution_template`, `cloud_validation`, `provisioning`, `teardown` and
`evidence` remain pending. All `approved_values` and `execution` fields remain `null`. Neither
Bicep deployment gate changes. Approving stage 3 before stage 1 is complete doesn't relax any
check: validation still requires stages 1–6, and provisioning stages 1–8. M22 restrictions, M23
SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
