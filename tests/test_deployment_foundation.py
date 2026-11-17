"""Offline Stage A gates, security regressions and real local ASGI smoke; no Azure."""

import copy
import json
import shutil
import socket
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]  # Existing runtime parser; no new stub dependency.

ROOT = Path(__file__).resolve().parents[1]
# Tooling is shipped in the source archive, outside the installed application package.
# This adds only the tooling root, never ROOT/src; wheel application imports stay isolated.
sys.path.insert(0, str(ROOT))
from deployment.build_container import (  # noqa: E402
    artifact_path,
    build,
    file_hash,
    make_context,
    validate_inputs,
    wheel_metadata,
)
from deployment.containers.smoke import run  # noqa: E402
from deployment.foundation import (  # noqa: E402
    FoundationError,
    load,
    pins,
    refuse_deployment,
    validate_compiled,
    validate_contract,
    validate_repository,
)


@pytest.fixture
def isolated(tmp_path: Path) -> Path:
    for folder in ("infra/azure", "deployment", "requirements", ".github/workflows"):
        shutil.copytree(
            ROOT / folder, tmp_path / folder, ignore=shutil.ignore_patterns("__pycache__")
        )
    return tmp_path


def test_current_foundation_is_explicitly_disabled_and_reuses_all_dependency_pins() -> None:
    result = validate_repository(ROOT)
    assert result["status"] == "PASS" and result["cloud_validation"] == "NOT_TESTED"
    assert pins(ROOT / "requirements/m23-constraints.txt") == pins(
        ROOT / "requirements/m22-constraints.txt"
    )
    assert len(pins(ROOT / "requirements/m23-constraints.txt")) == 39


@pytest.mark.parametrize(
    "field,value",
    [
        ("cloud_execution_allowed", True),
        ("cloud_execution_allowed", 0),
        ("cloud_export_allowed", True),
        ("benchmark_released", True),
        ("model_calls_allowed", True),
        ("model_calls_allowed", 1),
        ("candidate_status", "APPROVED"),
        ("independent_quality_status", "PASS"),
        ("stage", "B"),
    ],
)
def test_cannot_promote_stage_quality_or_external_execution(field: str, value: object) -> None:
    contract = load(ROOT / "deployment/contract.json")
    contract[field] = value
    with pytest.raises(FoundationError):
        validate_contract(contract)


@pytest.mark.parametrize("environment", ["dev", "test", "prod"])
@pytest.mark.parametrize(
    "field,value",
    [
        ("deployment_enabled", True),
        ("max_replicas", 2),
        ("max_concurrency", True),
        ("monthly_budget_gbp", 100),
        ("tenant_id", "invented"),
        ("region_status", "VERIFIED"),
        ("data_boundary", "SHARED"),
    ],
)
def test_every_environment_fails_closed_on_unapproved_configuration(
    environment: str,
    field: str,
    value: object,
) -> None:
    contract = load(ROOT / "deployment/contract.json")
    contract["environments"][environment][field] = value
    with pytest.raises(FoundationError):
        validate_contract(contract)


def test_claimed_approvals_do_not_authorise_deployment() -> None:
    contract = load(ROOT / "deployment/contract.json")
    with pytest.raises(FoundationError, match="stage_a_cloud_execution_prohibited"):
        refuse_deployment(contract)
    contract["mandatory_gates"]["deployment"]["approval_identity"] = "not-a-real-approval"
    with pytest.raises(FoundationError, match="no_fabricated_approval"):
        refuse_deployment(contract)


def test_required_approval_gates_and_adapter_status_cannot_be_fabricated() -> None:
    value = load(ROOT / "deployment/contract.json")
    value["mandatory_gates"]["fake"] = value["mandatory_gates"].pop("budget")
    with pytest.raises(FoundationError, match="gate_inventory"):
        validate_contract(value)
    value = load(ROOT / "deployment/contract.json")
    value["adapter_status"]["entra"] = "IMPLEMENTED"
    with pytest.raises(FoundationError, match="adapter_status"):
        validate_contract(value)


