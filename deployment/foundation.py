"""Read-only offline foundation checks; no Azure SDK, credential chain or subprocess login."""

import argparse
import json
import re
from pathlib import Path
from typing import Any

MODULES = (
    "network",
    "identity",
    "registry",
    "data",
    "monitoring",
    "compute",
    "gateway",
    "private-endpoints",
)
CHECKOUT = "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
ENVIRONMENTS = {"dev", "test", "prod"}
GATES = {
    "scope",
    "region_residency_capacity",
    "budget",
    "identity_rbac",
    "private_network_dns",
    "linux_artifacts",
    "cloud_adapters",
    "migration_restore_rollback",
    "independent_quality_scope_exception",
    "github_environment_protection",
    "cloud_validation",
    "provisioning",
    "deployment",
    "teardown",
}


class FoundationError(ValueError):
    """Messages identify a fixed failed contract, never payload or credential details."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise FoundationError(code)


def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, "duplicate_json_key")
        result[key] = value
    return result


def load(path: Path) -> dict[str, Any]:
    require(not path.is_symlink() and path.is_file(), "configuration_unavailable")
    with path.open("rb") as stream:
        data = stream.read(1048577)
    require(len(data) <= 1048576, "configuration_capacity")
    value = json.loads(data, object_pairs_hook=unique)
    require(isinstance(value, dict), "configuration_shape")
    assert isinstance(value, dict)
    return value


def pins(path: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for line in path.read_text().splitlines():
        if line.startswith("-c "):
            result.update(pins(path.parent / line[3:]))
        elif "==" in line and not line.startswith("#"):
            name, version = line.split("==")
            result[name.lower().replace("_", "-")] = version
    return dict(sorted(result.items()))


def validate_contract(value: dict[str, Any]) -> None:
    require(value["format"] == "m23-offline-deployment-contract-v1", "contract_version")
    require(value["stage"] == "A", "stage")
    for key in ("cloud_execution_allowed", "cloud_export_allowed", "benchmark_released"):
        require(value[key] is False, "stage_a_execution_forbidden")
    require(
        type(value["model_calls_allowed"]) is int and value["model_calls_allowed"] == 0,
        "live_models_forbidden",
    )
    require(value["candidate_status"] == "PENDING_REVIEW", "holdout_guard")
    require(value["independent_quality_status"] == "NOT_TESTED", "quality_guard")
    require(set(value["environments"]) == ENVIRONMENTS, "environment_roster")
    for name, environment in value["environments"].items():
        require(environment["github_environment"] == "m23-" + name, "environment_identity")
        require(environment["data_boundary"] == "ISOLATED_" + name.upper(), "data_isolation")
        require(environment["deployment_enabled"] is False, "deployment_disabled")
        require(environment["region_status"] == "UNVERIFIED", "subscription_unverified")
        require(environment["region"] == "uksouth", "candidate_region")
        for field in ("max_replicas", "max_concurrency"):
            require(type(environment[field]) is int and environment[field] == 1, "capacity_cap")
        for field in (
            "subscription_id",
            "resource_group",
            "tenant_id",
            "owner",
            "expiry_utc",
            "monthly_budget_gbp",
            "experiment_budget_gbp",
            "runtime_hours",
        ):
            require(environment[field] is None, "unapproved_environment_value")
    require(set(value["mandatory_gates"]) == GATES, "gate_inventory")
    for gate in value["mandatory_gates"].values():
        require(gate["status"] == "PENDING_REVIEW", "unapproved_gate")
        require(
            all(gate[k] is None for k in ("approval_identity", "approval_time", "evidence_sha256")),
            "no_fabricated_approval",
        )
    require(
        set(value["adapter_status"])
        == {
            "cloud_host",
            "entra",
            "canonical_session_store",
            "postgres",
            "blob",
            "service_bus",
            "cloud_telemetry",
        }
        and set(value["adapter_status"].values()) == {"NOT_IMPLEMENTED"},
        "adapter_status",
    )
    require(
        set(value["optional_services"])
        == {
            "foundry",
            "document_intelligence",
            "ai_search",
            "content_safety",
            "live_models",
        },
        "optional_service_inventory",
    )
    require(
        all(
            v["enabled"] is False and v["resources"] == "NOT_DEFINED"
            for v in value["optional_services"].values()
        ),
        "optional_service_disabled",
    )


def refuse_deployment(value: dict[str, Any]) -> None:
    validate_contract(value)
    # Even editing an approval/status string cannot activate Stage A cloud execution.
    raise FoundationError("stage_a_cloud_execution_prohibited")


def validate_workflows(root: Path) -> None:
    for name in ("m23-validate.yml", "m23-deploy.yml"):
        workflow = load(root / ".github/workflows" / name)  # JSON-compatible YAML, stdlib only.
        require(workflow["permissions"] == {"contents": "read"}, "workflow_permissions")
        require("pull_request_target" not in workflow["on"], "unsafe_workflow_trigger")
        for job in workflow["jobs"].values():
            require(job["timeout-minutes"] <= 10, "workflow_timeout")
            for step in job.get("steps", []):
                if "uses" in step:
                    require(step["uses"] == CHECKOUT, "pinned_reviewed_action")
                    require(step["with"]["persist-credentials"] is False, "checkout_credentials")
                command = step.get("run", "").lower()
                require(
                    not any(
                        s in command
                        for s in (
                            "azure/login",
                            "az ",
                            "new-az",
                            "docker push",
                            "curl ",
                            "wget ",
                            "pip install",
                            "bicep publish",
                            "what-if",
                        )
                    ),
                    "no_cloud_or_download_step",
                )
        if name == "m23-deploy.yml":
            require(set(workflow["on"]) == {"workflow_dispatch"}, "manual_deployment_only")
            job = workflow["jobs"]["deploy"]
            require(job["if"] == "${{ false }}", "hard_disabled_deployment_job")
            require(job["environment"] == "m23-${{ inputs.environment }}", "protected_environment")
            require(
                job["permissions"] == {"contents": "read", "id-token": "write"},
                "future_job_only_oidc",
            )
            require(
                job["steps"] == [{"name": "Stage A refuses cloud execution", "run": "exit 78"}],
                "no_live_deployment_action",
            )


def validate_repository(root: Path) -> dict[str, object]:
    validate_contract(load(root / "deployment/contract.json"))
    require(
        pins(root / "requirements/m23-constraints.txt")
        == pins(root / "requirements/m22-constraints.txt"),
        "dependency_closure_unchanged",
    )
    require(len(pins(root / "requirements/m23-constraints.txt")) == 39, "runtime_pin_count")
    for path in [
        root / "infra/azure/main.bicep",
        *(root / "infra/azure/modules" / (name + ".bicep") for name in MODULES),
    ]:
        text = path.read_text()
        code = re.sub(r"//[^\n]*", "", text)
        require(
            "@allowed([false])\nparam deploymentEnabled bool = false" in code,
            "bicep_unconditionally_disabled_parameter",
        )
        # Formatter may put array comprehensions on a separate line. Inspect each
        # declaration header up to its first body brace, not arbitrary body text.
        for declaration in re.finditer(r"^\s*(resource|module)\s+(.+?)\{", code, re.M | re.S):
            header = declaration.group(2)
            require(
                "existing" in header or "if (deploymentEnabled)" in header,
                "unguarded_infrastructure",
            )
        require(
            not any(
                v in code
                for v in (
                    "Microsoft.CognitiveServices/",
                    "Microsoft.Search/",
                    "Microsoft.Authorization/roleAssignments",
                )
            ),
            "no_ai_or_iam_activation",
        )
    for environment in ENVIRONMENTS:
        text = (root / "infra/azure/environments" / (environment + ".bicepparam")).read_text()
        require("param deploymentEnabled = false" in text, "environment_parameters_disabled")
        require("param environment = '" + environment + "'" in text, "separate_parameters")
    compute = (root / "infra/azure/modules/compute.bicep").read_text()
    require(
        "internal: true" in compute and "publicNetworkAccess: 'Disabled'" in compute,
        "private_container_environment",
    )
    require("allowInsecure: false" in compute, "tls_required")
    require("@maxValue(1)" in compute and "maxReplicas: maxReplicas" in compute, "replica_limit")
    require("/health/ready" in compute and "/health/live" in compute, "health_contracts")
    for module in ("data", "identity", "registry", "monitoring", "gateway"):
        text = (root / "infra/azure/modules" / (module + ".bicep")).read_text()
        require("publicNetworkAccess: 'Enabled'" not in text, "public_access_forbidden")
        require(
            "'Disabled'" in text,
            "public_network_disabled",
        )
    data = (root / "infra/azure/modules/data.bicep").read_text()
    for invariant in (
        "allowSharedKeyAccess: false",
        "allowBlobPublicAccess: false",
        "supportsHttpsTrafficOnly: true",
        "disableLocalAuth: true",
        "passwordAuth: 'Disabled'",
        "minimumTlsVersion: 'TLS1_2'",
        "bypass: 'None', defaultAction: 'Deny'",
        "deleteRetentionPolicy: { enabled: true, days: 30 }",
        "containerDeleteRetentionPolicy: { enabled: true, days: 30 }",
    ):
        require(invariant in data, "data_authentication_boundary")
    for invariant in (
        "resource blobDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview'"
        " = if (deploymentEnabled)",
        "scope: blobs",
        "workspaceId: diagnosticWorkspaceId",
        "logAnalyticsDestinationType: 'Dedicated'",
        "{ category: 'StorageRead', enabled: true }",
        "{ category: 'StorageWrite', enabled: true }",
        "{ category: 'StorageDelete', enabled: true }",
    ):
        require(invariant in data, "blob_diagnostics_boundary")
    main = (root / "infra/azure/main.bicep").read_text()
    require(
        "diagnosticWorkspaceId: resourceId('Microsoft.OperationalInsights/workspaces', "
        "'${name}-logs')"
        in main
        and "dependsOn: [monitoring]" in main,
        "same_environment_diagnostic_destination",
    )
    identity = (root / "infra/azure/modules/identity.bicep").read_text()
    require(
        "enableRbacAuthorization: true" in identity and "enablePurgeProtection: true" in identity,
        "key_custody_boundary",
    )
    require(
        "networkAcls: { bypass: 'None', defaultAction: 'Deny' }" in identity,
        "vault_default_deny",
    )
    registry = (root / "infra/azure/modules/registry.bicep").read_text()
    require(
        "adminUserEnabled: false" in registry and "anonymousPullEnabled: false" in registry,
        "registry_authentication_boundary",
    )
    docker = (root / "deployment/containers/Dockerfile").read_text()
    for invariant in (
        "FROM ${PYTHON_BASE}",
        "--network=none",
        "--no-index",
        "--require-hashes",
        "--no-deps",
        "USER 10001:10001",
        "HEALTHCHECK",
        "--healthcheck",
    ):
        require(invariant in docker, "container_security_contract")
    require("ARG PYTHON_BASE=" not in docker and "ADD " not in docker, "no_mutable_base_or_add")
    require(
        all(
            line.split()[1] == "${PYTHON_BASE}"
            for line in docker.splitlines()
            if line.startswith("FROM ")
        ),
        "every_base_content_addressed",
    )
    validate_workflows(root)
    return {
        "format": "m23-static-foundation-check-v1",
        "status": "PASS",
        "cloud_execution": "DISABLED",
        "runtime_distributions": 39,
        "bicep_modules": len(MODULES),
        "environments": sorted(ENVIRONMENTS),
        "adapters": "NOT_IMPLEMENTED",
        "cloud_validation": "NOT_TESTED",
    }


def validate_compiled(path: Path) -> dict[str, object]:
    template = load(path)
    parameter = template["parameters"]["deploymentEnabled"]
    require(
        parameter["type"] == "bool"
        and len(parameter["allowedValues"]) == 1
        and parameter["allowedValues"][0] is False
        and parameter["defaultValue"] is False,
        "compiled_parameter_cannot_enable",
    )
    resources = template.get("resources", [])
    require(isinstance(resources, list) and bool(resources), "compiled_resource_shape")
    for resource in resources:
        require(
            resource["condition"] == "[parameters('deploymentEnabled')]", "compiled_resource_guard"
        )
        if resource["type"].lower() == "microsoft.resources/deployments":
            require(
                resource["properties"]["parameters"]["deploymentEnabled"]["value"] is False,
                "compiled_nested_module_disabled",
            )
    return {
        "status": "PASS",
        "declared_top_level_resources": len(resources),
        "enabled_resources": 0,
        "azure_validation": "NOT_TESTED",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline only: never logs in or deploys")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--check-deployment", action="store_true")
    parser.add_argument("--compiled", type=Path)
    args = parser.parse_args()
    try:
        if args.check_deployment:
            refuse_deployment(load(args.root / "deployment/contract.json"))
        result = (
            validate_compiled(args.compiled) if args.compiled else validate_repository(args.root)
        )
        print(json.dumps(result, sort_keys=True))
    except (KeyError, ValueError, OSError, TypeError):
        parser.exit(78, "M23 Stage A operation blocked or invalid; no cloud execution.\n")


if __name__ == "__main__":
    main()
