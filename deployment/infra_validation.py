"""Offline checks for the infrastructure-only Azure validation template (Option C).

Reads local files only: no Azure SDK, credential chain, subprocess, network or deployment.
Provisioning is always refused while the template's hard gate permits only ``false``.
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

TEMPLATE = "infra/azure-validation/main.bicep"
CONTRACT = "infra/azure-validation/contract.json"
M23_MAIN = "infra/azure/main.bicep"
ALLOWED_TYPES = {
    "Microsoft.App/managedEnvironments",
    "Microsoft.Consumption/budgets",
    "Microsoft.Insights/diagnosticSettings",
    "Microsoft.KeyVault/vaults",
    "Microsoft.ManagedIdentity/userAssignedIdentities",
    "Microsoft.Network/networkSecurityGroups",
    "Microsoft.Network/virtualNetworks",
    "Microsoft.OperationalInsights/workspaces",
}
APPROVALS = {
    "budget",
    "cloud_validation",
    "identity_rbac",
    "network",
    "provisioning",
    "region_capacity",
    "scope",
    "teardown",
}
APPROVED_VALUES = {
    "budget_amount",
    "budget_contact_emails",
    "budget_end_date",
    "budget_start_date",
    "expires_at",
    "include_container_environment",
    "location",
    "log_daily_quota_gb",
    "owner",
    "resource_group",
    "subscription_id",
}
SCOPE = {
    "ai_services",
    "application_workload",
    "claims_data",
    "container_images",
    "public_ingress",
    "public_ip",
    "role_assignments",
}
CONTRACT_KEYS = {
    "allowed_resource_types",
    "approvals",
    "approved_values",
    "format",
    "notes",
    "proposed_max_lifetime_hours",
    "provisioning_allowed",
    "restrictions",
    "scope",
    "status",
}
# Parameters whose values must come from an owner approval: declared without defaults.
UNDEFAULTED = (
    "location",
    "owner",
    "expiresAt",
    "budgetAmount",
    "budgetContactEmails",
    "budgetStartDate",
    "budgetEndDate",
    "logDailyQuotaGb",
)
REQUIRED_TAGS = ("purpose", "application", "dataClass", "owner", "expiresAt", "managedBy")
FORBIDDEN = (
    "Microsoft.Network/publicIPAddresses",
    "Microsoft.App/containerApps",
    "Microsoft.Authorization/roleAssignments",
    "federatedIdentityCredentials",
    "Microsoft.ApiManagement",
    "Microsoft.ContainerRegistry",
    "Microsoft.DBforPostgreSQL",
    "Microsoft.ServiceBus",
    "Microsoft.Storage",
    "Microsoft.CognitiveServices",
    "Microsoft.Search",
    "Microsoft.MachineLearningServices",
    "Microsoft.Web/",
    "Microsoft.Compute/",
    "external: true",
    "'Enabled'",
    "image:",
    "secrets",
    "enablePurgeProtection: true",
)
GATE = "@allowed([false])\nparam provisioningApproved bool = false"
M23_GATE = "@allowed([false])\nparam deploymentEnabled bool = false"


class ValidationError(ValueError):
    """Fixed failure code; never contains file contents or credentials."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValidationError(code)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def load_contract(path: Path) -> dict[str, Any]:
    require(not path.is_symlink() and path.is_file(), "contract_unavailable")
    data = path.read_bytes()
    require(len(data) <= 262144, "contract_capacity")
    value = json.loads(data, object_pairs_hook=_unique)
    require(isinstance(value, dict), "contract_shape")
    assert isinstance(value, dict)
    return value


def validate_contract(value: dict[str, Any]) -> None:
    require(set(value) == CONTRACT_KEYS, "contract_keys")
    require(value["format"] == "azure-infrastructure-validation-contract-v1", "contract_format")
    require(value["status"] == "PREPARATION_ONLY", "contract_status")
    require(value["provisioning_allowed"] is False, "provisioning_must_be_false")
    require(set(value["allowed_resource_types"]) == ALLOWED_TYPES, "resource_allowlist")
    require(len(value["allowed_resource_types"]) == len(ALLOWED_TYPES), "resource_allowlist")
    scope = value["scope"]
    require(isinstance(scope, dict) and set(scope) == SCOPE, "scope_keys")
    require(all(v is False for v in scope.values()), "scope_must_exclude_workloads")
    approvals = value["approvals"]
    require(isinstance(approvals, dict) and set(approvals) == APPROVALS, "approval_keys")
    for record in approvals.values():
        require(
            isinstance(record, dict)
            and set(record) == {"approval_identity", "approval_time", "evidence_sha256", "status"},
            "approval_shape",
        )
    values = value["approved_values"]
    require(isinstance(values, dict) and set(values) == APPROVED_VALUES, "approved_value_keys")
    lifetime = value["proposed_max_lifetime_hours"]
    require(isinstance(lifetime, int) and not isinstance(lifetime, bool), "lifetime_type")
    require(0 < lifetime <= 72, "lifetime_bound")
    restrictions = value["restrictions"]
    require(set(restrictions) == {"m22", "m23", "m24"}, "restriction_keys")
    require("SECURITY GATE NO-GO" in restrictions["m23"], "m23_restriction")
    require("NOT_TESTED" in restrictions["m24"], "m24_restriction")


