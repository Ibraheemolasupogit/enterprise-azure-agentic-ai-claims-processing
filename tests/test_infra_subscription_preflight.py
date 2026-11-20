"""Offline tests for the fail-closed subscription preflight (no Azure calls)."""

import copy
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deployment.infra_subscription_preflight import (  # noqa: E402
    PreflightError,
    approved_commitment,
    check,
    commitment,
    lint,
)

MODULE = ROOT / "deployment/infra_subscription_preflight.py"
PROPOSAL = (
    ROOT / "docs/deployment/infra-validation-approvals/2026-11-20-g2-approved-values-proposal.md"
)
# Synthetic fixture GUIDs, built at runtime so no GUID literal appears in this file's text.
SUB = "-".join(["1a2b3c4d", "5e6f", "4a1b", "8c2d", "0123456789ab"])
OTHER = "-".join(["ffffffff", "0000", "4000", "8000", "000000000001"])
ACCOUNT: dict[str, Any] = {"id": SUB, "name": "OctoCAT-Agentic-AI", "state": "Enabled"}
APPROVED = "sha256:" + hashlib.sha256(("infraval-subscription-v1:" + SUB).encode()).hexdigest()


def text(account: dict[str, Any]) -> str:
    return json.dumps(account)


def test_commitment_is_domain_separated_and_case_insensitive() -> None:
    assert commitment(SUB) == APPROVED
    assert commitment(SUB.upper()) == APPROVED
    assert APPROVED != "sha256:" + hashlib.sha256(SUB.encode()).hexdigest()
    assert re.fullmatch(r"sha256:[0-9a-f]{64}", APPROVED)


@pytest.mark.parametrize("bad", ["", "OctoCAT-Agentic-AI", SUB[:-1], SUB + "0", " " + SUB])
def test_commitment_rejects_non_guid(bad: str) -> None:
    with pytest.raises(PreflightError, match="subscription_id_format"):
        commitment(bad)


def test_check_passes_for_matching_subscription() -> None:
    result = check(text(ACCOUNT), APPROVED, SUB)
    assert result == {
        "subscription_preflight": "PASS",
        "name": "OctoCAT-Agentic-AI",
        "state": "Enabled",
    }
    assert SUB not in json.dumps(result)


def test_check_accepts_session_value_with_trailing_newline_and_case() -> None:
    assert check(text(ACCOUNT), APPROVED, SUB.upper() + "\n")["subscription_preflight"] == "PASS"


@pytest.mark.parametrize(
    ("account", "approved", "session", "code"),
    [
        ({**ACCOUNT, "id": OTHER}, APPROVED, OTHER, "subscription_hash_mismatch"),
        ({**ACCOUNT, "name": "Other"}, APPROVED, SUB, "subscription_name_mismatch"),
        ({**ACCOUNT, "name": "octocat-agentic-ai"}, APPROVED, SUB, "subscription_name_mismatch"),
        ({**ACCOUNT, "state": "Disabled"}, APPROVED, SUB, "subscription_not_enabled"),
        ({**ACCOUNT, "state": "Warned"}, APPROVED, SUB, "subscription_not_enabled"),
        (
            {k: v for k, v in ACCOUNT.items() if k != "state"},
            APPROVED,
            SUB,
            "subscription_not_enabled",
        ),
        ({k: v for k, v in ACCOUNT.items() if k != "id"}, APPROVED, SUB, "account_id_missing"),
        ({**ACCOUNT, "id": 7}, APPROVED, SUB, "account_id_missing"),
        ({**ACCOUNT, "id": "not-a-guid"}, APPROVED, SUB, "subscription_id_format"),
        (ACCOUNT, APPROVED, None, "session_subscription_missing"),
        (ACCOUNT, APPROVED, "", "session_subscription_missing"),
        (ACCOUNT, APPROVED, OTHER, "session_subscription_mismatch"),
        (ACCOUNT, APPROVED.upper(), SUB, "approved_format"),
        (ACCOUNT, APPROVED[len("sha256:") :], SUB, "approved_format"),
        (ACCOUNT, APPROVED + "0", SUB, "approved_format"),
        (ACCOUNT, "sha256:" + "0" * 64, SUB, "subscription_hash_mismatch"),
    ],
)
def test_check_refuses(
    account: dict[str, Any], approved: str, session: str | None, code: str
) -> None:
    with pytest.raises(PreflightError, match=f"^{code}$"):
        check(text(account), approved, session)


