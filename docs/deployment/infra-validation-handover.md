# Infrastructure validation — context handover (2026-11-20)

A snapshot for resuming the Option C infrastructure validation in a fresh session. Authority stays
with [`infra/azure-validation/contract.json`](../../infra/azure-validation/contract.json) and the
dated records in [`infra-validation-approvals/`](infra-validation-approvals/); this note grants
nothing. Full procedure: [infrastructure-validation.md](infrastructure-validation.md).

## Repository state

- **Last commit:** `0d9f3ff` (`main`).
- **Uncommitted, awaiting the owner** (prepared, not approved):
  - `deployment/infra_stage7_deploy.sh`, `deployment/infra_stage8_teardown.sh`,
    `deployment/infra_stage8_cost_check.sh`, `deployment/infra_evidence.py` (new)
  - `tests/test_infra_stage7_stage8_procedures.py` (new)
  - `docs/deployment/infrastructure-validation.md` and this handover
- **Drafted, not recorded:** the stage 6 `cloud_validation` approval (scratchpad only). Stage 6
  artifacts are in git-ignored `outputs/deployment/infra-validation-execution/`.
- Validation at last run: full suite 2030 passed; Ruff, strict mypy and `git diff --check`
  clean; contract validation PASS; `--check-provisioning` and `--authorize-validation` refused
  (exit 78).
- Contract: **`PREPARATION_ONLY`**, `provisioning_allowed=false`; all `approved_values` set;
  `execution` block all `null`.
  Both Bicep gates are `@allowed([false])` (`infra/azure-validation/main.bicep`
  `provisioningApproved`, `infra/azure/main.bicep` `deploymentEnabled`).

## Approvals (contract) and immutable evidence

| Stage | Approval | Status | Evidence (SHA-256 prefix) |
| --- | --- | --- | --- |
| 1 | `scope` | APPROVED (amended: + one subscription budget) | `32218157` amendment; original `ccfa1bab` preserved |
| 1 | `network`, `region_capacity`, `identity_rbac` | APPROVED | `b77a417f`, `0bbf4246`, `66eaf996` |
| 2 | `cost_exposure` | APPROVED | `ccfa1bab` |
| 3 | `provider_registration` | APPROVED, performed (`Microsoft.Network` only) | `6ac6063f`; execution `f1ffc2b3`, supplement `d4fcc724` |
| 4 | `budget` | APPROVED (values); subscription budget **created** | `55641a5f`; execution `ec041f24` |
| 5 | `execution_template` | APPROVED, conditions G1–G8 | `1d69d8bb`; G1 verification `df2d7079` |
| 6–9 | `cloud_validation`, `provisioning`, `teardown`, `evidence` | **PENDING** | — |

Records are immutable: never edit a hashed or cited record; add a new dated record or supplement.

Stage 5 binds Bicep CLI 0.48.1 (`62cd5958…`), reviewed source `4beed4f7…`, reviewed compiled
`28c29de5…` and execution compiled `dfc26600…` (one-line gate change, git-ignored, never
committed).

## Open conditions and owner decisions

- **G1:** resolved for the five named providers. `Microsoft.Network` was confirmed earlier;
  `Microsoft.Consumption`'s registration state is **unverified** (only the budget operation
  succeeded).
- **G2: approved** 2026-11-20 ([record](infra-validation-approvals/2026-11-20-g2-g3a-approval.md),
  `bcb8f790…`, citing proposal `e05e9d2d…`): `location=uksouth`,
  `resource_group=rg-claims-infraval-uks-tmp01`, `include_container_environment=false`,
  `log_daily_quota_gb=1`, `subscription_id=sha256:8bcf62e8…f8bc686`,
  `expires_at=2026-11-25T16:00:00Z`. Plan (not in the contract yet): `T0`
  2026-11-25T13:00:00Z, window end 15:00:00Z, `run_id` `infraval-20261125-01`.
- **G3-A: accepted** (same record). The resource-group budget is removed at teardown; the
  subscription budget stays for the +24 h/+72 h cost checks.
- **G9:** resource-group creation (tagged, empty, absence proven first, post-state asserted) and
  empty-group cleanup (refuses unless the group is idle and empty). **Needs the separate stage 6
  `cloud_validation` approval.** Commands are in the G2 proposal.
- **G4–G8:** open as recorded in the stage 5 record: November timing; what-if may report
  `Unsupported`; the `PREPARATION_ONLY` tag label; the teardown state file must exclude the
  subscription budget; the scope-amendment wording.

