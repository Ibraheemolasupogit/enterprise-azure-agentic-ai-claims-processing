# Azure infrastructure validation (Option C)

**Status: PREPARATION ONLY — NOT PROVISIONED.** Prepared 2026-11-19 at baseline `43cbf5b` under
the owner's approval to prepare an infrastructure-only validation. No Azure call, validation,
provisioning or spending has occurred, and none is authorised by this document.

This validation deploys **no claims application, container image, claims data, AI service,
public IP or public ingress**. It's separate from the M23 deployment foundation:
`infra/azure/main.bicep` and its false-only `deploymentEnabled` gate are unchanged. **M23 remains
DEFERRED — SECURITY GATE NO-GO**, M22's independent-review restrictions and M24's six
NOT_TESTED demonstrations are unchanged, and nothing here represents application, quality or
production readiness.

## Purpose

Prove, with real evidence, that a minimal landing zone can be validated, provisioned within an
approved budget and lifetime, monitored, and completely torn down. Specifically:

- the template validates and the what-if matches the approved resource list;
- the deployment identity is scoped to one resource group;
- tags, budget alerts and log caps work;
- teardown leaves no resources or charges.

## Artifacts

| File | Purpose |
| --- | --- |
| [`infra/azure-validation/main.bicep`](../../infra/azure-validation/main.bicep) | Minimal template with its own hard `@allowed([false])` provisioning gate |
| [`infra/azure-validation/contract.json`](../../infra/azure-validation/contract.json) | Contract v2: scope, resource allow-list, 12 approval records, the 9-stage checklist, approved values and the hash-bound `execution` block (all pending or null) |
| [`deployment/infra_validation.py`](../../deployment/infra_validation.py) | Offline validator: contract states, template and M23 gates, contract-bound authorisation, strict what-if check, teardown **planning** and purge-identity check. It never calls Azure, deploys or deletes |
| [`tests/test_infra_validation.py`](../../tests/test_infra_validation.py) | Positive checks and fail-closed mutations for every control |
| [`deployment/infra_subscription_preflight.py`](../../deployment/infra_subscription_preflight.py) | Cloud Shell subscription preflight (stdlib only): compares the live subscription with an approved `sha256:` commitment, the name `OctoCAT-Agentic-AI` and the `Enabled` state, and checks that the session's `$SUB` is that subscription. Never prints or stores the raw ID; refusals exit 78. `lint` requires strict mode, the preflight before every other `az` command, `--subscription "$SUB"` on every `az` command and fail-closed verification, and rejects `az account set`, shell tracing and GUID literals |
| [`tests/test_infra_subscription_preflight.py`](../../tests/test_infra_subscription_preflight.py) | Positive and negative preflight and lint tests; the proposal's G9 procedures must pass strict `lint` |
| [`deployment/infra_stage6_validate_whatif.sh`](../../deployment/infra_stage6_validate_whatif.sh) | Stage 6 ARM validate and what-if procedure (**prepared, not approved**); see [Stage 6 procedure](#stage-6-procedure-prepared-not-approved) |
| [`tests/test_infra_stage6_procedure.py`](../../tests/test_infra_stage6_procedure.py) | Runs the stage 6 procedure offline against a stub `az`: passes only on an approved synthetic contract and fails closed on every refusal path |

## Resources (all behind the hard gate)

| Resource | Secure configuration |
| --- | --- |
| Network security group | Deny inbound from the Internet; deny Internet egress; no inbound allow rules |
| Virtual network | One delegated subnet; no public IPs |
| User-assigned managed identity | No role assignments, federated credentials or secrets |
| Key Vault | RBAC only, no access policies, no secrets, public network access disabled, default-deny ACLs; purge protection **not** enabled and 7-day soft-delete so teardown completes |
| Log Analytics workspace | Approved daily cap, 30-day retention, local auth disabled, public ingestion and query disabled |
| Key Vault diagnostic setting | Audit logs to the workspace |
| Container Apps environment (**optional, off by default**) | Internal only, public access disabled, **no container apps or images** |
| Budget | Resource-group scope; notifications at 50/80/100% actual spend |

Excluded: API Management, container registry, PostgreSQL, Service Bus, storage, private
endpoints, container apps, Document Intelligence, AI Search, model services, role assignments.

**Outside the group (scope amendment):** one subscription-scope `Microsoft.Consumption/budgets`,
`infraval-uks-tmp01-budget`, filtered by `ResourceGroupName` to `rg-claims-infraval-uks-tmp01`. It
isn't deployed by the template, isn't in the what-if, and isn't touched by the teardown plan.
**It exists:** the owner created it on 2026-11-20 (2 GBP, monthly, 2026-11-01 to 2026-12-31;
[execution record](infra-validation-approvals/2026-11-20-subscription-budget-execution.md)). It's
kept for +24 h/+72 h post-teardown monitoring or until its expiry on 2026-12-31; deleting it
earlier needs a separate owner approval.

## Parameters requiring owner approval (no defaults)

`location` (`uksouth` or `westeurope`), `owner`, `expiresAt`, `budgetAmount`,
`budgetContactEmails`, `budgetStartDate`, `budgetEndDate` and `logDailyQuotaGb` (1–5). The
optional `includeContainerEnvironment` defaults to `false`. Enabling it needs an approved
review of the environment's platform egress, because the subnet denies Internet egress. The
contract proposes a **maximum 72-hour lifetime** as an upper bound; it isn't an approved value.

## Contract states (default deny)

| Status | Permits | Requires |
| --- | --- | --- |
| `PREPARATION_ONLY` (repository default) | Nothing; `execution` must be all null | — |
| `APPROVED_FOR_VALIDATION` | ARM validate and what-if **only**; provisioning stays refused | Stages 1–6 approved; artifacts bound by hash |
| `APPROVED_FOR_EXECUTION_WINDOW` | One provisioning window of **at most 2 hours**, ending no later than the approved expiry | Stages 1–8 approved; artifacts **and the passing what-if** bound by hash |

In **every** state, the repository template `infra/azure-validation/main.bicep` stays
false-only and `--check-provisioning` refuses it. Only an **execution copy** may open the gate.
That copy is compiled with the pinned Bicep 0.48.1 and bound by SHA-256, and it must differ from
the reviewed compiled template **only** in the gate's `allowedValues`. The M23 template
`infra/azure/main.bicep` is never changed.

## Approval checklist (9 stages, 12 contract approvals)

| Stage | Contract approvals | Evidence required |
| --- | --- | --- |
| 1 Scope, region, identity, network | `scope`, `region_capacity`, `identity_rbac`, `network` | Resource list; subscription and region; deployer identity matrix (group-scoped, no secrets); no ingress or public IPs |
| 2 Cost exposure | `cost_exposure` | Accepted exposure statement (realistic ≈ $0; stated worst case; budgets don't stop spend) |
| 3 Provider registration | `provider_registration` | Registration states before and after (`Microsoft.Network`) |
| 4 Budget values | `budget` | Amount, contacts, start/end dates, expiry |
| 5 Execution template | `execution_template` | Reviewed and execution compiled hashes; one-line gate diff |
| 6 ARM validate and what-if | `cloud_validation` | Retained `whatif.json` passing `--check-whatif` |
| 7 Provisioning window | `provisioning` | Window start and end (≤ 2 h), bound what-if hash |
| 8 Teardown | `teardown` | Approved teardown plan and identity checks |
| 9 Evidence record | `evidence` | Receipts filed; no gate or evidence changes |

Each approval record needs status, identity, time and an evidence SHA-256. Approval of one
stage never implies the next. Any change to resources, region, SKU, permissions, budget,
template, parameters or window invalidates the affected approvals.

### Recorded approvals

| Approval | Status | Evidence |
| --- | --- | --- |
| `scope` | **APPROVED**, amended 2026-11-20 (repository-owner): seven in-group resources (environment disabled, `OctoCAT-Agentic-AI`, `uksouth`, `rg-claims-infraval-uks-tmp01`, 2-hour window) **plus one subscription-scope budget** `infraval-uks-tmp01-budget` filtered by `ResourceGroupName` to that group; creation and deletion need separate approval | [Amendment](infra-validation-approvals/2026-11-20-scope-amendment-subscription-budget.md), SHA-256 `32218157…ea2133ad`; original [record](infra-validation-approvals/2026-11-20-scope-and-cost-exposure.md) `ccfa1bab…56cd4f` preserved |
| `cost_exposure` | **APPROVED** 2026-11-20 (repository-owner): exposure acknowledged; $2 budget alerts aren't hard caps | Same record |
| `network` | **APPROVED** 2026-11-20 (repository-owner): isolated VNet plan, no policies or locks reported, no existing VNets, Network Watcher **Option A** | [Record](infra-validation-approvals/2026-11-20-stage1-findings-and-network.md), SHA-256 `b77a417f…cbc3da44` |
| `region_capacity` | **APPROVED** 2026-11-20 (repository-owner): live UK South quota VNets 0/1,000, NSGs 0/5,000; five types supported. Key Vault, Log Analytics and identity quotas not live-checked (residual) | [Record](infra-validation-approvals/2026-11-20-region-capacity.md), SHA-256 `0bbf4246…0eadbe5d` |
| `identity_rbac` | **APPROVED** 2026-11-20 (repository-owner): direct Owner (User, subscription scope), 0 deny assignments, owner deploys personally via Cloud Shell, no service principal, federated identity or secrets; least privilege acknowledged | [Record](infra-validation-approvals/2026-11-20-identity-rbac.md), SHA-256 `66eaf996…d5ab27e4` |
| `provider_registration` | **APPROVED** 2026-11-20 (repository-owner): register `Microsoft.Network` only, by the owner in Cloud Shell, to enable live quota checks. **Performed 2026-11-20** (`NotRegistered` → `Registered`); [execution record](infra-validation-approvals/2026-11-20-provider-registration-execution.md); [supplement](infra-validation-approvals/2026-11-20-provider-registration-execution-supplement.md) (SHA-256 `d4fcc724…275a5fe8`): resource-group count unchanged at 1, `NetworkWatcherRG` and the validation group absent (group-level observation, not a full inventory) | [Record](infra-validation-approvals/2026-11-20-provider-registration.md), SHA-256 `6ac6063f…580cf132` |
| `budget` | **APPROVED** 2026-11-20 (repository-owner): amount 2 (subscription billing currency; **GBP**, established at creation), public contact `ibraheemolasupo@yahoo.com`, `Actual` alerts at 50/80/100% (`GreaterThanOrEqualTo`), monthly 2026-11-01 to 2026-12-31, no action group, `owner=repository-owner`; applies to the template budget and `infraval-uks-tmp01-budget`; stop if the post-creation currency is unexpected; creation and deletion need separate approval. **Subscription budget created 2026-11-20** (PUT 02:18:10Z, GET check passed 02:18:13Z; 2 GBP, current spend 0.00 GBP) after two runs stopped before any write on an absence-check parser defect; [execution record](infra-validation-approvals/2026-11-20-subscription-budget-execution.md), SHA-256 `ec041f24…20c57aa5`. The template's resource-group budget isn't deployed | [Record](infra-validation-approvals/2026-11-20-budget.md), SHA-256 `55641a5f…7bd5d410` |
| `execution_template` | **APPROVED** 2026-11-20 (repository-owner): one exact execution copy, bound to Bicep 0.48.1 (`62cd5958…`), reviewed source `4beed4f7…08d82b`, reviewed compiled `28c29de5…c41a17` and execution compiled `dfc26600…bb970989` (one-line gate change, never committed). Not yet written to the `execution` block. **G1 resolved** 2026-11-20: the five named providers confirmed `Registered` by owner query; `Microsoft.Network` confirmed earlier; `Microsoft.Consumption` state unverified (budget operation succeeded) ([verification record](infra-validation-approvals/2026-11-20-g1-provider-states.md), SHA-256 `df2d7079…b9bf4775`). **G2 and G3-A approved** 2026-11-20 (repository-owner; [G2/G3-A approval](infra-validation-approvals/2026-11-20-g2-g3a-approval.md), SHA-256 `bcb8f790…2933ecf2`, citing the [proposal](infra-validation-approvals/2026-11-20-g2-approved-values-proposal.md) `e05e9d2d…f4e9fbd6`): the six G2 `approved_values` set, including the subscription commitment; plan `T0` 2026-11-25T13:00:00Z, window end 15:00:00Z, `run_id` `infraval-20261125-01` (not yet in the `execution` block); resource-group budget end date accepted as an exception and removed at teardown. **G9 not approved** (stage 6); G4–G8 open | [Record](infra-validation-approvals/2026-11-20-execution-template.md), SHA-256 `1d69d8bb…650bf8ba` |
| All other approvals | PENDING | — |

The contract remains **`PREPARATION_ONLY`** with `provisioning_allowed=false`. The stage 4 budget
values, `owner` and the six G2 values are set in `approved_values`; all `execution` fields
remain `null`. **Stage 1 is complete.** Stage 4 budget values are approved and the subscription budget exists (GBP). Stage 5 `execution_template` is approved; G1, G2 and G3 are resolved and G4–G8 remain open. Stage 6 needs its own `cloud_validation` approval (including G9). Stages 6–9 remain pending.

## Offline commands

```sh
python3 -I -B deployment/infra_validation.py --root .                       # PASS; repository gate FALSE_ONLY
python3 -I -B deployment/infra_validation.py --root . --check-provisioning  # always refused (exit 78)
# With an approved contract copy and the exact artifacts (refusal = exit 78):
python3 -I -B deployment/infra_validation.py --contract C --authorize-validation \
  --reviewed-template REVIEWED.json --execution-template EXEC.json --parameters PARAMS.json
python3 -I -B deployment/infra_validation.py --contract C --check-whatif whatif.json
python3 -I -B deployment/infra_validation.py --contract C --authorize-execution \
  --reviewed-template REVIEWED.json --execution-template EXEC.json --parameters PARAMS.json --whatif whatif.json
python3 -I -B deployment/infra_validation.py --contract C --plan-teardown state.json
python3 -I -B deployment/infra_validation.py --contract C --verify-purge VAULT DELETED_VAULT_ID
```

Every fail-closed decision runs **locally** on files exported from Cloud Shell. Cloud Shell
only runs the owner-approved commands.

## Stage 6 procedure (prepared, not approved)

[`deployment/infra_stage6_validate_whatif.sh`](../../deployment/infra_stage6_validate_whatif.sh)
is the owner's Cloud Shell procedure for stage 6. **It isn't approved and mustn't run** before
the stage 6 `cloud_validation` approval and the G9 group creation (G2 and G3-A are approved).
Any failed step stops it with a non-zero exit; there's no retry, create, delete or `--no-wait`.

1. **Upload integrity (offline):** `SHA256SUMS` must list exactly `contract.json`,
   `execution.json`, `infra_subscription_preflight.py`, `infra_validation.py`,
   `parameters.json` and `reviewed.json`, and every hash must match.
2. **Offline authorisation:** `--authorize-validation` must return
   `AUTHORIZED_FOR_VALIDATION_ONLY` / `NOT_AUTHORIZED`. The resource group, run ID, location and
   expiry come from the contract, and the approved expiry must still be in the future. The
   repository contract (`PREPARATION_ONLY`) refuses here, before any Azure command.
3. **Subscription identity:** the bootstrap, then the preflight `check`, before every other
   Azure command.
4. **Group state (read-only):** the group exists, `Succeeded`, in the approved location, with
   exactly the three G9 tags, and has no resources, locks or deployments.
5. **ARM validate, then what-if** of the bound execution template and parameters.
6. **Offline `--check-whatif`** (exactly the seven `Create`s), then proof that the group is
   still empty and no deployment is in progress.
7. Prints only the SHA-256 of `whatif.json` and `validate.json`. Both files hold the raw
   subscription ID; they stay in Cloud Shell and are never committed or shared unmasked.

**Procedure lint.** `infra_subscription_preflight.py lint` refuses a procedure unless:
- its first statement is exactly `set -euo pipefail`, and nothing relaxes it (`set +e`,
  `set +o pipefail`, `set +u`);
- `$SUB` is assigned once, by `SUB=$(az account show --query id -o tsv)`, and never
  reassigned, exported, read or unset;
- the exact preflight `check --contract contract.json` runs after the bootstrap and before
  every other `az` command (an unknown verb counts as a write: `write_before_preflight`);
- every `az` command carries exactly `--subscription "$SUB"`, with no `--no-wait`;
- no `az`, `test`, `python3` or `sha256sum` statement is a condition (`if`, `while`, `until`,
  `!`) or part of an `&&`/`||` list, and no test can pass on empty output (`test !`,
  `test -z`, `test -n`, `!=`, `= ""`);
- no `local`/`export`/`declare` masks a failing command substitution.

Quoted JMESPath and Python text is masked first, so its `&&`, `!=` and `==` don't count. The
one-off read-only `commit` snippet can't run `check` (no commitment is approved yet), so only
the command-level rules (`lint_commands`) apply to it. Both G9 blocks pass the strict rules.

Not tested against real Azure: the `az deployment group validate`/`what-if` flags and output
shapes are exercised only through a stub. An unexpected flag or shape fails closed.

## What-if check

The what-if must contain **exactly one `Create`** for each of the seven deployed types (NSG,
virtual network, managed identity, Key Vault, Log Analytics workspace, diagnostic setting,
budget). Everything must be in the approved resource group with the `nsval-` naming, and the
diagnostic setting must be `vault-audit` on the vault. Types are parsed in full, including child
and extension segments: a vault secret is `microsoft.keyvault/vaults/secrets`, not a vault. Any
other type or change type, including `Unsupported`, any duplicate or any missing type stops the
process for an owner decision.

## Fail-closed teardown (plan only; owner executes after the teardown approval)

`--plan-teardown` reads an owner-exported state file. That file holds the group (name, tags,
locks), its resources (IDs, tags), the deployment's output resource IDs (or `null` if missing),
the deployment state and the budget names. It returns an ordered plan or **refuses for manual
review**:

- **Group identity:** refuses unless the name equals the approved group, is never
  `rg-claims-agentic-ai-dev`, and carries `purpose=infrastructure-validation` **and**
  `infravalRun=<run_id>`. The group must not have existed before; it's created with both tags.
  Any lock refuses.
- **Running deployment:** `Running`/`Accepted` gives only *cancel the deployment, then re-plan*.
- **Partial failure or missing outputs:** works from the actual inventory. Only resources that
  exist are acted on; an absent group is verify-only.
- **Unexpected state:** refuses on any unexpected type, untagged resource, resource missing from
  the deployment record, or more than one candidate per type or budget.
- **Order:** capture evidence → delete budget → permanently delete the workspace (`--force`) →
  delete the group (waits for completion) → `--verify-purge` against
  `az keyvault show-deleted --name <vault> --query properties.vaultId` → purge the vault → verify.

Verification after teardown:
- group absent;
- no soft-deleted workspace or vault;
- every recorded ID returns not-found;
- no resources carry the validation tag;
- no role assignments at the group's scope;
- Network Watcher (Option A): record whether `NetworkWatcherRG` and `NetworkWatcher_uksouth`
  exist after deployment and after teardown. They're **never deleted** by teardown, and no paid
  Network Watcher feature is enabled;
- a cost check at **+72 h** (pay-as-you-go cost data can take up to 72 hours).
- the subscription-scope budget stays in place for the +24 h/+72 h checks; it's deleted only
  under its separate approval, or auto-deleted at its approved expiry.

## Stop conditions

Stop and tear down, or don't start, if any of these occur:

- the what-if lists anything outside the allow-list, a public IP, ingress or an excluded SKU;
- any approved value is missing, or there's no dated quote (deny when the budget is missing);
- spend reaches the approved stop threshold, or the expiry passes;
- the deployer needs permissions beyond the resource group, or any client secret;
- any step needs a container image, application code, claims data, AI services or a change to
  `infra/azure/main.bicep`;
- resources or charges remain after teardown;
- the what-if check, an authorisation check or a teardown plan refuses;
- the purge target's original ID isn't exactly in the approved group;
- any step would deploy the repository template or treat a contract file as authority by itself;
- anything would imply application, quality or production readiness.

## Limitations

- **Local compilation passes; Azure-side checks are NOT_TESTED.** On 2026-11-19 the template
  compiled with **zero diagnostics** using the pinned Bicep CLI **0.48.1 (`cec7951cf6`)**,
  SHA-256 `62cd5958c62fa1b738e9b69f24799fabddb90ed83fdb7d6d2563dde376ce479d`. That's the
  official `bicep-osx-arm64` release asset, whose release digest matches the M23 Stage A pin,
  signed by Apple Team ID `UBF8T346G9` and kept in git-ignored `artifacts/tools/`. As a
  control, all 12 M23 compilations reproduced their recorded outputs byte for byte. The
  compiled ARM template keeps `provisioningApproved` restricted to `false`, with every
  resource conditioned on it. Local compilation checks the compiler's type and schema model
  only; ARM validation and what-if (provider acceptance, quota, policy) remain approval 7.
- **The budget API version (`Microsoft.Consumption/budgets@2021-10-01`) is new to this
  repository.** The other API versions reuse the reviewed M23 modules.
- **Workspace query access is disabled** (no private link scope), so logs can't be queried
  from outside Azure's private network. Enabling query access is a separate approval.
- **Budgets only notify.** Stopping spend relies on the operator and the teardown procedure.