@pytest.mark.parametrize("raw", ["", "not json", "[]", '"x"'])
def test_check_refuses_malformed_account_json(raw: str) -> None:
    with pytest.raises(PreflightError, match="account_json"):
        check(raw, APPROVED, SUB)


def test_approved_commitment_from_contract() -> None:
    live = json.loads((ROOT / "infra/azure-validation/contract.json").read_text())
    with pytest.raises(PreflightError, match="subscription_not_approved"):
        approved_commitment(live)  # live value is still null: fail closed
    filled = copy.deepcopy(live)
    filled["approved_values"]["subscription_id"] = APPROVED
    assert approved_commitment(filled) == APPROVED
    for bad in ("OctoCAT-Agentic-AI", SUB, APPROVED.upper(), 1):
        filled["approved_values"]["subscription_id"] = bad
        with pytest.raises(PreflightError, match="approved_format"):
            approved_commitment(filled)


def run(
    args: list[str], stdin: str, env_sub: str | None = None
) -> subprocess.CompletedProcess[str]:
    env = {"PATH": "/usr/bin:/bin"}
    if env_sub is not None:
        env["INFRAVAL_SUB"] = env_sub
    return subprocess.run(
        [sys.executable, "-I", "-B", str(MODULE), *args],
        input=stdin,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def test_cli_commit_prints_only_the_commitment() -> None:
    result = run(["commit"], text(ACCOUNT))
    assert result.returncode == 0 and result.stdout.strip() == APPROVED
    assert SUB not in result.stdout + result.stderr


@pytest.mark.parametrize(
    "account", [{**ACCOUNT, "name": "Other"}, {**ACCOUNT, "state": "Disabled"}]
)
def test_cli_commit_refuses_wrong_subscription(account: dict[str, Any]) -> None:
    result = run(["commit"], text(account))
    assert result.returncode == 78 and SUB not in result.stdout + result.stderr


def test_cli_check_pass_and_refusals_never_print_the_id(tmp_path: Path) -> None:
    assert run(["check", "--approved", APPROVED], text(ACCOUNT), SUB).returncode == 0
    contract = json.loads((ROOT / "infra/azure-validation/contract.json").read_text())
    contract["approved_values"]["subscription_id"] = APPROVED
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract))
    assert run(["check", "--contract", str(path)], text(ACCOUNT), SUB).returncode == 0
    cases = [
        (["check", "--approved", APPROVED], text({**ACCOUNT, "id": OTHER}), OTHER),
        (["check", "--approved", APPROVED], text(ACCOUNT), None),
        (["check", "--approved", APPROVED], text(ACCOUNT), OTHER),
        (
            ["check", "--contract", str(ROOT / "infra/azure-validation/contract.json")],
            text(ACCOUNT),
            SUB,
        ),
        (["check", "--contract", str(tmp_path / "missing.json")], text(ACCOUNT), SUB),
        (["check", "--approved", APPROVED], "{", SUB),
    ]
    for args, stdin, session in cases:
        result = run(args, stdin, session)
        assert result.returncode == 78, args
        assert json.loads(result.stdout)["subscription_preflight"] == "REFUSED"
        assert (
            SUB not in result.stdout + result.stderr and OTHER not in result.stdout + result.stderr
        )


COMPLIANT = """set -euo pipefail
SUB=$(az account show --query id -o tsv)
az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \\
  python3 -I infra_subscription_preflight.py check --contract contract.json
test "$(az group exists -n "$RG" --subscription "$SUB")" = false
az group list --subscription "$SUB" --query "[?name=='x'] | length(@)" -o tsv
test "$(az deployment group list -g "$RG" --subscription "$SUB" \\
  --query "length([?a=='b'])" -o tsv)" = 0
# az group delete -n "$RG"   (comments are ignored)
az group create -n "$RG" -l uksouth --subscription "$SUB" -o none \\
  --tags purpose=infrastructure-validation
"""


def test_lint_accepts_compliant_procedure() -> None:
    assert lint(COMPLIANT) == []