## Subscription preflight and remaining gaps

`deployment/infra_subscription_preflight.py` (stdlib only, run in Cloud Shell; refusals exit 78;
the raw ID stays in memory and is never printed):
- `commit` prints only `sha256(` `infraval-subscription-v1:` + lower-case GUID `)`;
- `check` requires the commitment, the name `OctoCAT-Agentic-AI`, the `Enabled` state, and that
  the session's `$SUB` is that subscription;
- `lint` requires `--subscription "$SUB"` on every `az` command and rejects `az account set`,
  shell tracing and GUID literals.

Remaining gaps, to close before stage 6:
1. ~~Stage 6, 7 and 8 procedures~~ **Prepared, not approved** (stage 7/8 uncommitted):
   `infra_stage6_validate_whatif.sh`, `infra_stage7_deploy.sh`, `infra_stage8_teardown.sh` and
   `infra_stage8_cost_check.sh`, each running the preflight before any other Azure command.
2. ~~Lint ordering and strict mode~~ **Closed offline** (uncommitted): strict `lint` requires
   `set -euo pipefail`, the bootstrap and the exact preflight before every other `az` command,
   and fail-closed verification. `lint_commands` keeps the command-level rules only.
3. The validator never calls the preflight (the stage 6 procedure chains them).
4. Upload integrity: the stage 6 procedure checks `SHA256SUMS` for exactly six files, but the
   manifest itself still needs a manual comparison with the repository.
5. Azure error messages may show `/subscriptions/<id>` in the terminal; mask output before
   sharing. `validate.json` and `whatif.json` contain the raw ID.

## Proposed execution window (not approved)

| Item | Value |
| --- | --- |
| `T0` / `window_start_utc` | `2026-11-25T13:00:00Z` |
| `window_end_utc` | `2026-11-25T15:00:00Z` (2 h maximum) |
| `expires_at` | `2026-11-25T16:00:00Z` (teardown and Key Vault purge deadline) |
| `run_id` | `infraval-20261125-01` (also the group's `infravalRun` tag) |

The deployment must happen in November 2026 UTC for the resource-group budget's start date. Run
the stage 6 what-if on 2026-11-25. Moving `T0` needs a new dated record.

## Current Azure state (owner-reported)

- Subscription `OctoCAT-Agentic-AI`, owner holds direct Owner. Registered: `Microsoft.Network`
  plus the five G1 providers; `Microsoft.Consumption` is unverified.
- **Only Azure object created by this work:** subscription budget `infraval-uks-tmp01-budget`
  (2 GBP, Monthly, 2026-11-01 to 2026-12-31, `ResourceGroupName` filter
  `rg-claims-infraval-uks-tmp01`, Actual 50/80/100%). Billing currency is **GBP**. It's retained
  until it expires; deleting it early needs separate approval.
- The validation resource group **doesn't exist**. No in-group resources have been deployed.
  `NetworkWatcherRG` was absent at the last check.

## Exact next safe task

Wait for the owner to commit the G2/G3-A files. Then, only on the owner's instruction, prepare
stage 6 offline: rebuild the execution copy (compiled hash must equal `dfc26600…`), generate the
approved `parameters.json` and the `SHA256SUMS` manifest, and draft the stage 6
`cloud_validation` approval (G9 creation, the stage 6 script, the `execution` block, status
`APPROVED_FOR_VALIDATION`) for the owner's decision.

## Prohibitions (standing)

- **No Azure writes or calls** by the assistant. The owner runs approved commands in Cloud
  Shell. No resource-group creation, deployment, what-if, teardown, purge or budget change
  without the specific approval.
- **No approval changes** without an explicit owner instruction. Never edit a hashed or cited
  record.
- **Don't change** the contract status, `provisioning_allowed`, the `execution` block, the
  templates or either Bicep gate (both stay `@allowed([false])`).
- **No `git add`, commit, push or history rewrite.** The owner does all Git writes. Terminal
  blocks for the owner start with
  `cd /Users/privilege/Desktop/GitHub_repository/enterprise-azure-agentic-ai-claims-processing`.
- **No downloads, installs, container builds or trust-store changes.** M22 restrictions, M23
  SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are
  unchanged.
- Keep personal email addresses and raw subscription IDs out of new files; the approver identity
  is `repository-owner`.
