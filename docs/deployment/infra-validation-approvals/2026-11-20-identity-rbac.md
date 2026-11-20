# Infrastructure validation approval record — identity and RBAC

**Recorded:** 2026-11-20T00:24:22Z · **Approver:** repository-owner · **Baseline:** `7ef8c11`

This record is the evidence for the `identity_rbac` approval in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) (checklist
stage 1). It's an immutable record: any change needs a new dated record. The contract stays
`PREPARATION_ONLY` with `provisioning_allowed=false`, and **no Azure action is authorised by this
record**.

## Read-only findings (owner-reported, 2026-11-20)

Raw command output isn't retained in the repository, so these are **owner-reported** results
from read-only Azure Cloud Shell queries.

| Check | Reported result |
| --- | --- |
| Subscription `OctoCAT-Agentic-AI` | Enabled |
| Signed-in principal | User |
| Role assignment | **Owner**, assigned **directly** to the user at **subscription scope** (an active assignment, as listed by `az role assignment list`) |
| Deny assignments at subscription scope | **0** |
| Policy assignments (including inherited) | None |
| Resource locks | None |

## Approval — `identity_rbac`

The owner approves this deployment identity for the infrastructure-only validation:

- **Deployer:** the owner, deploying **personally** through **Azure Cloud Shell** using their
  existing interactive authentication.
- **No service principal, no federated identity credential, no client secret, and no stored
  credentials** of any kind are created or used.
- **Least privilege acknowledged:** subscription Owner exceeds the minimum this validation needs
  (Contributor on the dedicated resource group, plus the subscription-level rights for provider
  registration and group creation). The owner accepts using it, limited to the commands in the
  approved execution and teardown procedures.
- The template's user-assigned managed identity receives **no role assignments**.
- Approval of this identity grants no deployment. Every later stage (provider registration,
  budget, execution template, ARM validation and what-if, provisioning, teardown, evidence) still
  needs its own approval.

## Still PENDING

- **`region_capacity`:** live network quota remains unverified. The quota API returned
  `SubscriptionHasNoUsages` while `Microsoft.Network` is unregistered, and default limits aren't
  treated as live quota.
- `provider_registration`, `budget`, `execution_template`, `cloud_validation`, `provisioning`,
  `teardown` and `evidence` remain pending. All `approved_values` and `execution` fields remain
  `null`. Neither Bicep deployment gate changes. M22 restrictions, M23 SECURITY GATE NO-GO, M24's
  six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
