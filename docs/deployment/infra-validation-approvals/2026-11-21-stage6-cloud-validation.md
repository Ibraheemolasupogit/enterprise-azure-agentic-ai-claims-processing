# Infrastructure validation approval record — stage 6 `cloud_validation`

**Recorded:** `2026-11-21T00:48:17Z` ·
**Approver:** repository-owner · **Baseline:** `7bb5399`

This record is the evidence for the `cloud_validation` approval in
`infra/azure-validation/contract.json` (checklist stage 6). It approves **ARM validate and what-if
only**, plus the G9 resource-group creation and empty-group cleanup that they need. It is immutable
once recorded; any change needs a new dated record.

## 1. Bound artifacts

| Artifact | SHA-256 | Source |
| --- | --- | --- |
| Stage 6 procedure `deployment/infra_stage6_validate_whatif.sh` | `7e3bc971d6687562596476c7e8804f525aae253e587f2cb5827038a154a2425b` | Commit `88b09e4`; strict lint PASS |
| Reviewed compiled template (`reviewed.json`) | `28c29de5f4d0bc36529a5682246da5324cb9b2db8267583b8227254e55c41a17` | Stage 5 record `1d69d8bb…`; recompiled 2026-11-20, identical |
| Execution compiled template (`execution.json`) | `dfc26600fb9c8748fdf9fead8078bf281f4482ae27ed987c004adf33bb970989` | Stage 5 record; rebuilt with Bicep 0.48.1 (`62cd5958…`) from execution source `8715d9a0…` (one-line gate diff), identical |
| Parameters (`parameters.json`) | `d668581c7e7c0b9a025ebedc9c124058be6ea371ff649084f9dd9c3ed6208b7c` | Generated from the G2/G3-A approved values (record `bcb8f790…`) + `provisioningApproved=true` |
| Preflight module | `858b102e08fc2634ab74537c4c595fa582b5b641b3b423f22b5799b9daec4287` | Commit `88b09e4` (unchanged at `0d9f3ff`) |
| Validator `deployment/infra_validation.py` | `3b971f1f5355efaa0a1824f2fb7d39e83dc336bfc9c0d13a653f387f17b1b2fb` | Unchanged at `0d9f3ff` |
| G9 creation block (proposal block 2) | `67d411034d9dbf73a3e101f0bc4be8e37611aa0a4037fdfd3bdf3dfd9902aa71` | Proposal `e05e9d2d…`, immutable |
| G9 empty-group cleanup block (proposal block 3) | `5ff114baa9ffefb28d406a75b4adfab8027de8ffb864737df4711c15a6e767be` | Proposal `e05e9d2d…`, immutable |
| Optional read-only provider check (section 6) | `aee19829adc357c1fcdd4253006e09c26023e5cf6d2dc9098fae4cd07d245254` | This record; strict lint PASS |

Prior records incorporated by reference (unchanged):

- Stage 5 execution-template approval: `docs/deployment/infra-validation-approvals/2026-11-20-execution-template.md`,
  SHA-256 `1d69d8bbdc82551a3fcad00f7bd6d277e08b26c4cd26a5c85dd292d0650bf8ba`.
- G2/G3-A approval: `docs/deployment/infra-validation-approvals/2026-11-20-g2-g3a-approval.md`,
  SHA-256 `bcb8f7909c08b9612421fc96dbeaa81dc229220cee7c80c138c3a7192933ecf2`.
- G9 proposal containing the bound command blocks: `docs/deployment/infra-validation-approvals/2026-11-20-g2-approved-values-proposal.md`,
  SHA-256 `e05e9d2d3f54e291c3a0337041db9243083db91e7f55a4eafd7cfbc6f4e9fbd6`.

`contract.json` changes when this record is filed, so the upload `SHA256SUMS` is regenerated from
the **committed** contract after filing. The owner compares every uploaded file's SHA-256 with the
repository before running anything. Any other byte in any bound file invalidates this approval.

## 2. Contract transition (exact)

Only these fields change, in one edit, after this record's own SHA-256 is known:

| Field | From | To |
| --- | --- | --- |
| `status` | `PREPARATION_ONLY` | `APPROVED_FOR_VALIDATION` |
| `approvals.cloud_validation.status` | `PENDING` | `APPROVED` |
| `approvals.cloud_validation.approval_identity` | `null` | `repository-owner` |
| `approvals.cloud_validation.approval_time` | `null` | `2026-11-21T00:48:17Z` |
| `approvals.cloud_validation.evidence_sha256` | `null` | `H_RECORD` |
| `execution.run_id` | `null` | `infraval-20261125-01` |
| `execution.resource_group` | `null` | `rg-claims-infraval-uks-tmp01` |
| `execution.reviewed_template_sha256` | `null` | `28c29de5f4d0bc36529a5682246da5324cb9b2db8267583b8227254e55c41a17` |
| `execution.approved_template_sha256` | `null` | `dfc26600fb9c8748fdf9fead8078bf281f4482ae27ed987c004adf33bb970989` |
| `execution.approved_parameters_sha256` | `null` | `d668581c7e7c0b9a025ebedc9c124058be6ea371ff649084f9dd9c3ed6208b7c` |

