#!/usr/bin/env bash
# Stage 8: read-only +24h / +72h post-teardown checks for the infrastructure validation.
#
# PREPARED, NOT APPROVED. Runs under the stage 8 `teardown` approval, in the stage 7/8 directory,
# with CHECKPOINT_HOURS=24 or 72. It refuses before the checkpoint is due (from
# teardown-receipt.json), and it changes nothing in Azure. Pay-as-you-go cost data can take up to
# 72 hours, so only the +72h result closes the cost check.
#
# A refusal (residual resource, soft-deleted vault or workspace, missing subscription budget,
# spend in another currency or at/above the approved budget) stops for owner review.
#
# Offline lint: python3 -I infra_subscription_preflight.py lint infra_stage8_cost_check.sh
set -euo pipefail
umask 077
case "$CHECKPOINT_HOURS" in
  24|72) ;;
  *) echo "set CHECKPOINT_HOURS to 24 or 72" >&2; exit 1 ;;
esac

# 1. Integrity, teardown approval and timing (offline).
sha256sum --strict --quiet -c SHA256SUMS
printf '{"group": null}\n' > gate-state.json
python3 -I -B infra_validation.py --contract contract.json --plan-teardown gate-state.json > gate-plan.json
test "$(python3 -I -B infra_evidence.py get gate-plan.json decision)" = VERIFY_ONLY
python3 -I -B infra_evidence.py elapsed teardown-receipt.json "$CHECKPOINT_HOURS"
RG=$(python3 -I -B infra_evidence.py get contract.json execution resource_group)
VAULT=$(python3 -I -B infra_evidence.py get-optional targets.json vault)
WORKSPACE=$(python3 -I -B infra_evidence.py get-optional targets.json workspace)
EV="cost-${CHECKPOINT_HOURS}h-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -m 700 "$EV"

# 2. Subscription identity (read-only), before every other Azure command.
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json

# 3. Still absent, nothing soft-deleted, nothing tagged, no recorded ID back.
test "$(az group exists -n "$RG" --subscription "$SUB")" = false
test "$(az keyvault list-deleted --subscription "$SUB" --query "length([?name=='$VAULT'])" -o tsv)" = 0
test "$(az monitor log-analytics workspace list-deleted-workspaces --subscription "$SUB" --query "length([?name=='$WORKSPACE'])" -o tsv)" = 0
test "$(az resource list --subscription "$SUB" --query "[].id" -o json | python3 -I -B infra_evidence.py count-ids targets.json)" = 0
test "$(az resource list --subscription "$SUB" --tag purpose=infrastructure-validation --query "length(@)" -o tsv)" = 0

# 4. Cost: the subscription budget (filtered to the validation group) still exists, in GBP and
#    below the approved amount.
az rest --method get --subscription "$SUB" -o json \
  --url "https://management.azure.com/subscriptions/{subscriptionId}/providers/Microsoft.Consumption/budgets/infraval-uks-tmp01-budget?api-version=2021-10-01" > "$EV/subscription-budget.json"
test "$(python3 -I -B infra_evidence.py get "$EV/subscription-budget.json" name)" = infraval-uks-tmp01-budget
python3 -I -B infra_evidence.py spend "$EV/subscription-budget.json" contract.json | tee "$EV/spend.txt"
python3 -I -B infra_evidence.py mask "$EV" "$EV-masked"
echo "COST_CHECK_+${CHECKPOINT_HOURS}h: PASS (record $EV-masked/ in the stage 9 evidence)"