@pytest.mark.parametrize(
    ("script", "violation"),
    [
        ('az group create -n "$RG" -l uksouth', "missing_explicit_subscription"),
        ('test "$(az group exists -n "$RG")" = false', "missing_explicit_subscription"),
        ('az group list | grep x --subscription "$SUB"', "missing_explicit_subscription"),
        ("az group list --subscription $SUB", "missing_explicit_subscription"),
        ("az group list --subscription OctoCAT-Agentic-AI", "missing_explicit_subscription"),
        (
            'az group list --subscription "$SUB" --subscription "$X"',
            "missing_explicit_subscription",
        ),
        ("az account show -o json", "missing_explicit_subscription"),
        (
            'az group delete -n "$RG" --yes; az group list --subscription "$SUB"',
            "missing_explicit_subscription",
        ),
        ('az group create -n "$RG" \\\n  -l uksouth -o none', "missing_explicit_subscription"),
        ('az account set --subscription "$SUB"', "forbidden_command"),
        ("set -x", "xtrace_enabled"),
        ("set -euxo pipefail", "xtrace_enabled"),
        ("set -o xtrace", "xtrace_enabled"),
        ("bash -x procedure.sh", "xtrace_enabled"),
        ("  set -ux", "xtrace_enabled"),
        ('az group list --subscription "$SUB" # ' + SUB, "raw_guid_literal"),
    ],
)
def test_lint_refuses(script: str, violation: str) -> None:
    assert any(violation in v for v in lint(script)), lint(script)


def test_cli_lint_exit_codes(tmp_path: Path) -> None:
    good, bad = tmp_path / "good.sh", tmp_path / "bad.sh"
    good.write_text(COMPLIANT)
    bad.write_text('az group delete -n "$RG" --yes\n')
    assert run(["lint", str(good)], "").returncode == 0
    assert run(["lint", str(bad)], "").returncode == 78


def test_proposal_procedures_pass_lint() -> None:
    blocks = re.findall(r"```bash\n(.*?)```", PROPOSAL.read_text(), re.S)
    assert len(blocks) == 3
    for block in blocks:
        assert "az " in block and lint(block) == []


def test_no_guid_literal_in_module_tests_or_proposal() -> None:
    pattern = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
    )
    for path in (MODULE, Path(__file__), PROPOSAL):
        assert not pattern.search(path.read_text()), path


# --- G9 procedures executed against a stub `az` (offline): regression tests for D1-D3 ---------

STUB_AZ = r"""#!/bin/bash
echo "$*" >> "$CALLS"
case "$*" in
  "account show --query id -o tsv") echo "$STUBSUB" ;;
  "account show --subscription "*" -o json")
    printf '{"id":"%s","name":"OctoCAT-Agentic-AI","state":"Enabled"}\n' "$STUBSUB" ;;
  "group exists"*) if [ -f "$CALLS.deleted" ]; then echo false; else echo "$STUB_EXISTS"; fi ;;
  "group list"*)
    if [ "$STUB_LIST_FAILS" = 1 ]; then echo "ERROR: AuthorizationFailed" >&2; exit 1; fi
    if [ -n "$STUB_GROUPS" ]; then printf '%s\n' "$STUB_GROUPS"; fi ;;
  "group create"*) ;;
  *"--query {state:"*)
    printf '{"state": "%s", "location": "%s", "tags": %s}\n' \
      "$STUB_STATE" "$STUB_LOCATION" "$STUB_TAGS" ;;
  *"--query properties.provisioningState"*) echo "$STUB_STATE" ;;
  *"--query location"*) echo "$STUB_LOCATION" ;;
  *"--query tags -o json"*) echo "$STUB_TAGS" ;;
  *"--query tags.infravalRun"*) echo infraval-20261125-01 ;;
  *"--query tags.purpose"*) echo infrastructure-validation ;;
  "resource list"*|"lock list"*) echo 0 ;;
  "deployment group list"*)
    n=0
    for s in $STUB_DEPLOYMENTS; do
      case "$*" in
        *"!='Succeeded'"*"!='Failed'"*"!='Canceled'"*)
          case "$s" in Succeeded|Failed|Canceled) ;; *) n=$((n + 1)) ;; esac ;;
        *"=='Running'"*) if [ "$s" = Running ]; then n=$((n + 1)); fi ;;
        *) n=999 ;;
      esac
    done
    echo "$n" ;;
  "group delete"*) touch "$CALLS.deleted" ;;
  *) echo "unexpected az call" >&2; exit 2 ;;
esac
"""
GOOD_TAGS = {
    "purpose": "infrastructure-validation",
    "infravalRun": "infraval-20261125-01",
    "expiresAt": "2026-11-25T16:00:00Z",
}
STUB_DEFAULTS = {
    "STUB_EXISTS": "false",
    "STUB_LIST_FAILS": "0",
    "STUB_GROUPS": "",
    "STUB_STATE": "Succeeded",
    "STUB_LOCATION": "uksouth",
    "STUB_TAGS": json.dumps(GOOD_TAGS),
    "STUB_DEPLOYMENTS": "",
}


