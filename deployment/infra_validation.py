"""Offline checks for the infrastructure-only Azure validation template (Option C).

Reads local files only: no Azure SDK, credential chain, subprocess, network or deployment.
The repository template's hard gate permits only ``false`` in every contract state. A
hash-bound execution copy may be authorised for ARM validation/what-if, and separately for
one provisioning window, only by a fully approved contract. Teardown output is a plan for
owner execution; nothing here deletes, deploys or calls Azure.
"""

import argparse
import hashlib
import json
import re
from datetime import UTC, datetime
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
# The optional Container Apps environment must stay off: what-if expects exactly these seven.
DEPLOYED_TYPES = {t.lower() for t in ALLOWED_TYPES} - {"microsoft.app/managedenvironments"}
PROTECTED_GROUPS = {"rg-claims-agentic-ai-dev"}
NAME_PREFIX = "nsval-"
APPROVALS = {
    "budget",
    "cloud_validation",
    "cost_exposure",
    "evidence",
    "execution_template",
    "identity_rbac",
    "network",
    "provider_registration",
    "provisioning",
    "region_capacity",
    "scope",
    "teardown",
}
CHECKLIST = (
    (1, "scope_region_identity_network", ("scope", "region_capacity", "identity_rbac", "network")),
    (2, "cost_exposure_acceptance", ("cost_exposure",)),
    (3, "provider_registration", ("provider_registration",)),
    (4, "budget_values", ("budget",)),
    (5, "execution_template_gate_copy", ("execution_template",)),
    (6, "arm_validate_and_what_if", ("cloud_validation",)),
    (7, "provisioning_window", ("provisioning",)),
    (8, "teardown", ("teardown",)),
    (9, "evidence_record", ("evidence",)),
)
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
EXECUTION_KEYS = {
    "approved_parameters_sha256",
    "approved_template_sha256",
    "approved_whatif_sha256",
    "resource_group",
    "reviewed_template_sha256",
    "run_id",
    "window_end_utc",
    "window_start_utc",
}
PREPARATION = "PREPARATION_ONLY"
VALIDATION = "APPROVED_FOR_VALIDATION"
EXECUTION = "APPROVED_FOR_EXECUTION_WINDOW"
STATUSES = {PREPARATION, VALIDATION, EXECUTION}
MAX_WINDOW_SECONDS = 2 * 3600
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
    "checklist",
    "execution",
    "format",
    "notes",
    "proposed_max_lifetime_hours",
    "provisioning_allowed",
    "restrictions",
    "scope",
    "status",
}
# Template parameter -> contract approved value.
PARAMETER_VALUES = {
    "location": "location",
    "owner": "owner",
    "expiresAt": "expires_at",
    "budgetAmount": "budget_amount",
    "budgetContactEmails": "budget_contact_emails",
    "budgetStartDate": "budget_start_date",
    "budgetEndDate": "budget_end_date",
    "logDailyQuotaGb": "log_daily_quota_gb",
    "includeContainerEnvironment": "include_container_environment",
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
SHA256 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(ValueError):
    """Fixed failure code; never contains file contents or credentials."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise ValidationError(code)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def _json(data: bytes, code: str) -> dict[str, Any]:
    require(len(data) <= 4194304, code + "_capacity")
    value = json.loads(data, object_pairs_hook=_unique)
    require(isinstance(value, dict), code + "_shape")
    assert isinstance(value, dict)
    return value


def load_contract(path: Path) -> dict[str, Any]:
    require(not path.is_symlink() and path.is_file(), "contract_unavailable")
    data = path.read_bytes()
    require(len(data) <= 262144, "contract_capacity")
    return _json(data, "contract")


def _approval_ok(record: dict[str, Any]) -> bool:
    return (
        record["status"] == "APPROVED"
        and isinstance(record["approval_identity"], str)
        and bool(record["approval_identity"])
        and isinstance(record["approval_time"], str)
        and bool(record["approval_time"])
        and isinstance(record["evidence_sha256"], str)
        and SHA256.match(record["evidence_sha256"]) is not None
    )


def validate_contract(value: dict[str, Any]) -> None:
    require(set(value) == CONTRACT_KEYS, "contract_keys")
    require(value["format"] == "azure-infrastructure-validation-contract-v2", "contract_format")
    status = value["status"]
    require(status in STATUSES, "contract_status")
    # Default deny: only the execution-window state may allow provisioning.
    if status == EXECUTION:
        require(value["provisioning_allowed"] is True, "provisioning_flag_inconsistent")
    else:
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
        if record["status"] == "PENDING":
            require(
                all(
                    record[k] is None
                    for k in ("approval_identity", "approval_time", "evidence_sha256")
                ),
                "pending_approval_has_values",
            )
        else:
            require(_approval_ok(record), "approval_incomplete_record")
    checklist = value["checklist"]
    require(isinstance(checklist, list) and len(checklist) == len(CHECKLIST), "checklist_shape")
    for item, (stage, name, keys) in zip(checklist, CHECKLIST, strict=True):
        require(
            isinstance(item, dict)
            and item.get("stage") == stage
            and item.get("name") == name
            and tuple(item.get("approvals", ())) == keys
            and set(item) == {"stage", "name", "approvals"},
            "checklist_mapping",
        )
    mapped = [k for _, _, keys in CHECKLIST for k in keys]
    require(sorted(mapped) == sorted(APPROVALS), "checklist_coverage")
    execution = value["execution"]
    require(isinstance(execution, dict) and set(execution) == EXECUTION_KEYS, "execution_keys")
    if status == PREPARATION:
        require(all(v is None for v in execution.values()), "preparation_execution_must_be_null")
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
    """Always refuses: the repository template is false-only and never deployable."""
    validate_contract(value)
    raise ValidationError("provisioning_refused_preparation_only")


def _require_stages(contract: dict[str, Any], last_stage: int) -> None:
    for stage, _, keys in CHECKLIST:
        if stage <= last_stage:
            for key in keys:
                require(_approval_ok(contract["approvals"][key]), f"approval_incomplete:{key}")


def resource_type(resource_id: str) -> str:
    """Full lower-case ARM type of the LAST resource in an ID, including child segments.

    ``.../providers/NS/t1/n1/t2/n2`` gives ``ns/t1/t2``; extension resources use the last
    ``/providers/`` segment, so diagnostic settings and budgets resolve to their own type.
    """
    parts = [p for p in resource_id.split("/") if p]
    lowered = [p.lower() for p in parts]
    require("providers" in lowered, "not_a_provider_resource_id")
    index = len(lowered) - 1 - lowered[::-1].index("providers")
    tail = parts[index + 1 :]
    require(len(tail) >= 3 and len(tail) % 2 == 1, "malformed_resource_id")
    return "/".join([tail[0], *tail[1::2]]).lower()


def _resource_group_of(resource_id: str) -> str:
    parts = [p for p in resource_id.split("/") if p]
    lowered = [p.lower() for p in parts]
    require("resourcegroups" in lowered, "resource_outside_group")
    return parts[lowered.index("resourcegroups") + 1].lower()


def check_whatif(whatif: dict[str, Any], resource_group: str) -> list[str]:
    """Exactly one Create per deployed type, in the approved group, with expected identities."""
    changes = whatif.get("changes")
    require(isinstance(changes, list), "whatif_shape")
    assert isinstance(changes, list)
    seen: dict[str, str] = {}
    for change in changes:
        require(isinstance(change, dict), "whatif_shape")
        rid = change.get("resourceId", "")
        require(isinstance(rid, str) and bool(rid), "whatif_shape")
        kind = resource_type(rid)
        require(change.get("changeType") == "Create", f"unexpected_change_type:{kind}")
        require(kind in DEPLOYED_TYPES, f"unexpected_type:{kind}")
        require(kind not in seen, f"duplicate_type:{kind}")
        require(_resource_group_of(rid) == resource_group.lower(), "wrong_resource_group")
        name = rid.rstrip("/").split("/")[-1]
        if kind == "microsoft.insights/diagnosticsettings":
            parent = rid.lower().split("/providers/microsoft.insights/")[0]
            require(
                name == "vault-audit" and resource_type(parent) == "microsoft.keyvault/vaults",
                "diagnostic_setting_target",
            )
        elif kind == "microsoft.keyvault/vaults":
            require(name.startswith(NAME_PREFIX.replace("-", "")), "vault_name")
        else:
            require(name.startswith(NAME_PREFIX), f"name_prefix:{kind}")
        seen[kind] = rid
    require(set(seen) == DEPLOYED_TYPES, "missing_types")
    return sorted(seen.values())


def validate_compiled_reviewed(doc: dict[str, Any]) -> None:
    """The reviewed compiled template: false-only gate and every resource conditioned on it."""
    gate = doc.get("parameters", {}).get("provisioningApproved", {})
    require(
        gate.get("type") == "bool"
        and gate.get("defaultValue") is False
        and gate.get("allowedValues") == [False],
        "reviewed_gate_not_false_only",
    )
    resources = doc.get("resources", [])
    items = list(resources.values()) if isinstance(resources, dict) else list(resources)
    require(len(items) == len(ALLOWED_TYPES), "reviewed_resource_count")
    require({r.get("type") for r in items} == ALLOWED_TYPES, "reviewed_resource_types")
    require(
        all("parameters('provisioningApproved')" in str(r.get("condition", "")) for r in items),
        "reviewed_resource_ungated",
    )


def gate_only_difference(reviewed: dict[str, Any], execution: dict[str, Any]) -> bool:
    """The execution copy may differ from the reviewed template ONLY in the gate's allowedValues."""
    a = json.loads(json.dumps(reviewed))
    b = json.loads(json.dumps(execution))
    for doc in (a, b):
        doc.get("metadata", {}).pop("_generator", None)  # compiler stamp only
    gate_a = a.get("parameters", {}).get("provisioningApproved", {})
    gate_b = b.get("parameters", {}).get("provisioningApproved", {})
    if gate_a.get("allowedValues") != [False] or gate_b.get("allowedValues") != [False, True]:
        return False
    gate_a.pop("allowedValues")
    gate_b.pop("allowedValues")
    return bool(a == b)


def _bind_artifacts(
    contract: dict[str, Any], reviewed: bytes, execution: bytes, parameters: bytes
) -> dict[str, str]:
    ex = contract["execution"]
    values = contract["approved_values"]
    require(all(v is not None for v in values.values()), "approved_values_incomplete")
    group = values["resource_group"]
    require(
        isinstance(group, str) and group not in PROTECTED_GROUPS, "resource_group_not_permitted"
    )
    require(ex["resource_group"] == group and bool(ex["run_id"]), "execution_identity")
    require(sha256(reviewed) == ex["reviewed_template_sha256"], "reviewed_template_hash_mismatch")
    require(sha256(execution) == ex["approved_template_sha256"], "template_hash_mismatch")
    reviewed_doc = _json(reviewed, "reviewed_template")
    execution_doc = _json(execution, "execution_template")
    validate_compiled_reviewed(reviewed_doc)
    require(gate_only_difference(reviewed_doc, execution_doc), "template_differs_beyond_gate")
    require(sha256(parameters) == ex["approved_parameters_sha256"], "parameters_hash_mismatch")
    supplied = _json(parameters, "parameters").get("parameters")
    require(isinstance(supplied, dict), "parameters_shape")
    assert isinstance(supplied, dict)
    plain = {k: v.get("value") if isinstance(v, dict) else None for k, v in supplied.items()}
    require(set(plain) == set(PARAMETER_VALUES) | {"provisioningApproved"}, "parameter_set")
    for parameter, key in PARAMETER_VALUES.items():
        require(plain[parameter] == values[key], f"parameter_not_approved:{parameter}")
    require(plain["includeContainerEnvironment"] is False, "parameter_scope")
    require(plain["provisioningApproved"] is True, "parameter_gate")
    return {"run_id": str(ex["run_id"]), "resource_group": group}


def authorize_validation(
    contract: dict[str, Any], reviewed: bytes, execution: bytes, parameters: bytes
) -> dict[str, str]:
    """ARM validate/what-if only (stages 1-6). Never authorises provisioning."""
    validate_contract(contract)
    require(contract["status"] in (VALIDATION, EXECUTION), "contract_not_approved_for_validation")
    _require_stages(contract, 6)
    bound = _bind_artifacts(contract, reviewed, execution, parameters)
    return {**bound, "decision": "AUTHORIZED_FOR_VALIDATION_ONLY", "provisioning": "NOT_AUTHORIZED"}


def authorize_execution(
    contract: dict[str, Any],
    reviewed: bytes,
    execution: bytes,
    parameters: bytes,
    whatif: bytes,
    now: datetime,
) -> dict[str, str]:
    """One provisioning window (stages 1-8) bound to the exact template, parameters and what-if."""
    validate_contract(contract)
    require(contract["status"] == EXECUTION, "contract_not_approved_for_execution")
    _require_stages(contract, 8)
    bound = _bind_artifacts(contract, reviewed, execution, parameters)
    ex = contract["execution"]
    require(sha256(whatif) == ex["approved_whatif_sha256"], "whatif_hash_mismatch")
    check_whatif(_json(whatif, "whatif"), bound["resource_group"])
    start = datetime.fromisoformat(ex["window_start_utc"])
    end = datetime.fromisoformat(ex["window_end_utc"])
    expires = datetime.fromisoformat(contract["approved_values"]["expires_at"])
    require(0 < (end - start).total_seconds() <= MAX_WINDOW_SECONDS, "window_too_long")
    require(end <= expires, "window_beyond_expiry")
    require(start <= now <= end, "outside_execution_window")
    return {**bound, "decision": "AUTHORIZED_FOR_WINDOW", "window_end_utc": end.isoformat()}


def plan_teardown(contract: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    """Ordered teardown PLAN for owner execution, or a refusal for manual review. Never guesses."""
    validate_contract(contract)
    require(_approval_ok(contract["approvals"]["teardown"]), "approval_incomplete:teardown")
    ex = contract["execution"]
    group_name, run_id = ex["resource_group"], ex["run_id"]
    require(isinstance(group_name, str) and isinstance(run_id, str), "execution_identity")
    require(group_name not in PROTECTED_GROUPS, "protected_group")
    group = state.get("group")
    if group is None:
        return {
            "decision": "VERIFY_ONLY",
            "actions": ["VERIFY:group_absent"],
            "resource_group": group_name,
        }
    require(isinstance(group, dict) and group.get("name") == group_name, "group_name_mismatch")
    tags = group.get("tags") or {}
    require(
        tags.get("purpose") == "infrastructure-validation" and tags.get("infravalRun") == run_id,
        "group_not_created_by_this_run",
    )
    require(not group.get("locks"), "group_has_locks")
    if state.get("deployment_state") in ("Running", "Accepted"):
        return {"decision": "CANCEL_FIRST", "actions": ["CANCEL_DEPLOYMENT_THEN_REPLAN"]}
    resources = state.get("resources", [])
    require(isinstance(resources, list), "resources_shape")
    by_type: dict[str, list[str]] = {}
    for item in resources:
        kind = resource_type(item["id"])
        require(kind in DEPLOYED_TYPES, f"unexpected_resource:{kind}")
        require(_resource_group_of(item["id"]) == group_name.lower(), "resource_outside_group")
        require(
            (item.get("tags") or {}).get("purpose") == "infrastructure-validation",
            "untagged_resource",
        )
        by_type.setdefault(kind, []).append(item["id"].rstrip("/").split("/")[-1])
    recorded = state.get("deployment_ids")
    if recorded is not None:
        known = {i.lower() for i in recorded}
        require({r["id"].lower() for r in resources} <= known, "resource_not_in_deployment_record")
    require(all(len(v) == 1 for v in by_type.values()), "ambiguous_target")
    budgets = state.get("budgets", [])
    require(isinstance(budgets, list) and len(budgets) <= 1, "ambiguous_budget")
    actions = ["CAPTURE_EVIDENCE"]
    if budgets:
        require(str(budgets[0]).startswith(NAME_PREFIX), "budget_name")
        actions.append(f"DELETE_BUDGET:{budgets[0]}")
    workspace = by_type.get("microsoft.operationalinsights/workspaces")
    if workspace:
        actions.append(f"FORCE_DELETE_WORKSPACE:{workspace[0]}")
    actions.append(f"DELETE_GROUP:{group_name}")
    vault = by_type.get("microsoft.keyvault/vaults")
    if vault:
        actions.append(f"VERIFY_PURGE_TARGET_THEN_PURGE_VAULT:{vault[0]}")
    actions.append("VERIFY")
    return {
        "decision": "TEARDOWN_PLAN_ONLY",
        "requires_owner_execution": True,
        "resource_group": group_name,
        "run_id": run_id,
        "actions": actions,
    }


def verify_purge_target(contract: dict[str, Any], vault: str, deleted_vault_id: str) -> str:
    """Purge only a soft-deleted vault whose original ID is exactly in the approved group."""
    validate_contract(contract)
    require(_approval_ok(contract["approvals"]["teardown"]), "approval_incomplete:teardown")
    group = contract["execution"]["resource_group"]
    require(isinstance(group, str) and group not in PROTECTED_GROUPS, "protected_group")
    require(resource_type(deleted_vault_id) == "microsoft.keyvault/vaults", "purge_not_a_vault")
    require(_resource_group_of(deleted_vault_id) == group.lower(), "purge_wrong_group")
    require(
        deleted_vault_id.rstrip("/").split("/")[-1].lower() == vault.lower(), "purge_wrong_name"
    )
    return "PURGE_TARGET_VERIFIED"


_resource_blocks_pattern = re.compile(
    r"^resource \w+ '([A-Za-z.]+/[A-Za-z/]+)@[0-9a-z-]+' = (.*)$", re.M
)


def _resource_blocks(text: str) -> list[tuple[str, str]]:
    return [(kind, rest) for kind, rest in _resource_blocks_pattern.findall(text)]


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
    result = validate_template(template)  # repository gate is false-only in EVERY state
    m23 = (root / M23_MAIN).read_text()
    require(M23_GATE in m23, "m23_gate_changed")
    return {
        "format": "azure-infrastructure-validation-check-v2",
        "status": "PASS",
        "contract_status": contract["status"],
        "provisioning": "REFUSED_PREPARATION_ONLY"
        if contract["status"] == PREPARATION
        else "REPOSITORY_TEMPLATE_NOT_DEPLOYABLE",
        "repository_gate": "FALSE_ONLY",
        "cloud_calls": 0,
        "m23_gate": "UNCHANGED_FALSE_ONLY",
        **result,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline only: never logs in, deploys or deletes")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--check-provisioning", action="store_true")
    parser.add_argument("--authorize-validation", action="store_true")
    parser.add_argument("--authorize-execution", action="store_true")
    parser.add_argument("--check-whatif", type=Path)
    parser.add_argument("--plan-teardown", type=Path, help="state JSON exported by the owner")
    parser.add_argument("--verify-purge", nargs=2, metavar=("VAULT", "DELETED_VAULT_ID"))
    parser.add_argument("--reviewed-template", type=Path)
    parser.add_argument("--execution-template", type=Path)
    parser.add_argument("--parameters", type=Path)
    parser.add_argument("--whatif", type=Path)
    args = parser.parse_args()
    contract_path = args.contract or args.root / CONTRACT
    try:
        if args.check_provisioning:
            refuse_provisioning(load_contract(args.root / CONTRACT))
        if args.authorize_validation or args.authorize_execution:
            contract = load_contract(contract_path)
            artifacts = (
                args.reviewed_template.read_bytes(),
                args.execution_template.read_bytes(),
                args.parameters.read_bytes(),
            )
            result: object = (
                authorize_execution(
                    contract, *artifacts, args.whatif.read_bytes(), datetime.now(UTC)
                )
                if args.authorize_execution
                else authorize_validation(contract, *artifacts)
            )
        elif args.check_whatif:
            contract = load_contract(contract_path)
            group = contract["approved_values"]["resource_group"]
            require(isinstance(group, str), "resource_group_not_approved")
            result = check_whatif(_json(args.check_whatif.read_bytes(), "whatif"), group)
        elif args.plan_teardown:
            state = _json(args.plan_teardown.read_bytes(), "state")
            result = plan_teardown(load_contract(contract_path), state)
        elif args.verify_purge:
            result = verify_purge_target(load_contract(contract_path), *args.verify_purge)
        else:
            result = validate_repository(args.root)
        print(json.dumps(result, sort_keys=True))
    except (KeyError, ValueError, OSError, TypeError, AttributeError):
        parser.exit(78, "Infrastructure validation blocked or invalid; no cloud execution.\n")


if __name__ == "__main__":
    main()
