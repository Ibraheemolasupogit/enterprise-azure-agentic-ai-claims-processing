#!/usr/bin/env bash
# Stage 7: one controlled deployment for the infrastructure-only validation (Option C).
#
# PREPARED, NOT APPROVED. Don't run it before the stage 7 `provisioning` approval and the stage 8
# `teardown` approval are recorded, the contract is APPROVED_FOR_EXECUTION_WINDOW and binds the
# stage 6 what-if by hash. It refuses on its own otherwise, and outside the approved window.
#
# Run in Azure Cloud Shell (Bash), in a fresh directory that holds exactly these eight files and a
# SHA256SUMS manifest for them, generated locally from the approved commit and compared by the
# owner before upload:
#   contract.json  execution.json  reviewed.json  parameters.json  whatif.json
#   infra_subscription_preflight.py  infra_validation.py  infra_evidence.py
# Keep this directory: the stage 8 procedure runs in it and needs targets.json and ev/.
#
# One deployment, Incremental mode, synchronous. A second run refuses (the group must have no
# deployment). Any failure stops the script: don't rerun, go to the stage 8 procedure.
# ev/, deployment.json and state.json contain the raw subscription ID: never commit or share them.
# Only evidence-masked/ may be shared, after a manual check.
#
# Offline lint: python3 -I infra_subscription_preflight.py lint infra_stage7_deploy.sh
set -euo pipefail
set -E
umask 077
trap 'echo "STAGE7_STOPPED at line $LINENO: no retry. Capture state and follow the stage 8 procedure." >&2' ERR

# 1. Integrity of the uploaded files (offline).
test "$(awk '{print $2}' SHA256SUMS | LC_ALL=C sort | tr '\n' ' ')" = "contract.json execution.json infra_evidence.py infra_subscription_preflight.py infra_validation.py parameters.json reviewed.json whatif.json "
sha256sum --strict --quiet -c SHA256SUMS

# 2. Offline authorisation: stages 1-8 approved, APPROVED_FOR_EXECUTION_WINDOW, exact template,
#    parameters and what-if hashes, and now inside the approved window. Refusal exits 78.
authorize_execution() {
  python3 -I -B infra_validation.py --contract contract.json --authorize-execution \
    --reviewed-template reviewed.json --execution-template execution.json \
    --parameters parameters.json --whatif whatif.json > authorize.json
  test "$(python3 -I -B infra_evidence.py get authorize.json decision)" = AUTHORIZED_FOR_WINDOW
}
authorize_execution
RG=$(python3 -I -B infra_evidence.py get authorize.json resource_group)
RUN=$(python3 -I -B infra_evidence.py get authorize.json run_id)
LOCATION=$(python3 -I -B infra_evidence.py get contract.json approved_values location)
EXPIRES=$(python3 -I -B infra_evidence.py get contract.json approved_values expires_at)
DEPLOYMENT="$RUN-deploy"
mkdir -m 700 ev

# 3. Subscription identity (read-only), before every other Azure command.
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json

# 4. The G9 group is unchanged since stage 6: tags, location, empty, unlocked, no deployment.
CHECK_OUTPUT=$(az group exists -n "$RG" --subscription "$SUB")
test "$CHECK_OUTPUT" = true
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query properties.provisioningState -o tsv)
test "$CHECK_OUTPUT" = Succeeded
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query location -o tsv)
test "$CHECK_OUTPUT" = "$LOCATION"
CHECK_OUTPUT=$(az group show -n "$RG" --subscription "$SUB" --query tags -o json | python3 -I -c 'import json, sys; print(json.load(sys.stdin) == {"purpose": "infrastructure-validation", "infravalRun": sys.argv[1], "expiresAt": sys.argv[2]})' "$RUN" "$EXPIRES")
test "$CHECK_OUTPUT" = True
CHECK_OUTPUT=$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0
CHECK_OUTPUT=$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0
CHECK_OUTPUT=$(az deployment group list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)
test "$CHECK_OUTPUT" = 0

# 5. The one deployment: the bound execution template and parameters, Incremental, synchronous.
authorize_execution
az deployment group create -g "$RG" --subscription "$SUB" -n "$DEPLOYMENT" --mode Incremental \
  --template-file execution.json --parameters @parameters.json -o json > deployment.json
test "$(python3 -I -B infra_evidence.py get deployment.json properties provisioningState)" = Succeeded

# 6. Evidence (read-only) and the exact inventory: one of each of the seven approved types, all
#    tagged, all in the deployment record; teardown targets pinned for stage 8.
az group show -n "$RG" --subscription "$SUB" -o json > ev/group.json
az lock list -g "$RG" --subscription "$SUB" -o json > ev/locks.json
az resource list -g "$RG" --subscription "$SUB" -o json > ev/resources.json
az deployment group show -g "$RG" -n "$DEPLOYMENT" --subscription "$SUB" -o json > ev/deployment.json
az rest --method get --subscription "$SUB" -o json \
  --url "https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/$RG/providers/Microsoft.Consumption/budgets?api-version=2021-10-01" > ev/budgets.json
az role assignment list --scope "/subscriptions/$SUB/resourceGroups/$RG" --subscription "$SUB" --query "[].scope" -o json > ev/roles.json
test "$(python3 -I -B infra_evidence.py count-scopes "$RG" < ev/roles.json)" = 0
python3 -I -B infra_evidence.py state ev > state.json
python3 -I -B infra_validation.py --contract contract.json --plan-teardown state.json > plan.json
test "$(python3 -I -B infra_evidence.py expect-full plan.json state.json)" = INVENTORY_EXACT
test "$(python3 -I -B infra_evidence.py targets state.json plan.json targets.json)" = TARGETS_RECORDED
python3 -I -B infra_evidence.py mask ev evidence-masked

# 7. Hashes only; the files stay in Cloud Shell.
sha256sum deployment.json state.json plan.json targets.json
echo "STAGE7_DEPLOYED: PASS (teardown is due before $EXPIRES; run the stage 8 procedure in this directory)"
