#!/usr/bin/env bash
# Stage 8: fail-closed teardown for the infrastructure-only validation (Option C).
#
# PREPARED, NOT APPROVED. Don't run it before the stage 8 `teardown` approval is recorded. It
# refuses on its own unless the uploaded contract approves teardown. It's separately gated from
# stage 7: it never deploys, and stage 7 never deletes.
#
# Run in Azure Cloud Shell (Bash) in the stage 7 directory: the same eight hash-checked files
# (SHA256SUMS), plus targets.json pinned by stage 7. It is resume-safe: each run re-reads the live
# state, re-plans with the validator and acts only on what still exists. If a run stops, fix
# nothing by hand: record the masked output and rerun only after owner review.
#
# Order (validator plan): evidence -> resource-group budget -> workspace (permanent delete) ->
# resource group -> Key Vault purge-target check -> purge -> absence verification. The
# subscription budget infraval-uks-tmp01-budget and NetworkWatcherRG are never touched.
# ev8-*/, state.json and plan.json contain the raw subscription ID: never commit or share them.
#
# Offline lint: python3 -I infra_subscription_preflight.py lint infra_stage8_teardown.sh
set -euo pipefail
set -E
umask 077
trap 'echo "STAGE8_STOPPED at line $LINENO: no retry, no manual deletion. Owner review, then rerun this procedure." >&2' ERR

# 1. Integrity of the uploaded files (offline).
test "$(awk '{print $2}' SHA256SUMS | LC_ALL=C sort | tr '\n' ' ')" = "contract.json execution.json infra_evidence.py infra_subscription_preflight.py infra_validation.py parameters.json reviewed.json whatif.json "
sha256sum --strict --quiet -c SHA256SUMS

# 2. Offline gate: the contract must approve teardown (the validator refuses otherwise, exit 78).
printf '{"group": null}\n' > gate-state.json
python3 -I -B infra_validation.py --contract contract.json --plan-teardown gate-state.json > gate-plan.json
test "$(python3 -I -B infra_evidence.py get gate-plan.json decision)" = VERIFY_ONLY
RG=$(python3 -I -B infra_evidence.py get contract.json execution resource_group)
RUN=$(python3 -I -B infra_evidence.py get contract.json execution run_id)
LOCATION=$(python3 -I -B infra_evidence.py get contract.json approved_values location)
EXPIRES=$(python3 -I -B infra_evidence.py get contract.json approved_values expires_at)
DEPLOYMENT="$RUN-deploy"
EV="ev8-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$EV"
python3 -I -c 'import sys; from datetime import UTC, datetime; print("EXPIRY_BREACHED" if datetime.now(UTC) > datetime.fromisoformat(sys.argv[1]) else "WITHIN_EXPIRY")' "$EXPIRES" | tee "$EV/expiry-status.txt"

# 3. Subscription identity (read-only), before every other Azure command.
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json

BUDGETS_URL="https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/$RG/providers/Microsoft.Consumption/budgets"
SUB_BUDGET_URL="https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Consumption/budgets/infraval-uks-tmp01-budget?api-version=2021-10-01"

capture_state() {
  az group show -n "$RG" --subscription "$SUB" -o json > "$EV/group.json"
  az lock list -g "$RG" --subscription "$SUB" -o json > "$EV/locks.json"
  az resource list -g "$RG" --subscription "$SUB" -o json > "$EV/resources.json"
  az deployment group show -g "$RG" -n "$DEPLOYMENT" --subscription "$SUB" -o json > "$EV/deployment.json"
  az rest --method get --subscription "$SUB" -o json --url "$BUDGETS_URL?api-version=2021-10-01" > "$EV/budgets.json"
  az role assignment list --scope "/subscriptions/$SUB/resourceGroups/$RG" --subscription "$SUB" --query "[].scope" -o json > "$EV/roles.json"
  test "$(python3 -I -B infra_evidence.py count-scopes "$RG" < "$EV/roles.json")" = 0
  python3 -I -B infra_evidence.py state "$EV" > state.json
}

cancel_deployment() {
  az deployment group cancel -g "$RG" -n "$DEPLOYMENT" --subscription "$SUB"
  echo "STAGE8_CANCEL_REQUESTED: rerun this procedure once the deployment is no longer Running or Accepted"
  exit 3
}

delete_budget() {
  az rest --method delete --subscription "$SUB" --url "$BUDGETS_URL/$1?api-version=2021-10-01"
  test "$(az rest --method get --subscription "$SUB" --url "$BUDGETS_URL?api-version=2021-10-01" --query "length(value)" -o tsv)" = 0
}