`H_RECORD` is a symbolic reference to the SHA-256 of the final recorded file, calculated
only after both pending UTC timestamp fields in this record have been replaced with the same
actual owner-authorised recording time. Keep `H_RECORD` literal in this record; insert the
resulting numerical digest only in `contract.json`. Do not insert the resulting contract hash,
upload-manifest hash or recording commit ID into this record. The baseline identifies the
reviewed input commit. This ordering avoids a self-referential hash dependency.

**Unchanged:** `provisioning_allowed=false`; `execution.approved_whatif_sha256`,
`window_start_utc` and `window_end_utc` stay `null` (they belong to stage 7); `provisioning`,
`teardown` and `evidence` stay `PENDING`; all `approved_values`, approval records and hashes; both
repository Bicep gates stay `@allowed([false])`.

## 3. G9: resource-group creation and empty-group cleanup

**Creation** — permitted **once**, on **2026-11-25 UTC**, only by running proposal block 2
verbatim (SHA-256 above) in Azure Cloud Shell, after the preflight passes. It may create only
`rg-claims-infraval-uks-tmp01` in `uksouth`, with exactly the tags `purpose=infrastructure-validation`,
`infravalRun=infraval-20261125-01`, `expiresAt=2026-11-25T16:00:00Z`. No resource, lock, role
assignment, policy or budget is created.

Stop for owner review — **no retry, no delete, no manual fix** — if:
- the preflight refuses;
- the group already exists (any letter case) or the group list fails;
- the create fails;
- after creation, the state isn't `Succeeded`, the location isn't `uksouth`, the tags aren't
  exactly the three above, or any resource or lock is present.

**Empty-group cleanup** — permitted only by running proposal block 3 verbatim, and only if
stage 7 doesn't follow (section 8). It deletes only this group, only when it carries this run's
`infravalRun` and `purpose` tags, holds no resource and no lock, and has no deployment in a state
other than `Succeeded`, `Failed` or `Canceled`. There's no `--no-wait` and no
`--force-deletion-types`. If any check fails: **don't delete**; stop for owner review.

Initiate G9 empty-group cleanup immediately on abort, subject to all checks above. Complete
cleanup and verify the group's absence by **16:00 UTC on November 25, 2026**
(`2026-11-25T16:00:00Z`). If cleanup cannot be completed or absence cannot be verified by this deadline,
stop, record the failure and request a separately authorised recovery. This grants no permission
to provision or delete other resources.

This hard deadline supersedes the proposal's cleanup timing for this run. The bound cleanup
block and all subscription, resource, tag, lock and deployment-state checks remain unchanged.

## 4. Stage 6 run

Permitted **once**, on 2026-11-25 UTC, after G9 creation passes, by running the bound procedure
verbatim in a fresh Cloud Shell directory holding exactly the six files and `SHA256SUMS`.
It performs, in order: manifest check; offline `--authorize-validation` (must return
`AUTHORIZED_FOR_VALIDATION_ONLY` / `NOT_AUTHORIZED`); expiry check; bootstrap and preflight; read-only
group checks; one `az deployment group validate`; one `az deployment group what-if`; offline
`--check-whatif` (exactly the seven `Create`s); a post-check that the group is still empty and idle.
A PASS ends with `STAGE6_VALIDATE_WHATIF: PASS` and the SHA-256 of `whatif.json` and
`validate.json`.

The owner downloads `whatif.json` to the git-ignored `outputs/` area and re-runs
`--check-whatif` locally. Its hash is **evidence for the stage 7 decision only**; this record
doesn't bind it.

## 5. Explicitly not authorised

- **Stage 7 provisioning:** no `az deployment group create`, no deployment of any template, no
  execution window. `APPROVED_FOR_VALIDATION` can't authorise execution: the validator refuses
  with `contract_not_approved_for_execution`, and even with the status forced, with
  `approval_incomplete:provisioning`.
- **Stage 8 teardown and Key Vault purge:** `plan_teardown` refuses (`approval_incomplete:teardown`).
  Only the empty-group cleanup in section 3 may delete anything.
