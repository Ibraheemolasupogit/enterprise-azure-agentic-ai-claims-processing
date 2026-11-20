#!/usr/bin/env bash
# Stage 6: ARM validate and what-if for the infrastructure-only validation (Option C).
#
# PREPARED, NOT APPROVED. Don't run it before the stage 6 `cloud_validation` approval, the G2
# and G3-A decisions and the G9 resource-group creation. It refuses on its own unless the
# uploaded contract is APPROVED_FOR_VALIDATION and binds these exact artifacts by hash.
#
# Run in Azure Cloud Shell (Bash), in a fresh directory that holds exactly these six files and
# a SHA256SUMS manifest for them, generated locally at the approved commit and compared by the
# owner before upload:
#   infra_subscription_preflight.py  infra_validation.py  contract.json
#   reviewed.json    the reviewed compiled template
#   execution.json   the approved execution compiled template
#   parameters.json  the approved parameter file
#
# Azure operations: read-only checks, then one ARM validate and one what-if. Neither creates a
# resource. There's no create, delete, deployment, retry or --no-wait. Any failed check stops
# the script with a non-zero exit; stop for owner review and don't rerun parts of it by hand.
# validate.json and whatif.json contain the raw subscription ID: never commit or share them
# unmasked. Azure error text on the terminal may also show it.
#
# Offline lint: python3 -I infra_subscription_preflight.py lint infra_stage6_validate_whatif.sh
set -euo pipefail
umask 077

# 1. Integrity of the uploaded files (offline): exactly the six files, each matching SHA256SUMS.
test "$(awk '{print $2}' SHA256SUMS | LC_ALL=C sort | tr '\n' ' ')" = "contract.json execution.json infra_subscription_preflight.py infra_validation.py parameters.json reviewed.json "
sha256sum --strict --quiet -c SHA256SUMS

# 2. Offline authorisation: stages 1-6 approved, status APPROVED_FOR_VALIDATION, and these exact
#    templates and parameters bound by hash. A refusal exits 78 before any Azure command.
python3 -I -B infra_validation.py --contract contract.json --authorize-validation \
  --reviewed-template reviewed.json --execution-template execution.json \
  --parameters parameters.json > authorize.json
FIELD='import functools, json, sys; v = functools.reduce(lambda a, k: a[k], sys.argv[2:], json.load(open(sys.argv[1]))); ok = isinstance(v, str) and v != "" and v == v.strip(); print(v) if ok else sys.exit("field_invalid")'
test "$(python3 -I -c "$FIELD" authorize.json decision)" = AUTHORIZED_FOR_VALIDATION_ONLY
test "$(python3 -I -c "$FIELD" authorize.json provisioning)" = NOT_AUTHORIZED
RG=$(python3 -I -c "$FIELD" authorize.json resource_group)
RUN=$(python3 -I -c "$FIELD" authorize.json run_id)
LOCATION=$(python3 -I -c "$FIELD" contract.json approved_values location)
EXPIRES=$(python3 -I -c "$FIELD" contract.json approved_values expires_at)
DEPLOYMENT="$RUN-stage6"
test "$(python3 -I -c 'import sys; from datetime import UTC, datetime; print(datetime.now(UTC) < datetime.fromisoformat(sys.argv[1]))' "$EXPIRES")" = True

# 3. Subscription identity (read-only), before every other Azure command.
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \
  python3 -I infra_subscription_preflight.py check --contract contract.json

# 4. The G9 group exists exactly as created, and is empty, unlocked and without deployments.
test "$(az group exists -n "$RG" --subscription "$SUB")" = true
test "$(az group show -n "$RG" --subscription "$SUB" --query properties.provisioningState -o tsv)" = Succeeded
test "$(az group show -n "$RG" --subscription "$SUB" --query location -o tsv)" = "$LOCATION"
test "$(az group show -n "$RG" --subscription "$SUB" --query tags -o json | python3 -I -c 'import json, sys; print(json.load(sys.stdin) == {"purpose": "infrastructure-validation", "infravalRun": sys.argv[1], "expiresAt": sys.argv[2]})' "$RUN" "$EXPIRES")" = True
test "$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
test "$(az lock list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
test "$(az deployment group list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0

# 5. ARM validate, then what-if, of the bound execution template (no resource is created).
az deployment group validate -g "$RG" --subscription "$SUB" -n "$DEPLOYMENT" \
  --template-file execution.json --parameters @parameters.json -o json > validate.json
test "$(python3 -I -c "$FIELD" validate.json properties provisioningState)" = Succeeded
az deployment group what-if -g "$RG" --subscription "$SUB" -n "$DEPLOYMENT" \
  --template-file execution.json --parameters @parameters.json \
  --result-format FullResourcePayloads --no-pretty-print -o json > whatif.json
test "$(python3 -I -c "$FIELD" whatif.json status)" = Succeeded

# 6. Offline what-if check (exactly the seven Creates), and proof that nothing was created.
python3 -I -B infra_validation.py --contract contract.json --check-whatif whatif.json > whatif-check.json
test "$(az resource list -g "$RG" --subscription "$SUB" --query "length(@)" -o tsv)" = 0
test "$(az deployment group list -g "$RG" --subscription "$SUB" --query "length([?properties.provisioningState!='Succeeded' && properties.provisioningState!='Failed' && properties.provisioningState!='Canceled'])" -o tsv)" = 0

# 7. Evidence for the owner: hashes only. The files stay in Cloud Shell.
sha256sum whatif.json validate.json
echo "STAGE6_VALIDATE_WHATIF: PASS (validation only; provisioning not authorised)"