@pytest.mark.parametrize(
    "file,old,new",
    [
        ("main", "@allowed([false])", "@allowed([true, false])"),
        ("modules/compute", "internal: true", "internal: false"),
        ("modules/compute", "publicNetworkAccess: 'Disabled'", "publicNetworkAccess: 'Enabled'"),
        ("modules/compute", "allowInsecure: false", "allowInsecure: true"),
        ("modules/compute", "@maxValue(1)", "@maxValue(10)"),
        ("modules/data", "if (deploymentEnabled)", "if (true)"),
        ("modules/data", "allowSharedKeyAccess: false", "allowSharedKeyAccess: true"),
        ("modules/data", "allowBlobPublicAccess: false", "allowBlobPublicAccess: true"),
        ("modules/data", "supportsHttpsTrafficOnly: true", "supportsHttpsTrafficOnly: false"),
        ("modules/data", "disableLocalAuth: true", "disableLocalAuth: false"),
        ("modules/data", "passwordAuth: 'Disabled'", "passwordAuth: 'Enabled'"),
        ("modules/identity", "enablePurgeProtection: true", "enablePurgeProtection: false"),
        ("modules/identity", "enableRbacAuthorization: true", "enableRbacAuthorization: false"),
        ("modules/registry", "adminUserEnabled: false", "adminUserEnabled: true"),
        ("modules/registry", "anonymousPullEnabled: false", "anonymousPullEnabled: true"),
        ("modules/identity", "defaultAction: 'Deny'", "defaultAction: 'Allow'"),
        ("modules/data", "bypass: 'None'", "bypass: 'AzureServices'"),
        ("modules/data", "minimumTlsVersion: 'TLS1_2'", "minimumTlsVersion: 'TLS1_0'"),
        (
            "modules/data",
            "deleteRetentionPolicy: { enabled: true, days: 30 }",
            "deleteRetentionPolicy: { enabled: false }",
        ),
        (
            "modules/data",
            "containerDeleteRetentionPolicy: { enabled: true, days: 30 }",
            "containerDeleteRetentionPolicy: { enabled: false }",
        ),
        ("modules/data", "scope: blobs", "scope: storage"),
        ("modules/data", "workspaceId: diagnosticWorkspaceId", "workspaceId: 'other-workspace'"),
        (
            "modules/data",
            "category: 'StorageRead', enabled: true",
            "category: 'StorageRead', enabled: false",
        ),
        (
            "modules/data",
            "category: 'StorageWrite', enabled: true",
            "category: 'StorageWrite', enabled: false",
        ),
        (
            "modules/data",
            "category: 'StorageDelete', enabled: true",
            "category: 'StorageDelete', enabled: false",
        ),
        ("main", "'${name}-logs'", "'other-environment-logs'"),
        ("main", "dependsOn: [monitoring]", "dependsOn: []"),
    ],
)
def test_iac_security_mutations_are_detected(isolated: Path, file: str, old: str, new: str) -> None:
    path = isolated / "infra/azure" / (file + ".bicep")
    assert old in path.read_text()
    path.write_text(path.read_text().replace(old, new, 1))
    with pytest.raises(FoundationError):
        validate_repository(isolated)


@pytest.mark.parametrize(
    "attack", ["automatic", "enabled", "oidc", "credentials", "action", "login"]
)
def test_workflow_cannot_activate_cloud_or_expand_credentials(isolated: Path, attack: str) -> None:
    path = isolated / ".github/workflows/m23-deploy.yml"
    value = load(path)
    if attack == "automatic":
        value["on"]["push"] = {}
    elif attack == "enabled":
        value["jobs"]["deploy"]["if"] = "${{ true }}"
    elif attack == "oidc":
        value["permissions"]["id-token"] = "write"
    elif attack == "credentials":
        value["jobs"]["preflight"]["steps"][0]["with"]["persist-credentials"] = True
    elif attack == "action":
        value["jobs"]["preflight"]["steps"][0]["uses"] = "actions/checkout@main"
    else:
        value["jobs"]["preflight"]["steps"].append({"run": "az login"})
    path.write_text(json.dumps(value))
    with pytest.raises(FoundationError):
        validate_repository(isolated)


def test_workflows_are_valid_yaml_without_implicit_boolean_on_keys() -> None:
    for path in (ROOT / ".github/workflows").glob("m23-*.yml"):
        assert yaml.safe_load(path.read_text()) == load(path)
        assert "on" in load(path)


def test_compiled_arm_guards_are_checked_without_calling_arm(tmp_path: Path) -> None:
    template: dict[str, Any] = {
        "parameters": {
            "deploymentEnabled": {"type": "bool", "allowedValues": [False], "defaultValue": False}
        },
        "resources": [
            {
                "type": "Microsoft.Resources/deployments",
                "condition": "[parameters('deploymentEnabled')]",
                "properties": {"parameters": {"deploymentEnabled": {"value": False}}},
            }
        ],
    }
    path = tmp_path / "compiled.json"
    path.write_text(json.dumps(template))
    assert validate_compiled(path)["enabled_resources"] == 0
    for value in (True, 0):
        changed = copy.deepcopy(template)
        changed["parameters"]["deploymentEnabled"]["allowedValues"] = [value]
        path.write_text(json.dumps(changed))
        with pytest.raises(FoundationError):
            validate_compiled(path)
    template["resources"][0]["properties"]["parameters"]["deploymentEnabled"]["value"] = True
    path.write_text(json.dumps(template))
    with pytest.raises(FoundationError, match="compiled_nested_module_disabled"):
        validate_compiled(path)


