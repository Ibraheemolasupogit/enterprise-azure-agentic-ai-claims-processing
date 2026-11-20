# Infrastructure validation approval record — execution template (stage 5)

**Recorded:** 2026-11-20T05:16:14Z · **Approver:** repository-owner · **Baseline:** `95c5fbf`

This record is the evidence for the `execution_template` approval in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) (checklist
stage 5). It approves **one exact execution copy** of the reviewed template, bound below by hash.
It's an immutable record: any change needs a new dated record.

It doesn't approve ARM validate, what-if, provisioning or teardown, and it doesn't set any
`execution` field. The contract stays `PREPARATION_ONLY` with `provisioning_allowed=false`.
The repository template `infra/azure-validation/main.bicep` stays `@allowed([false])`.
**No Azure action is authorised by this record.**

## Bound toolchain and reviewed artifacts

| Item | SHA-256 / value |
| --- | --- |
| Compiler | Bicep CLI **0.48.1** (`cec7951cf6`), binary `62cd5958c62fa1b738e9b69f24799fabddb90ed83fdb7d6d2563dde376ce479d` (git-ignored `artifacts/tools/bicep-0.48.1/bicep`) |
| Reviewed source | `infra/azure-validation/main.bicep` `4beed4f7290af307996059118d9100113711b47ab0d79cf2228e0a9cd808d82b` (last changed in `c2b7239`) |
| Reviewed compiled template | `28c29de5f4d0bc36529a5682246da5324cb9b2db8267583b8227254e55c41a17` |
| Execution source | `8715d9a0b0ce2c35ea271c828dd0cbd09fa58004fbd85463c54e121d1d3e1993` |
| Execution compiled template | `dfc26600fb9c8748fdf9fead8078bf281f4482ae27ed987c004adf33bb970989` |

Reproduced at recording: both compilations gave 0 diagnostics. The reviewed output equals the
recorded compile receipt's `main.json`. Rebuilding the execution copy gives the same hash.

## The execution copy

- It's a copy of the reviewed source with **exactly one line changed**: `@allowed([false])` →
  `@allowed([false, true])` on `provisioningApproved`. The default stays `false`.
- It lives only in git-ignored `outputs/deployment/infra-validation-execution/` and is **never
  committed**.
- The validator's binding checks pass on these exact files:
  - `validate_compiled_reviewed` on the reviewed template: the gate allows only `false`, it
    defaults to `false`, and all 8 resources are conditioned on it.
  - `gate_only_difference(reviewed, execution)` is true: the only difference is the gate's
    `allowedValues`.
- The deployed set, with the Container Apps environment off, is the approved seven: NSG, virtual
  network, user-assigned identity, Key Vault, Log Analytics workspace, `vault-audit` diagnostic
  setting and resource-group budget.
- The two compiled hashes become `reviewed_template_sha256` and `approved_template_sha256` only
  when the stage 6 approval moves the contract to `APPROVED_FOR_VALIDATION`.

Any other compiler, source edit or output hash invalidates this approval.

## Unresolved conditions (G1–G8)

These come from the stage 5 review. They're recorded here as conditions, not resolved by this
approval.

| # | Condition | Blocks |
| --- | --- | --- |
| G1 | **Provider registration.** ARM registers missing resource providers automatically when a template deploys. Stage 3 approved registering only `Microsoft.Network`. The states of `Microsoft.KeyVault`, `Microsoft.ManagedIdentity`, `Microsoft.OperationalInsights`, `Microsoft.Insights` and `Microsoft.App` aren't recorded. A read-only state check is required, and any `NotRegistered` provider needs explicit owner approval or acceptance | Stage 6 |
| G2 | **Six `approved_values` are `null`:** `location`, `resource_group`, `include_container_environment`, `log_daily_quota_gb`, `expires_at`, `subscription_id`. The validator refuses until all are recorded. Committing `subscription_id` would publish the subscription ID; that needs an owner decision | Stage 6 |
| G3 | The approved budget end date `2026-12-31` will be later than `expiresAt`, contrary to the `budgetEndDate` parameter description. The validator doesn't enforce the description, and the teardown plan deletes the resource-group budget. Proposed as a documented exception, with no template change; it still needs owner acceptance | Owner acceptance |
| G4 | `budgetStartDate` `2026-11-01` is valid only if the deployment runs in **November 2026 (UTC)**. Otherwise a new dated budget record must re-date it | Stage 7 timing |
| G5 | It isn't tested whether what-if reports the budget and diagnostic setting as `Create`. An `Unsupported` or other change type correctly stops the process for an owner decision | Stage 6 outcome |
| G6 | Deployed resources will carry the tag `deploymentStatus: PREPARATION_ONLY`. It's a fixed label, not a state. Changing it would change both bound hashes, so it's left unchanged | None (cosmetic) |
| G7 | The teardown state file's `budgets` list must contain only the resource-group budget. Listing the subscription budget makes the plan refuse (`budget_name`). The group must be created with the `purpose=infrastructure-validation` and `infravalRun=<run_id>` tags | Stages 7–8 procedure |
| G8 | Clarification of the [scope amendment](2026-11-20-scope-amendment-subscription-budget.md): its "never deletes it" refers to the **subscription budget**. The teardown plan does delete the dedicated resource group and the resource-group budget. That record is unchanged | None (clarified here) |

## Compatibility with the active subscription budget

The resource-group budget (`nsval-…-budget`) and the subscription budget
`infraval-uks-tmp01-budget` (2 GBP, filtered to the same group;
[execution record](2026-11-20-subscription-budget-execution.md)) are separate objects. Expect
duplicate alerts. The subscription budget stays after teardown for the +24 h/+72 h checks.

Realistic cost is about £0. The worst case, Log Analytics ingestion at the daily cap, could pass
2 GBP and trigger the 100% alert; budgets only notify, as accepted in the cost-exposure approval.

## Not approved by this record

`cloud_validation`, `provisioning`, `teardown`, `evidence`; any `approved_values` or `execution`
field; any provider registration; any Azure call. Neither repository Bicep gate changes. M22
restrictions, M23 SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE
COMPLETE are unchanged.