def refuse_provisioning(value: dict[str, Any]) -> None:
    """Always refuses: approvals in a file are not authority while the template gate is false."""
    validate_contract(value)
    raise ValidationError("provisioning_refused_preparation_only")


def _resource_blocks(text: str) -> list[tuple[str, str]]:
    found = re.findall(r"^resource \w+ '([A-Za-z.]+/[A-Za-z/]+)@[0-9a-z-]+' = (.*)$", text, re.M)
    return [(kind, rest) for kind, rest in found]


def validate_template(source: str) -> dict[str, object]:
    # Checks apply to code only; comments can neither satisfy nor trip a rule.
    text = re.sub(r"//.*$", "", source, flags=re.M)
    require(text.count(GATE) == 1, "hard_gate_missing")
    resources = _resource_blocks(text)
    require(bool(resources), "no_resources")
    require({kind for kind, _ in resources} <= ALLOWED_TYPES, "resource_type_not_allowed")
    require(len(resources) == text.count("\nresource "), "unparsed_resource")
    require(all(rest.startswith("if (provisioningApproved") for _, rest in resources), "ungated")
    for marker in FORBIDDEN:
        require(marker not in text, "forbidden_construct")
    for name in UNDEFAULTED:
        require(re.search(rf"^param {name} \w+$", text, re.M) is not None, "approval_param_default")
    tags = re.search(r"^var tags = \{(.*?)^\}", text, re.M | re.S)
    require(tags is not None, "tags_missing")
    assert tags is not None
    for tag in REQUIRED_TAGS:
        require(re.search(rf"^\s+{tag}:", tags.group(1), re.M) is not None, "tag_missing")
    require(text.count("tags: tags") >= 6, "untagged_resource")
    rules = re.findall(r"name: '(\w+)'\s*properties: \{(.*?)\n\s*\}", text, re.S)
    inbound = {name: body for name, body in rules if "direction: 'Inbound'" in body}
    deny = inbound.get("DenyInboundInternet", "")
    require(
        "access: 'Deny'" in deny
        and "sourceAddressPrefix: 'Internet'" in deny
        and "destinationPortRange: '*'" in deny,
        "inbound_deny",
    )
    require(all("access: 'Allow'" not in body for body in inbound.values()), "inbound_allow_rule")
    require("publicNetworkAccess: 'Disabled'" in text, "public_access")
    require("internal: true" in text, "environment_not_internal")
    require("enableRbacAuthorization: true" in text, "vault_rbac")
    require("accessPolicies: []" in text, "vault_access_policies")
    for threshold in (50, 80, 100):
        require(f"threshold: {threshold}," in text, "budget_threshold")
    return {"resources": len(resources), "resource_types": len({k for k, _ in resources})}


def validate_repository(root: Path) -> dict[str, object]:
    contract = load_contract(root / CONTRACT)
    validate_contract(contract)
    template = (root / TEMPLATE).read_text()
    result = validate_template(template)
    m23 = (root / M23_MAIN).read_text()
    require(M23_GATE in m23, "m23_gate_changed")
    return {
        "format": "azure-infrastructure-validation-check-v1",
        "status": "PASS",
        "provisioning": "REFUSED_PREPARATION_ONLY",
        "cloud_calls": 0,
        "m23_gate": "UNCHANGED_FALSE_ONLY",
        **result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline only: never logs in or deploys")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check-provisioning", action="store_true")
    args = parser.parse_args()
    try:
        if args.check_provisioning:
            refuse_provisioning(load_contract(args.root / CONTRACT))
        print(json.dumps(validate_repository(args.root), sort_keys=True))
    except (KeyError, ValueError, OSError, TypeError):
        parser.exit(78, "Infrastructure validation blocked or invalid; no cloud execution.\n")


if __name__ == "__main__":
    main()
