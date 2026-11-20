"""Offline tests for the stage 6 validate/what-if procedure, run against a stub `az`.

No Azure call is made: `az` is a local stub that records its arguments. The contract,
templates and parameters are synthetic copies in a fresh temporary directory; the repository
contract is only read.
"""

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deployment.infra_subscription_preflight import (  # noqa: E402
    AZ,
    _logical_lines,
    _segment,
    lint,
)

PROCEDURE = ROOT / "deployment/infra_stage6_validate_whatif.sh"
PREFLIGHT = ROOT / "deployment/infra_subscription_preflight.py"
VALIDATOR = ROOT / "deployment/infra_validation.py"
CONTRACT = ROOT / "infra/azure-validation/contract.json"
# Synthetic fixture GUIDs, built at runtime so no GUID literal appears in this file's text.
SUB = "-".join(["1a2b3c4d", "5e6f", "4a1b", "8c2d", "0123456789ab"])
OTHER = "-".join(["ffffffff", "0000", "4000", "8000", "000000000001"])
APPROVED = "sha256:" + hashlib.sha256(("infraval-subscription-v1:" + SUB).encode()).hexdigest()
RG = "rg-claims-infraval-uks-tmp01"
RUN = "infraval-20261125-01"
EXPIRES = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
PAST = (datetime.now(UTC) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
FILES = (
    "contract.json",
    "execution.json",
    "infra_subscription_preflight.py",
    "infra_validation.py",
    "parameters.json",
    "reviewed.json",
)
TYPES = (
    "Microsoft.App/managedEnvironments",
    "Microsoft.Consumption/budgets",
    "Microsoft.Insights/diagnosticSettings",
    "Microsoft.KeyVault/vaults",
    "Microsoft.ManagedIdentity/userAssignedIdentities",
    "Microsoft.Network/networkSecurityGroups",
    "Microsoft.Network/virtualNetworks",
    "Microsoft.OperationalInsights/workspaces",
)
REVIEWED: dict[str, Any] = {
    "metadata": {"_generator": {"version": "0.48.1.0", "templateHash": "1"}},
    "parameters": {
        "provisioningApproved": {"type": "bool", "defaultValue": False, "allowedValues": [False]}
    },
    "resources": [{"type": t, "condition": "[parameters('provisioningApproved')]"} for t in TYPES],
}
EXECUTION: dict[str, Any] = copy.deepcopy(REVIEWED)
EXECUTION["parameters"]["provisioningApproved"]["allowedValues"] = [False, True]
PROV = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers"
CHANGES = [
    f"{PROV}/Microsoft.Network/networkSecurityGroups/nsval-abc-nsg",
    f"{PROV}/Microsoft.Network/virtualNetworks/nsval-abc-vnet",
    f"{PROV}/Microsoft.ManagedIdentity/userAssignedIdentities/nsval-abc-id",
    f"{PROV}/Microsoft.KeyVault/vaults/nsvalabckv",
    f"{PROV}/Microsoft.OperationalInsights/workspaces/nsval-abc-logs",
    f"{PROV}/Microsoft.KeyVault/vaults/nsvalabckv/providers/"
    "Microsoft.Insights/diagnosticSettings/vault-audit",
    f"{PROV}/Microsoft.Consumption/budgets/nsval-abc-budget",
]
CREATES: list[dict[str, str]] = [{"resourceId": r, "changeType": "Create"} for r in CHANGES]
GOOD_WHATIF: dict[str, Any] = {"status": "Succeeded", "changes": CREATES}
GOOD_TAGS = {"purpose": "infrastructure-validation", "infravalRun": RUN, "expiresAt": EXPIRES}

STUB_AZ = r"""#!/bin/bash
echo "$*" >> "$CALLS"
case "$*" in
  "account show --query id -o tsv") echo "$STUBSUB" ;;
  "account show --subscription "*" -o json")
    printf '{"id":"%s","name":"%s","state":"Enabled"}\n' "$STUB_ACCOUNT" "$STUB_NAME" ;;
  "group exists"*) echo "$STUB_EXISTS" ;;
  *"--query properties.provisioningState"*) echo "$STUB_STATE" ;;
  *"--query location"*) echo "$STUB_LOCATION" ;;
  *"--query tags -o json"*) echo "$STUB_TAGS" ;;
  "resource list"*)
    if grep -q "^deployment group validate" "$CALLS"; then echo "$STUB_RESOURCES_AFTER";
    else echo "$STUB_RESOURCES"; fi ;;
  "lock list"*) echo "$STUB_LOCKS" ;;
  "deployment group list"*) echo "$STUB_DEPLOYMENTS" ;;
  "deployment group validate"*)
    if [ "$STUB_VALIDATE_FAILS" = 1 ]; then echo "ERROR: InvalidTemplate" >&2; exit 1; fi
    echo "$STUB_VALIDATE" ;;
  "deployment group what-if"*)
    if [ "$STUB_WHATIF_FAILS" = 1 ]; then echo "ERROR: what-if failed" >&2; exit 1; fi
    echo "$STUB_WHATIF" ;;
  *) echo "unexpected az call" >&2; exit 2 ;;
esac
"""
STUB_DEFAULTS = {
    "STUB_ACCOUNT": SUB,
    "STUB_NAME": "OctoCAT-Agentic-AI",
    "STUB_EXISTS": "true",
    "STUB_STATE": "Succeeded",
    "STUB_LOCATION": "uksouth",
    "STUB_TAGS": json.dumps(GOOD_TAGS),
    "STUB_RESOURCES": "0",
    "STUB_RESOURCES_AFTER": "0",
    "STUB_LOCKS": "0",
    "STUB_DEPLOYMENTS": "0",
    "STUB_VALIDATE_FAILS": "0",
    "STUB_VALIDATE": json.dumps({"properties": {"provisioningState": "Succeeded"}}),
    "STUB_WHATIF_FAILS": "0",
    "STUB_WHATIF": json.dumps(GOOD_WHATIF),
}
AZ_VERBS = {
    "account show",
    "group exists",
    "group show",
    "resource list",
    "lock list",
    "deployment group list",
    "deployment group validate",
    "deployment group what-if",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def approved_contract(expires: str = EXPIRES) -> dict[str, Any]:
    """A synthetic APPROVED_FOR_VALIDATION copy: stages 1-6 approved, 7-9 still pending."""
    contract: dict[str, Any] = json.loads(CONTRACT.read_text())
    contract["status"] = "APPROVED_FOR_VALIDATION"
    for key in ("cloud_validation",):
        contract["approvals"][key].update(
            status="APPROVED",
            approval_identity="repository-owner",
            approval_time="2026-11-25T12:00:00Z",
            evidence_sha256="e" * 64,
        )
    contract["approved_values"].update(
        location="uksouth",
        resource_group=RG,
        include_container_environment=False,
        log_daily_quota_gb=1,
        subscription_id=APPROVED,
        expires_at=expires,
    )
    return contract


def parameters(contract: dict[str, Any]) -> bytes:
    v = contract["approved_values"]
    values = {
        "location": v["location"],
        "owner": v["owner"],
        "expiresAt": v["expires_at"],
        "budgetAmount": v["budget_amount"],
        "budgetContactEmails": v["budget_contact_emails"],
        "budgetStartDate": v["budget_start_date"],
        "budgetEndDate": v["budget_end_date"],
        "logDailyQuotaGb": v["log_daily_quota_gb"],
        "includeContainerEnvironment": False,
        "provisioningApproved": True,
    }
    return json.dumps({"parameters": {k: {"value": x} for k, x in values.items()}}).encode()


def stage(tmp_path: Path, contract: dict[str, Any] | None = None) -> Path:
    """Fresh Cloud Shell-shaped directory with the six files and SHA256SUMS."""
    work = tmp_path / "work"
    work.mkdir()
    shutil.copy(PREFLIGHT, work / PREFLIGHT.name)
    shutil.copy(VALIDATOR, work / VALIDATOR.name)
    shutil.copy(PROCEDURE, work / PROCEDURE.name)
    contract = approved_contract() if contract is None else contract
    reviewed, execution = json.dumps(REVIEWED).encode(), json.dumps(EXECUTION).encode()
    params = parameters(contract)
    if contract["status"] != "PREPARATION_ONLY":
        contract["execution"].update(
            run_id=RUN,
            resource_group=RG,
            reviewed_template_sha256=sha(reviewed),
            approved_template_sha256=sha(execution),
            approved_parameters_sha256=sha(params),
        )
    (work / "contract.json").write_text(json.dumps(contract))
    (work / "reviewed.json").write_bytes(reviewed)
    (work / "execution.json").write_bytes(execution)
    (work / "parameters.json").write_bytes(params)
    sums = "".join(f"{sha((work / n).read_bytes())}  {n}\n" for n in FILES)
    (work / "SHA256SUMS").write_text(sums)
    return work


def run(work: Path, tmp_path: Path, **overrides: str) -> tuple[int, list[str], str]:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "az").write_text(STUB_AZ)
    (bin_dir / "az").chmod(0o755)
    (bin_dir / "python3").symlink_to(sys.executable)
    calls = tmp_path / "calls.log"
    calls.write_text("")
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin",
        "CALLS": str(calls),
        "STUBSUB": SUB,
        **STUB_DEFAULTS,
        **overrides,
    }
    result = subprocess.run(
        ["/bin/bash", PROCEDURE.name],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    output = result.stdout + result.stderr
    assert SUB not in output and OTHER not in output  # the raw ID is never printed
    return result.returncode, calls.read_text().splitlines(), result.stdout


def count(calls: list[str], prefix: str) -> int:
    return sum(call.startswith(prefix) for call in calls)


def test_procedure_passes_strict_lint_via_cli() -> None:
    assert lint(PROCEDURE.read_text()) == []
    result = subprocess.run(
        [sys.executable, "-I", "-B", str(PREFLIGHT), "lint", str(PROCEDURE)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0 and json.loads(result.stdout)["lint"] == "PASS"


def test_procedure_uses_only_read_validate_and_whatif_commands() -> None:
    commands = [
        _segment(line, match.start())
        for _, line in _logical_lines(PROCEDURE.read_text())
        for match in AZ.finditer(line)
    ]
    verbs = [" ".join(w for w in c.split()[1:4] if not w.startswith("-")) for c in commands]
    assert all(any(v.startswith(allowed) for allowed in AZ_VERBS) for v in verbs), verbs
    assert verbs.count("deployment group validate") == 1
    assert verbs.count("deployment group what-if") == 1
    assert not any("--no-wait" in c for c in commands)


def test_stage6_passes_on_approved_contract_and_clean_group(tmp_path: Path) -> None:
    code, calls, stdout = run(stage(tmp_path), tmp_path)
    assert code == 0, calls
    assert "STAGE6_VALIDATE_WHATIF: PASS" in stdout
    assert calls[0] == "account show --query id -o tsv"
    assert calls[1].startswith("account show --subscription ")
    assert all(f"--subscription {SUB}" in c for c in calls[1:])
    assert all(any(c.startswith(v) for v in AZ_VERBS) for c in calls)
    assert count(calls, "deployment group validate") == 1
    assert count(calls, "deployment group what-if") == 1
    work = tmp_path / "work"
    assert json.loads((work / "authorize.json").read_text())["provisioning"] == "NOT_AUTHORIZED"
    assert len(json.loads((work / "whatif-check.json").read_text())) == 7


def test_repository_contract_refuses_before_any_azure_command(tmp_path: Path) -> None:
    live: dict[str, Any] = json.loads(CONTRACT.read_text())  # PREPARATION_ONLY
    code, calls, _ = run(stage(tmp_path, live), tmp_path)
    assert code == 78 and calls == []


@pytest.mark.parametrize(
    "mutate",
    [
        lambda c: c.update(status="PREPARATION_ONLY"),
        lambda c: c["approvals"]["cloud_validation"].update(
            status="PENDING", approval_identity=None, approval_time=None, evidence_sha256=None
        ),
        lambda c: c["approved_values"].update(subscription_id=None),
    ],
)
def test_unapproved_contract_refuses_before_any_azure_command(tmp_path: Path, mutate: Any) -> None:
    contract = approved_contract()
    mutate(contract)
    work = stage(tmp_path, contract)
    if contract["status"] == "PREPARATION_ONLY":  # keep it internally valid: null execution
        contract["execution"] = dict.fromkeys(contract["execution"])
        (work / "contract.json").write_text(json.dumps(contract))
        sums = "".join(f"{sha((work / n).read_bytes())}  {n}\n" for n in FILES)
        (work / "SHA256SUMS").write_text(sums)
    code, calls, _ = run(work, tmp_path)
    assert code != 0 and calls == []


@pytest.mark.parametrize("target", ["contract.json", "execution.json", "infra_validation.py"])
def test_tampered_upload_refuses_before_any_azure_command(tmp_path: Path, target: str) -> None:
    work = stage(tmp_path)
    with (work / target).open("a") as handle:
        handle.write("\n")
    code, calls, _ = run(work, tmp_path)
    assert code != 0 and calls == []


@pytest.mark.parametrize(
    "manifest_edit",
    [
        lambda lines: lines[:-1],  # a file missing from the manifest
        lambda lines: [*lines, lines[0]],  # a duplicate entry
        lambda lines: [*lines, f"{'0' * 64}  extra.json"],  # an unexpected file
    ],
)
def test_manifest_must_list_exactly_the_six_files(tmp_path: Path, manifest_edit: Any) -> None:
    work = stage(tmp_path)
    lines = (work / "SHA256SUMS").read_text().splitlines()
    (work / "SHA256SUMS").write_text("\n".join(manifest_edit(lines)) + "\n")
    code, calls, _ = run(work, tmp_path)
    assert code != 0 and calls == []


def test_expired_approval_refuses_before_any_azure_command(tmp_path: Path) -> None:
    code, calls, _ = run(stage(tmp_path, approved_contract(PAST)), tmp_path, STUB_TAGS="{}")
    assert code != 0 and calls == []


@pytest.mark.parametrize(
    "override",
    [
        {"STUB_ACCOUNT": OTHER},  # the live subscription isn't the approved commitment
        {"STUBSUB": OTHER, "STUB_ACCOUNT": OTHER},
        {"STUB_NAME": "Some-Other-Subscription"},
    ],
)
def test_failed_preflight_stops_before_any_other_azure_command(
    tmp_path: Path, override: dict[str, str]
) -> None:
    code, calls, _ = run(stage(tmp_path), tmp_path, **override)
    assert code == 78
    assert all(c.startswith("account show") for c in calls) and len(calls) == 2


@pytest.mark.parametrize(
    "override",
    [
        {"STUB_EXISTS": "false"},
        {"STUB_EXISTS": ""},
        {"STUB_STATE": "Deleting"},
        {"STUB_LOCATION": "westeurope"},
        {"STUB_TAGS": json.dumps({**GOOD_TAGS, "infravalRun": "infraval-other"})},
        {"STUB_TAGS": json.dumps({**GOOD_TAGS, "extra": "x"})},
        {"STUB_TAGS": "null"},
        {"STUB_RESOURCES": "1"},
        {"STUB_RESOURCES": ""},
        {"STUB_LOCKS": "1"},
        {"STUB_DEPLOYMENTS": "1"},
    ],
)
def test_unexpected_group_state_stops_before_validate(
    tmp_path: Path, override: dict[str, str]
) -> None:
    code, calls, _ = run(stage(tmp_path), tmp_path, **override)
    assert code != 0 and count(calls, "deployment group") <= 1
    assert count(calls, "deployment group validate") == 0


@pytest.mark.parametrize(
    "override",
    [
        {"STUB_VALIDATE_FAILS": "1"},
        {"STUB_VALIDATE": json.dumps({"properties": {"provisioningState": "Failed"}})},
        {"STUB_VALIDATE": "not json"},
    ],
)
def test_failed_validate_stops_before_whatif(tmp_path: Path, override: dict[str, str]) -> None:
    code, calls, stdout = run(stage(tmp_path), tmp_path, **override)
    assert code != 0 and "PASS (validation" not in stdout
    assert count(calls, "deployment group what-if") == 0


def _whatif(changes: list[dict[str, str]], status: str = "Succeeded") -> str:
    return json.dumps({"status": status, "changes": changes})


@pytest.mark.parametrize(
    "override",
    [
        {"STUB_WHATIF_FAILS": "1"},
        {"STUB_WHATIF": _whatif(CREATES, status="Failed")},
        {"STUB_WHATIF": _whatif(CREATES[:-1])},
        {"STUB_WHATIF": _whatif([{**CREATES[0], "changeType": "Modify"}, *CREATES[1:]])},
        {"STUB_WHATIF": _whatif([{**CREATES[0], "changeType": "Unsupported"}, *CREATES[1:]])},
        {
            "STUB_WHATIF": _whatif(
                [
                    *CREATES,
                    {
                        "resourceId": f"{PROV}/Microsoft.Network/publicIPAddresses/nsval-ip",
                        "changeType": "Create",
                    },
                ]
            )
        },
        {"STUB_WHATIF": "not json"},
        {"STUB_RESOURCES_AFTER": "1"},
    ],
)
def test_unexpected_whatif_or_post_state_fails_closed(
    tmp_path: Path, override: dict[str, str]
) -> None:
    code, _, stdout = run(stage(tmp_path), tmp_path, **override)
    assert code != 0 and "PASS (validation" not in stdout
