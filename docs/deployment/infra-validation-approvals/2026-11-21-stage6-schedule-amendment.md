# Stage 6 and G9 schedule amendment for November 21, 2026

**Reviewed baseline:** `c0125f41b0ec11b8d233a4857c19e172ebb3d02e` · **Approver:** repository-owner ·
**Recorded UTC:** `2026-11-21T05:46:44Z`.

Upon owner-authorised recording, this dated record supersedes only the schedule, run ID, expiry and
affected command and file bindings for the November 25 run in the existing Stage 6 approval
(`3c15dfde020c6a0931628cbeb5c3db0e07c21de980d9c7792ffec4de271dbccb`) and G2/G3-A approval (`bcb8f7909c08b9612421fc96dbeaa81dc229220cee7c80c138c3a7192933ecf2`).
It incorporates the existing G9 proposal (`e05e9d2d3f54e291c3a0337041db9243083db91e7f55a4eafd7cfbc6f4e9fbd6`) as amended below.
Preserve those records. Once recorded, this replacement has no automatic November 25 fallback.

Run `infraval-20261121-01` once in `uksouth` for `rg-claims-infraval-uks-tmp01`
under the existing subscription commitment and security/cost safeguards. From **08:00 UTC**
the owner may begin G9 and Stage 6 after the amendment and five-field contract transition are
committed, the upload is verified, and the owner gives separate execution instruction.
Require Stage 6 PASS by **11:00 UTC**. Reserve **11:00–13:00** for evidence review and separate
Stage 7 and Stage 8 approvals. **13:00–14:00 UTC** is the proposed deployment submission
window for a later approval. It reserves two hours after the last submission time for
teardown. Verified absence is due by **16:00 UTC** (`2026-11-21T16:00:00Z`).
Allow additional time before submitting if live conditions warrant it. If approval or
operational readiness cannot meet these cutoffs, skip the run and obtain a new schedule.

The contract transition changes only expiry, run ID, the parameter hash, and the Stage 6
approval time and record hash. Stages 7–9 stay pending, provisioning remains false, and the
what-if hash and Stage 7 window fields stay null. Contract status stays
`APPROVED_FOR_VALIDATION`. Both repository Bicep gates stay false-only. This amendment
covers only G9 and Stage 6 validation and what-if. The optional provider check is read-only.
The contract references the finalized record SHA-256. This record embeds no self-hash.

| Amended binding | SHA-256 |
| --- | --- |
| Stage 6 script `infra_stage6_validate_whatif_20261121.sh` | `1c4def2ac0521c5535a5781105a11dd9cf200e6cc1c959cd8c853a0c8c2767df` |
| `execution.json` | `dfc26600fb9c8748fdf9fead8078bf281f4482ae27ed987c004adf33bb970989` |
| `infra_subscription_preflight.py` | `858b102e08fc2634ab74537c4c595fa582b5b641b3b423f22b5799b9daec4287` |
| `infra_validation.py` | `3b971f1f5355efaa0a1824f2fb7d39e83dc336bfc9c0d13a653f387f17b1b2fb` |
| `parameters.json` | `b679e8e0b170b1fa2bc9ed162125ea2c968ebf5e5a7b06c728c11ca937f0a946` |
| `reviewed.json` | `28c29de5f4d0bc36529a5682246da5324cb9b2db8267583b8227254e55c41a17` |
| `g9-cleanup.sh` | `52a897c32d97ef16e5e2967db330dc5a55254d68253c35782407d78bf274e1b3` |
| `g9-create.sh` | `dd408671da55c2c2612570a73c38c38351183f095a85bdf6647c38b62a4943b7` |
| `provider-check.sh` | `424a59f1fd96e275cf76156e40270565460c67d0f494dd75161a160ba7de310d` |


The revised shell checks require successful command exit before comparing the output. The
G9 operations, subscription guards, expected group state and cleanup scope carry forward.
Stage 6 remains restricted to read-only checks, ARM validate and what-if. The seven approved
resource types, templates, budget values, budget retention, optional environment setting,
log cap and historical evidence retain their bindings. Keep bound Cloud Shell evidence private.

## G9 creation (exact block)

```bash
set -euo pipefail
RG=rg-claims-infraval-uks-tmp01
RUN=infraval-20261121-01
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json
CHECK_OUTPUT=$(az group exists -n "$RG" --subscription "$SUB")
test "$CHECK_OUTPUT" = false
NAMES=$(az group list --subscription "$SUB" --query "[].name" -o tsv)
N=$(printf '%s\n' "$NAMES" | tr 'A-Z' 'a-z' | grep -cxF "$RG" || true)
test "$N" = 0
az group create -n "$RG" -l uksouth --subscription "$SUB" -o none \
  --tags purpose=infrastructure-validation infravalRun="$RUN" expiresAt=2026-11-21T16:00:00Z
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query properties.provisioningState -o tsv)
test "$CHECK_OUTPUT" = Succeeded
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query location -o tsv)
test "$CHECK_OUTPUT" = uksouth
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query tags -o json | python3 -I -c 'import json,sys; print(json.load(sys.stdin) == {"purpose": "infrastructure-validation", "infravalRun": sys.argv[1], "expiresAt": "2026-11-21T16:00:00Z"})' "$RUN")
test "$CHECK_OUTPUT" = True
CHECK_OUTPUT=$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0
CHECK_OUTPUT=$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0
```

## G9 empty-group cleanup (exact block)

```bash
set -euo pipefail
RG=rg-claims-infraval-uks-tmp01
RUN=infraval-20261121-01
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query "tags.infravalRun" -o tsv)
test "$CHECK_OUTPUT" = "$RUN"
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query "tags.purpose" -o tsv)
test "$CHECK_OUTPUT" = infrastructure-validation
CHECK_OUTPUT=$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0
CHECK_OUTPUT=$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0
CHECK_OUTPUT=$(az deployment group list -g "$RG" --subscription "$SUB" --query "length([?properties.provisioningState!='Succeeded' && properties.provisioningState!='Failed' && properties.provisioningState!='Canceled'])" -o tsv)
test "$CHECK_OUTPUT" = 0
az group delete -n "$RG" --subscription "$SUB" --yes
CHECK_OUTPUT=$(az group exists -n "$RG" --subscription "$SUB")
test "$CHECK_OUTPUT" = false
```

## Optional provider check (exact block)

```bash
set -euo pipefail
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json
CHECK_OUTPUT=$(az provider show -n Microsoft.Consumption --subscription "$SUB" --query registrationState -o tsv)
test "$CHECK_OUTPUT" = Registered
```


Abort on any stop condition or missed cutoff. If no deployment was submitted and the group
qualifies, initiate the amended G9 empty-group cleanup immediately on abort and verify absence
by 16:00 UTC. If creation state or submission is uncertain, or any cleanup safeguard fails,
stop and record the failure for separate owner-approved recovery. Follow the closure runbook
for separately approved teardown, cost checks and Stage 9 evidence.
