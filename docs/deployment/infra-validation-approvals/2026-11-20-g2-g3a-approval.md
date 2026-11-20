# Infrastructure validation approval record — stage 5 conditions G2 (approved values) and G3-A

**Recorded:** 2026-11-20T08:19:57Z · **Approver:** repository-owner · **Baseline:** `88b09e4`

This record is the owner's approval of decisions D1–D5 of the G2/G3-A decision package. It
approves the immutable [proposal](2026-11-20-g2-approved-values-proposal.md), SHA-256
`e05e9d2d3f54e291c3a0337041db9243083db91e7f55a4eafd7cfbc6f4e9fbd6` (unchanged), as stated below.
It resolves conditions **G2** and **G3** of the
[stage 5 execution-template approval](2026-11-20-execution-template.md) (SHA-256
`1d69d8bbdc82551a3fcad00f7bd6d277e08b26c4cd26a5c85dd292d0650bf8ba`, unchanged).

It populates only the six G2 `approved_values` in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json). No
approval entry or `execution` field changes. The contract stays `PREPARATION_ONLY` with
`provisioning_allowed=false`. This record is immutable; any change needs a new dated record.
**No Azure action is authorised by this record.**

## D1–D3: approved values (G2)

| `approved_values` key | Approved value | Proposal basis |
| --- | --- | --- |
| `location` | `uksouth` | Scope approval |
| `resource_group` | `rg-claims-infraval-uks-tmp01` | Scope approval; not the protected `rg-claims-agentic-ai-dev` |
| `include_container_environment` | `false` | Scope approval; the validator requires `false` |
| `log_daily_quota_gb` | `1` | Cost-exposure record |
| `subscription_id` | `sha256:8bcf62e8790b8d138f042ec3628acb09a90b4d684b296bcac1c57be18f8bc686` | Commitment computed by the owner (below) |
| `expires_at` | `2026-11-25T16:00:00Z` | `T0` + 3 h: hard deadline for teardown, including the Key Vault purge |

**Subscription commitment.** The owner computed it in Azure Cloud Shell with
`infra_subscription_preflight.py commit` from `88b09e4` (module SHA-256
`858b102e08fc2634ab74537c4c595fa582b5b641b3b423f22b5799b9daec4287`). It's
`sha256("infraval-subscription-v1:" + lower-case subscription GUID)`. The raw subscription ID
isn't recorded anywhere in the repository. The commitment's binding to the live subscription is
the preflight `check`, which every Cloud Shell session must pass before any other Azure command.

## D4: execution plan (for the stage 6 and stage 7 approvals)

| Item | Approved plan |
| --- | --- |
| `T0` (`window_start_utc`) | `2026-11-25T13:00:00Z` |
| `window_end_utc` | `2026-11-25T15:00:00Z` (2 h, the validator's maximum; 1 h before `expires_at`) |
| `run_id` | `infraval-20261125-01` (also the resource group's `infravalRun` tag) |

These aren't written to the contract. The `execution` block stays all `null` until the stage 6
and stage 7 approvals bind them. The window is in November 2026 UTC, as the resource-group
budget's `2026-11-01` start date requires (G4). Run the stage 6 what-if on 2026-11-25, before
`T0`. Moving `T0` or `expires_at` needs a new dated record.

## D5: G3-A accepted

The resource-group budget's `budgetEndDate` (`2026-12-31`) is later than `expires_at`. That's
accepted as a **documented exception**, with no template or budget change:

- the resource-group budget **must be removed during teardown**;
- the subscription budget `infraval-uks-tmp01-budget` (2 GBP,
  [execution record](2026-11-20-subscription-budget-execution.md)) **stays** for the +24 h and
  +72 h post-teardown cost checks. Deleting it before its 2026-12-31 expiry needs a separate
  owner approval.

## Not approved by this record

- **G9:** resource-group creation and empty-group cleanup. These stay proposed for the separate
  stage 6 approval.
- **Stage 6 `cloud_validation`**, `provisioning`, `teardown`, `evidence`; any `execution` field;
  any contract status change; any Azure call.
- G4–G8 stay as recorded in the stage 5 approval.

Neither repository Bicep gate changes (both stay `@allowed([false])`). M22 restrictions, M23
SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
