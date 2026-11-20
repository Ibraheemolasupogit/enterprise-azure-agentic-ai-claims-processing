# Infrastructure validation proposal — stage 5 condition G2 (approved values), G3-A and G9

**Prepared:** 2026-11-20 · **Status: PROPOSED — NOT APPROVED** · **Baseline:** `03fe7cc`

This is a proposal for owner decision, not an approval record. Nothing cites it from
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json). All six
G2 `approved_values` remain `null`; G2, G3 and G9 stay open; the contract stays
`PREPARATION_ONLY` with `provisioning_allowed=false`. Approving it needs a **separate dated
approval record** that cites this file's hash and supplies the verified subscription commitment.
This file is immutable once committed.

## G2: proposed values

| Value | Proposed | Basis |
| --- | --- | --- |
| `location` | `uksouth` | Scope approval |
| `resource_group` | `rg-claims-infraval-uks-tmp01` | Scope approval; not the protected `rg-claims-agentic-ai-dev` |
| `include_container_environment` | `false` | Scope approval; the validator requires `false` |
| `log_daily_quota_gb` | `1` | Cost-exposure record ("the 1 GB daily cap") |
| `subscription_id` | `sha256:<verified hash>`: supplied by the owner at approval | Commitment, below |
| `expires_at` | `2026-11-25T16:00:00Z` | `T0` + 3 h: hard deadline for teardown, including the Key Vault purge |

Execution identity, recorded for the later stage 6 and stage 7 approvals (not `approved_values`):