def proposal_blocks(path: Path = PROPOSAL) -> list[str]:
    return re.findall(r"```bash\n(.*?)```", path.read_text(), re.S)


def run_block(block: str, tmp_path: Path, **overrides: str) -> tuple[int, list[str]]:
    """Run one proposal block in Cloud Shell shape against the stub; never contacts Azure."""
    work, bin_dir = tmp_path / "work", tmp_path / "bin"
    work.mkdir()
    bin_dir.mkdir()
    (bin_dir / "az").write_text(STUB_AZ)
    (bin_dir / "az").chmod(0o755)
    (bin_dir / "python3").symlink_to(sys.executable)
    shutil.copy(MODULE, work / MODULE.name)
    contract = json.loads((ROOT / "infra/azure-validation/contract.json").read_text())
    contract["approved_values"]["subscription_id"] = APPROVED  # temporary copy only
    (work / "contract.json").write_text(json.dumps(contract))
    (work / "procedure.sh").write_text(block)
    calls = tmp_path / "calls.log"
    calls.write_text("")
    env = {"PATH": f"{bin_dir}:/usr/bin:/bin", "CALLS": str(calls), "STUBSUB": SUB}
    env.update(STUB_DEFAULTS)
    env.update(overrides)
    result = subprocess.run(
        ["/bin/bash", "procedure.sh"],
        cwd=work,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert SUB not in result.stdout + result.stderr
    return result.returncode, calls.read_text().splitlines()


def count(calls: list[str], prefix: str) -> int:
    return sum(call.startswith(prefix) for call in calls)


CREATE, CLEANUP = proposal_blocks()[1], proposal_blocks()[2]


def test_g9_create_passes_on_clean_state(tmp_path: Path) -> None:
    code, calls = run_block(CREATE, tmp_path)
    assert code == 0 and count(calls, "group create") == 1
    bootstrap = "account show --query id -o tsv"
    assert all(f"--subscription {SUB}" in call for call in calls if call != bootstrap)


def test_g9_create_refuses_when_group_list_fails_d1(tmp_path: Path) -> None:
    code, calls = run_block(CREATE, tmp_path, STUB_LIST_FAILS="1")
    assert code != 0 and count(calls, "group create") == 0


def test_g9_create_refuses_existing_group_in_any_case(tmp_path: Path) -> None:
    code, calls = run_block(CREATE, tmp_path, STUB_GROUPS="RG-Claims-Infraval-UKS-Tmp01")
    assert code != 0 and count(calls, "group create") == 0


@pytest.mark.parametrize(
    "override",
    [
        {"STUB_STATE": "Failed"},
        {"STUB_STATE": ""},
        {"STUB_LOCATION": "westeurope"},
        {"STUB_TAGS": json.dumps({k: v for k, v in GOOD_TAGS.items() if k != "expiresAt"})},
        {"STUB_TAGS": json.dumps({**GOOD_TAGS, "extra": "x"})},
        {"STUB_TAGS": json.dumps({**GOOD_TAGS, "infravalRun": "infraval-20261125-02"})},
        {"STUB_TAGS": "null"},
        {"STUB_TAGS": "not json"},
    ],
)
def test_g9_create_stops_on_bad_post_state_d2(tmp_path: Path, override: dict[str, str]) -> None:
    code, calls = run_block(CREATE, tmp_path, **override)
    assert code != 0
    assert count(calls, "group create") == 1 and count(calls, "group delete") == 0


def test_g9_cleanup_deletes_only_an_idle_empty_group(tmp_path: Path) -> None:
    code, calls = run_block(
        CLEANUP, tmp_path, STUB_EXISTS="true", STUB_DEPLOYMENTS="Succeeded Failed Canceled"
    )
    assert code == 0 and count(calls, "group delete") == 1


@pytest.mark.parametrize(
    "states", ["Accepted", "Running", "Deploying", "Canceling", "Succeeded Accepted"]
)
def test_g9_cleanup_refuses_unfinished_deployment_d3(tmp_path: Path, states: str) -> None:
    code, calls = run_block(CLEANUP, tmp_path, STUB_EXISTS="true", STUB_DEPLOYMENTS=states)
    assert code != 0 and count(calls, "group delete") == 0