delete_workspace() {
  az monitor log-analytics workspace delete -g "$RG" -n "$1" --force true --yes --subscription "$SUB"
  test "$(az resource list -g "$RG" --subscription "$SUB" --resource-type Microsoft.OperationalInsights/workspaces --query "length(@)" -o tsv)" = 0
  test "$(az monitor log-analytics workspace list-deleted-workspaces --subscription "$SUB" --query "length([?name=='$1'])" -o tsv)" = 0
}

delete_group() {
  test "$1" = "$RG"
  test "$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
  az group delete -n "$RG" --yes --subscription "$SUB"
  test "$(az group exists -n "$RG" --subscription "$SUB")" = false
}

purge_vault() {
  DELETED_ID=$(az keyvault show-deleted --name "$1" --subscription "$SUB" --query properties.vaultId -o tsv)
  test "$(python3 -I -B infra_validation.py --contract contract.json --verify-purge "$1" "$DELETED_ID")" = '"PURGE_TARGET_VERIFIED"'
  az keyvault purge --name "$1" --location "$LOCATION" --subscription "$SUB"
  test "$(az keyvault list-deleted --subscription "$SUB" --query "length([?name=='$1'])" -o tsv)" = 0
}

verify_absent() {
  test "$(az group exists -n "$RG" --subscription "$SUB")" = false
  VAULT=$(python3 -I -B infra_evidence.py get-optional targets.json vault)
  WORKSPACE=$(python3 -I -B infra_evidence.py get-optional targets.json workspace)
  case "$VAULT" in
    none) ;;
    *) PENDING=$(az keyvault list-deleted --subscription "$SUB" --query "length([?name=='$VAULT'])" -o tsv)
       case "$PENDING" in
         0) ;;
         1) purge_vault "$VAULT" ;;
         *) echo "unexpected soft-deleted vault count" >&2; exit 1 ;;
       esac ;;
  esac
  case "$WORKSPACE" in
    none) ;;
    *) test "$(az monitor log-analytics workspace list-deleted-workspaces --subscription "$SUB" --query "length([?name=='$WORKSPACE'])" -o tsv)" = 0 ;;
  esac
  test "$(az resource list --subscription "$SUB" --query "[].id" -o json | python3 -I -B infra_evidence.py count-ids targets.json)" = 0
  test "$(az resource list --subscription "$SUB" --tag purpose=infrastructure-validation --query "length(@)" -o tsv)" = 0
  test "$(az role assignment list --all --subscription "$SUB" --query "[].scope" -o json | python3 -I -B infra_evidence.py count-scopes "$RG")" = 0
  test "$(az rest --method get --subscription "$SUB" --url "$SUB_BUDGET_URL" --query name -o tsv)" = infraval-uks-tmp01-budget
  az group exists -n NetworkWatcherRG --subscription "$SUB" > "$EV/networkwatcherrg-exists.txt"
  python3 -I -B infra_evidence.py receipt teardown-receipt.json
}

# 4. Live state -> validator plan -> pinned targets. An absent group is verify-only.
EXISTS=$(az group exists -n "$RG" --subscription "$SUB")
case "$EXISTS" in
  true) capture_state ;;
  false) printf '{"group": null}\n' > state.json ;;
  *) echo "unexpected group state" >&2; exit 1 ;;
esac
python3 -I -B infra_validation.py --contract contract.json --plan-teardown state.json > plan.json
python3 -I -B infra_evidence.py targets state.json plan.json targets.json
python3 -I -B infra_evidence.py mask "$EV" "$EV-masked"

# 5. Execute the plan in the validator's order; every step verifies its own result.
ACTIONS=$(python3 -I -B infra_evidence.py actions plan.json targets.json)
for ACTION in $ACTIONS; do
  case "$ACTION" in
    CAPTURE_EVIDENCE) echo "evidence captured in $EV" ;;
    CANCEL_DEPLOYMENT_THEN_REPLAN) cancel_deployment ;;
    DELETE_BUDGET:*) delete_budget "${ACTION#DELETE_BUDGET:}" ;;
    FORCE_DELETE_WORKSPACE:*) delete_workspace "${ACTION#FORCE_DELETE_WORKSPACE:}" ;;
    DELETE_GROUP:*) delete_group "${ACTION#DELETE_GROUP:}" ;;
    VERIFY_PURGE_TARGET_THEN_PURGE_VAULT:*) purge_vault "${ACTION#VERIFY_PURGE_TARGET_THEN_PURGE_VAULT:}" ;;
    VERIFY|VERIFY:group_absent) verify_absent ;;
    *) echo "unexpected action" >&2; exit 1 ;;
  esac
done

python3 -I -B infra_evidence.py mask "$EV" "$EV-masked"
echo "NetworkWatcherRG exists: $(cat "$EV/networkwatcherrg-exists.txt") (recorded only; never deleted)"
echo "STAGE8_TEARDOWN_VERIFIED: PASS ($(cat "$EV/expiry-status.txt")). Cost checks due at +24h and +72h."