| Item | Proposed |
| --- | --- |
| `T0` (`window_start_utc`) | `2026-11-25T13:00:00Z` |
| `window_end_utc` | `2026-11-25T15:00:00Z` (2 h, the validator's maximum) |
| `run_id` | `infraval-20261125-01` (also the group's `infravalRun` tag) |

Checks offline: all three timestamps use the same `…Z` form, which Python 3.12 parses as UTC.
`expiresAt` is 20 characters, the template's minimum. The window is 2 h and ends 1 h before
`expires_at`. `T0` is in November 2026, as the resource-group budget's `2026-11-01` start requires
(G4), and +72 h (2026-11-28) also falls in November.

Recording `expires_at` binds it into the parameter file and the `expiresAt` tag, so moving `T0`
later needs a new dated record. The stage 6 what-if should run on 2026-11-25, before `T0`, so
policy or quota changes can't go unnoticed. If the window crosses the workspace's daily-cap reset,
up to 2 GB could be ingested instead of 1 GB; fast teardown is the mitigation.

## Subscription identity: commitment, not the raw ID

`subscription_id` is to hold a domain-separated SHA-256 commitment:
`sha256(` `infraval-subscription-v1:` + lower-cased subscription GUID `)`, written as
`sha256:<64 hex>`. Subscription GUIDs are random, so the commitment can't practically be
reversed. The prefix stops it matching a plain hash of the same ID published elsewhere. The raw
ID never enters the repository.

[`deployment/infra_subscription_preflight.py`](../../../deployment/infra_subscription_preflight.py)
(stdlib only, run in Cloud Shell) enforces this. It reads `az account show` JSON from stdin, so
the ID stays in memory. Every outcome is a fixed code; a refusal exits 78.

- `commit` prints only the commitment, and only after checking the name `OctoCAT-Agentic-AI` and
  the `Enabled` state.
- `check` passes only if the commitment matches the approved value, the name and the `Enabled`
  state match, and the session's `$SUB` (used for every `--subscription`) is that same
  subscription.
- `lint` refuses a procedure in any of these cases:
  - an `az` command lacks `--subscription "$SUB"` (the only exception is the read-only bootstrap
    `az account show --query id -o tsv`);
  - it uses `az account set`;
  - it enables shell tracing (`set -x`), which would log `$SUB`;
  - it contains a GUID literal.

The owner computes the commitment once, read-only:

```bash
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | python3 -I infra_subscription_preflight.py commit
```

The validator is unchanged; it requires only that `subscription_id` is non-null. The binding to
the real subscription is this preflight, which every Cloud Shell session must pass first.

## G3-A: proposed budget-date exception

The resource-group budget's `budgetEndDate` (`2026-12-31`, stage 4) will be later than
`expires_at`. That contradicts the parameter's description ("no later than the approved
expiry"). The validator doesn't enforce the description, and the teardown plan deletes that
budget. **Proposed: accept as a documented exception, with no template or budget change.**

The subscription budget `infraval-uks-tmp01-budget` also ends on `2026-12-31`, later than
`expires_at` **by design**. The scope amendment keeps it after teardown for the +24 h and +72 h
checks, so it isn't part of this exception.

## G9: resource-group creation and cleanup (for the separate stage 6 approval)

ARM validate and what-if need the resource group to exist. The teardown plan needs it created
with `purpose=infrastructure-validation` and `infravalRun=<run_id>`, and not to have existed
before. **Nothing below is approved; don't run it.** It's proposed for the stage 6
`cloud_validation` approval.

**Key risk:** `az group create` on an existing group updates it instead of failing. So absence is
proven first, and the result is checked afterwards; nothing is deleted automatically.

Before either procedure, upload the module and the contract at the approved commit and confirm
their SHA-256 match the repository.

### Creation (one write)

```bash
set -euo pipefail
RG=rg-claims-infraval-uks-tmp01
RUN=infraval-20261125-01
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json
test "$(az group exists -n "$RG" --subscription "$SUB")" = false
NAMES=$(az group list --subscription "$SUB" --query "[].name" -o tsv)
N=$(printf '%s\n' "$NAMES" | tr 'A-Z' 'a-z' | grep -cxF "$RG" || true)
test "$N" = 0
az group create -n "$RG" -l uksouth --subscription "$SUB" -o none \
  --tags purpose=infrastructure-validation infravalRun="$RUN" expiresAt=2026-11-25T16:00:00Z
test "$(az group show -n "$RG" --subscription "$SUB" --query properties.provisioningState -o tsv)" = Succeeded
test "$(az group show -n "$RG" --subscription "$SUB" --query location -o tsv)" = uksouth
test "$(az group show -n "$RG" --subscription "$SUB" --query tags -o json | python3 -I -c 'import json,sys; print(json.load(sys.stdin) == {"purpose": "infrastructure-validation", "infravalRun": sys.argv[1], "expiresAt": "2026-11-25T16:00:00Z"})' "$RUN")" = True
test "$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
test "$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
```

Stop for owner review, with no retry and no delete, if any of these occur:
- the preflight refuses;
- the group exists;
- the create fails;
- the state isn't `Succeeded`;
- the location isn't `uksouth`;
- the tags aren't exactly the three above;
- any resource or lock is present.

### Empty-group cleanup (only if stage 7 doesn't follow)

The teardown plan can't be used here, because it needs the stage 8 approval. Delete only an
empty group from this run, within 24 h of deciding not to proceed:

```bash
set -euo pipefail
RG=rg-claims-infraval-uks-tmp01
RUN=infraval-20261125-01
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json
test "$(az group show -n "$RG" --subscription "$SUB" --query "tags.infravalRun" -o tsv)" = "$RUN"
test "$(az group show -n "$RG" --subscription "$SUB" --query "tags.purpose" -o tsv)" = infrastructure-validation
test "$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
test "$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
test "$(az deployment group list -g "$RG" --subscription "$SUB" --query "length([?properties.provisioningState!='Succeeded' && properties.provisioningState!='Failed' && properties.provisioningState!='Canceled'])" -o tsv)" = 0
az group delete -n "$RG" --subscription "$SUB" --yes
test "$(az group exists -n "$RG" --subscription "$SUB")" = false
```

If any resource or lock is present, or any deployment is in a state other than `Succeeded`,
`Failed` or `Canceled` (for example `Accepted` or `Running`), **don't delete**: stop for owner
review.
There's no `--no-wait` and no `--force-deletion-types`.

Both blocks pass the preflight's `lint` (checked by the repository tests).

## Decisions requested

1. Approve the four fixed values and `expires_at = 2026-11-25T16:00:00Z`; supply the
   commitment from `commit`.
2. Confirm `T0 = 2026-11-25T13:00:00Z`, the window end `15:00:00Z` and
   `run_id = infraval-20261125-01` for the stage 6 and 7 approvals.
3. Accept G3-A.
4. Approve G9 later, as part of stage 6.

Unchanged: all existing approval records and hashes; the validator; both repository Bicep gates
(`@allowed([false])`); M22 restrictions, M23 SECURITY GATE NO-GO, M24's six NOT_TESTED
demonstrations and M25 OFFLINE COMPLETE.