- **Provider registration:** none. No `az provider register`, feature or preview registration.
  Neither the stage 6 script nor the G9 blocks contain a provider command. If validate or what-if
  reports an unregistered provider (for example `MissingSubscriptionRegistration`), stop: don't
  register it and don't rerun.
- Subscription budget changes, role assignments, locks, policy changes, any other resource group,
  and any change to the templates, parameters, validator, preflight or procedure.

## 6. Optional read-only provider check (G1 residual)

Before the stage 6 run, the owner may confirm `Microsoft.Consumption` (used by the resource-group
budget) with this read-only block. If it doesn't print a pass (the `test` fails), stop: stage 6
doesn't run until the owner decides.

```bash
set -euo pipefail
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json
test "$(az provider show -n Microsoft.Consumption --subscription "$SUB" --query registrationState -o tsv)" = Registered
```

## 7. Unsupported what-if, unexpected CLI behaviour, sensitive files

**What-if results (G5).** Anything other than exactly one `Create` for each of the seven types —
including `Unsupported`, `Ignore`, `NoChange`, `Modify`, `Deploy`, a missing or duplicate type, or
any other type — makes `--check-whatif` refuse and the script stop. That's a stop for owner
decision, not a failure to work around. Don't rerun, edit the validator, filter the what-if or
hand-edit `whatif.json`. Accepting any such result needs a new reviewed validator change and new
dated records, which can't happen inside the window.

**Unexpected Azure CLI behaviour.** Stop, don't rerun and don't edit the bound script, if:
- a flag is rejected, the CLI prompts, or it asks to install an extension or upgrade;
- the output shape differs (for example no `status` or `properties.provisioningState`), or a
  command times out;
- validate or what-if returns a policy, quota, throttling or authorisation error;
- the group state changes between checks.

Record the step, the exit code and the **masked** error text. Changing the script changes its
hash and needs a new dated record.

**Sensitive files.** `validate.json`, `whatif.json` and `whatif-check.json` contain resource IDs
with the raw subscription ID; Azure error text on the terminal may too. They stay in Cloud Shell
and the git-ignored `outputs/` area only: never committed, pasted or shared unless every
`/subscriptions/<id>` is masked. `authorize.json` contains no ID. Records cite only file hashes.

## 8. Timing and abort plan

| Time (2026-11-25 UTC) | Step |
| --- | --- |
| from 08:00 | Optional provider check; G9 creation |
| by **11:00** | Stage 6 PASS (**stage 6 cutoff**) |
| 11:00–12:45 | Owner reviews the what-if; stage 7/8 decisions recorded and committed separately |
| 13:00–15:00 | Approved window (stage 7, not authorised here) |
| 16:00 | Hard expiry: G9 cleanup complete and absence verified; the stage 6 script refuses after this |

**Abort** if stage 6 hasn't passed by 11:00, any stop condition fires, or the stage 7/8 records
aren't committed before 13:00:

1. Don't provision. Nothing in stage 7 or 8 starts.
2. Initiate G9 empty-group cleanup immediately on abort if the group exists, using only the
   unchanged, hash-bound cleanup block with every subscription, resource, tag, lock and
   deployment-state check intact. Complete cleanup and verify absence by **16:00 UTC on
   November 25, 2026** (`2026-11-25T16:00:00Z`). If the group is already absent, verify and record
   its absence. If the group isn't empty or idle, any check fails, cleanup cannot be completed,
   or absence cannot be verified by the deadline: stop, record the failure and request a separately
   authorised recovery. Do not provision or delete other resources.
3. Record the outcome in a dated execution record (masked output, hashes, group state).
4. **Rescheduling** needs new dated records: a new `T0`, `expires_at` and `run_id`, so a new
   `parameters.json` hash and a new stage 6 approval (the group's `expiresAt` and `infravalRun`
   tags are bound to this run, so this group can't be reused). The deployment must still be in
   **November 2026 UTC** (G4); later than that needs a new budget record. The subscription budget
   is unaffected.

## Verification at drafting (offline)

On a scratchpad copy of the contract with exactly the section 2 transition (placeholder record
hash): `validate_contract` PASS; `authorize_validation` → `AUTHORIZED_FOR_VALIDATION_ONLY`,
`NOT_AUTHORIZED`; `authorize_execution` refused (`contract_not_approved_for_execution`; with the
status and flag forced, `approval_incomplete:provisioning`); `plan_teardown` refused
(`approval_incomplete:teardown`); `refuse_provisioning` refused. The bound stage 6 script ran end
to end against a stub `az` with the real templates and parameters: PASS, using only `account show`,
`group exists`, `group show`, `resource list`, `lock list`, `deployment group list`, `validate` and
`what-if`. The repository contract wasn't changed.

M22 restrictions, M23 SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE
COMPLETE are unchanged.