def test_pending_linux_inputs_cannot_reach_docker_or_create_a_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("pending inputs must not invoke Docker")

    monkeypatch.setattr(subprocess, "run", forbidden)
    manifest = ROOT / "deployment/containers/build-inputs.pending.json"
    with pytest.raises(FoundationError, match="linux_inputs_pending"):
        build(ROOT, manifest, tmp_path, file_hash(manifest))
    assert list(tmp_path.iterdir()) == []


def test_unpinned_build_manifest_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(FoundationError, match="independent_input_manifest_pin"):
        validate_inputs(
            ROOT, ROOT / "deployment/containers/build-inputs.pending.json", tmp_path, "0" * 64
        )


@pytest.mark.parametrize(
    "tag,extra,passes",
    [
        ("py3-none-any", None, True),
        ("cp312-cp312-manylinux_2_28_x86_64", None, True),
        ("cp39-abi3-manylinux_2_28_x86_64", None, True),
        ("cp312-cp312-macosx_11_0_arm64", None, False),
        ("cp313-cp313-manylinux_2_28_x86_64", None, False),
        ("py3-none-any", "../escape", False),
        ("py3-none-any", "code.pth", False),
    ],
)
def test_linux_wheel_metadata_and_archive_boundaries(
    tmp_path: Path,
    tag: str,
    extra: str | None,
    passes: bool,
) -> None:
    # Synthetic ZIP metadata only; never a real approved dependency or build lock.
    path = tmp_path / f"synthetic_test-0-{tag}.whl"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "synthetic_test-0.dist-info/METADATA",
            "Name: synthetic-test\nVersion: 0\nRequires-Python: >=3.12,<3.13\n",
        )
        archive.writestr(
            "synthetic_test-0.dist-info/WHEEL", "Wheel-Version: 1.0\nTag: " + tag + "\n"
        )
        if extra:
            archive.writestr(extra, "untrusted")
    if passes:
        assert wheel_metadata(path, (2, 28)) == ("synthetic-test", "0")
    else:
        with pytest.raises(FoundationError):
            wheel_metadata(path, (2, 28))


def test_artifact_hash_and_path_mismatch_fail_closed(tmp_path: Path) -> None:
    path = tmp_path / "synthetic.whl"
    path.write_bytes(b"synthetic test bytes, not an installable artifact")
    with pytest.raises(FoundationError, match="artifact_hash_mismatch"):
        artifact_path(tmp_path, {"file": path.name, "sha256": "0" * 64})
    with pytest.raises(FoundationError, match="artifact_basename"):
        artifact_path(tmp_path, {"file": "../synthetic.whl", "sha256": file_hash(path)})


def test_build_context_allowlist_excludes_labels_secrets_git_and_runtime_databases(
    tmp_path: Path,
) -> None:
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    wheel = artifacts / "synthetic.whl"
    wheel.write_bytes(b"synthetic context test; no Docker build")
    record = {"file": wheel.name, "sha256": file_hash(wheel)}
    target = tmp_path / "context"
    make_context(ROOT, {"dependency_wheels": [], "project_wheel": record}, artifacts, target)
    names = {str(p.relative_to(target)) for p in target.rglob("*") if p.is_file()}
    assert names == {
        "Dockerfile",
        ".dockerignore",
        "entrypoint.py",
        "smoke.py",
        "fixtures/manifest.json",
        "fixtures/specification.json",
        "fixtures/scenarios.json",
        "artifacts/requirements.txt",
        "artifacts/wheels/synthetic.whl",
    }
    assert all("m22" not in n and ".git" not in n and "sqlite" not in n for n in names)


def test_real_local_asgi_smoke_cannot_contact_external_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline smoke attempted network connection")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    result = run(ROOT / "data/rules/motor/v1")
    assert result["api_live"] == 200 and result["api_ready"] == 503
    assert result["api_missing_identity"] == 401 and result["mcp_tools"] == 3
    assert result["cloud_calls"] == result["model_calls"] == result["autonomous_outcomes"] == 0


@pytest.mark.parametrize("service", ["api-ui", "mcp"])
def test_cloud_entrypoint_and_healthcheck_never_become_ready(
    service: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("M23_CLOUD_EXECUTION", "enabled")
    monkeypatch.setenv("AZURE_CLIENT_SECRET", "synthetic-secret-must-not-be-read")
    for option in ([], ["--healthcheck"]):
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                str(ROOT / "deployment/containers/entrypoint.py"),
                "--service",
                service,
                *option,
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 78 and json.loads(result.stdout)["ready"] is False
        assert "synthetic-secret" not in result.stdout + result.stderr
