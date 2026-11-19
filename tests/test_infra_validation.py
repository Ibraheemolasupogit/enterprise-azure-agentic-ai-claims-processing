"""Offline checks for the infrastructure-only Azure validation template (no Azure calls)."""

import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deployment.infra_validation import (  # noqa: E402
    CONTRACT,
    M23_MAIN,
    TEMPLATE,
    ValidationError,
    load_contract,
    refuse_provisioning,
    validate_contract,
    validate_repository,
    validate_template,
)


@pytest.fixture
def isolated(tmp_path: Path) -> Path:
    for relative in (TEMPLATE, CONTRACT, M23_MAIN):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    return tmp_path


def contract() -> dict[str, Any]:
    return load_contract(ROOT / CONTRACT)


def test_current_template_and_contract_pass_and_never_provision() -> None:
    result = validate_repository(ROOT)
    assert result["status"] == "PASS" and result["cloud_calls"] == 0
    assert result["provisioning"] == "REFUSED_PREPARATION_ONLY"
    assert result["m23_gate"] == "UNCHANGED_FALSE_ONLY"
    with pytest.raises(ValidationError, match="provisioning_refused_preparation_only"):
        refuse_provisioning(contract())


def test_fabricated_approvals_and_values_still_cannot_provision() -> None:
    value = contract()
    for record in value["approvals"].values():
        record.update(
            approval_identity="someone", approval_time="2026-11-19T00:00:00Z", status="APPROVED"
        )
    value["approved_values"]["budget_amount"] = 10
    with pytest.raises(ValidationError, match="provisioning_refused_preparation_only"):
        refuse_provisioning(value)


@pytest.mark.parametrize(
    ("path", "new", "code"),
    [
        (("provisioning_allowed",), True, "provisioning_must_be_false"),
        (("status",), "APPROVED", "contract_status"),
        (("scope", "public_ingress"), True, "scope_must_exclude_workloads"),
        (("scope", "container_images"), True, "scope_must_exclude_workloads"),
        (("scope", "claims_data"), True, "scope_must_exclude_workloads"),
        (("proposed_max_lifetime_hours",), 168, "lifetime_bound"),
        (("proposed_max_lifetime_hours",), True, "lifetime_type"),
        (("restrictions", "m23"), "REOPENED", "m23_restriction"),
    ],
)
def test_contract_cannot_widen_scope_or_claim_authority(
    path: tuple[str, ...], new: object, code: str
) -> None:
    value = contract()
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = new
    with pytest.raises(ValidationError, match=code):
        validate_contract(value)


def test_contract_rejects_extra_resource_types_and_unknown_keys() -> None:
    value = contract()
    value["allowed_resource_types"].append("Microsoft.Network/publicIPAddresses")
    with pytest.raises(ValidationError, match="resource_allowlist"):
        validate_contract(value)
    value = contract()
    value["deploy_now"] = True
    with pytest.raises(ValidationError, match="contract_keys"):
        validate_contract(value)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "contract.json"
    path.write_text('{"status": "PREPARATION_ONLY", "status": "APPROVED"}')
    with pytest.raises(ValidationError, match="duplicate_json_key"):
        load_contract(path)


TEXT = (ROOT / TEMPLATE).read_text()


@pytest.mark.parametrize(
    ("old", "new", "code"),
    [
        (
            "@allowed([false])\nparam provisioningApproved",
            "@allowed([true, false])\nparam provisioningApproved",
            "hard_gate_missing",
        ),
        ("param owner string\n", "param owner string = 'nobody'\n", "approval_param_default"),
        ("param budgetAmount int\n", "param budgetAmount int = 100\n", "approval_param_default"),
        (
            "param location string\n",
            "param location string = 'uksouth'\n",
            "approval_param_default",
        ),
        ("  purpose: 'infrastructure-validation'\n", "", "tag_missing"),
        (
            "publicNetworkAccess: 'Disabled'\n    networkAcls",
            "publicNetworkAccess: 'Enabled'\n    networkAcls",
            "forbidden_construct",
        ),
        ("internal: true", "internal: false", "environment_not_internal"),
        (
            "softDeleteRetentionInDays: 7",
            "enablePurgeProtection: true\n    softDeleteRetentionInDays: 7",
            "forbidden_construct",
        ),
        ("threshold: 80,", "threshold: 95,", "budget_threshold"),
        ("access: 'Deny'", "access: 'Allow'", "inbound_deny"),
        (
            "direction: 'Outbound'\n          access: 'Deny'",
            "direction: 'Inbound'\n          access: 'Allow'",
            "inbound_allow_rule",
        ),
        (
            "= if (provisioningApproved) {\n  name: '${name}-id'",
            "= {\n  name: '${name}-id'",
            "ungated",
        ),
    ],
)
def test_template_security_mutations_fail_closed(old: str, new: str, code: str) -> None:
    assert TEXT.count(old) >= 1, old
    with pytest.raises(ValidationError, match=code):
        validate_template(TEXT.replace(old, new, 1))


@pytest.mark.parametrize(
    "kind",
    [
        "Microsoft.Network/publicIPAddresses@2024-05-01",
        "Microsoft.App/containerApps@2025-01-01",
        "Microsoft.Authorization/roleAssignments@2022-04-01",
        "Microsoft.ContainerRegistry/registries@2023-07-01",
        "Microsoft.Storage/storageAccounts@2023-05-01",
    ],
)
def test_out_of_scope_resources_are_rejected(kind: str) -> None:
    resource = f"resource extra '{kind}' = if (provisioningApproved) {{\n}}\n"
    with pytest.raises(ValidationError):
        validate_template(TEXT + "\n" + resource)


def test_comments_cannot_satisfy_or_trip_rules() -> None:
    # A gate or tag present only in a comment does not count.
    without_gate = TEXT.replace(
        "@allowed([false])\nparam provisioningApproved bool = false",
        "// @allowed([false])\n"
        "// param provisioningApproved bool = false\n"
        "param provisioningApproved bool = true",
    )
    with pytest.raises(ValidationError, match="hard_gate_missing"):
        validate_template(without_gate)
    # Forbidden words inside comments are ignored.
    assert validate_template(TEXT + "\n// no secrets, image: or public IP here\n")["resources"] == 8


def test_m23_main_gate_change_is_detected(isolated: Path) -> None:
    main = isolated / M23_MAIN
    main.write_text(
        main.read_text().replace(
            "@allowed([false])\nparam deploymentEnabled",
            "@allowed([true, false])\nparam deploymentEnabled",
        )
    )
    with pytest.raises(ValidationError, match="m23_gate_changed"):
        validate_repository(isolated)


def test_validation_makes_no_network_or_subprocess_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("offline validation attempted external execution")

    monkeypatch.setattr(socket.socket, "connect", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    monkeypatch.setattr(subprocess, "Popen", forbidden)
    assert validate_repository(ROOT)["status"] == "PASS"


def test_cli_refuses_provisioning_with_blocked_exit_code() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(ROOT / "deployment/infra_validation.py"),
            "--root",
            str(ROOT),
            "--check-provisioning",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 78 and "no cloud execution" in result.stderr
    assert (
        json.loads(
            subprocess.run(
                [
                    sys.executable,
                    "-I",
                    "-B",
                    str(ROOT / "deployment/infra_validation.py"),
                    "--root",
                    str(ROOT),
                ],
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
        )["status"]
        == "PASS"
    )
