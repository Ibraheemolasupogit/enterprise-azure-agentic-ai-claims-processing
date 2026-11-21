# ruff: noqa: E501  (the embedded stub `az` script keeps one command per line)
"""Offline tests for the stage 7 deployment and stage 8 teardown procedures.

No Azure call is made: `az` is a stateful local stub (Python) that models the resource group, its
resources, soft-deleted vaults and workspaces, budgets and deployments, and records every call.
The contract, templates, parameters and what-if are synthetic copies in fresh temporary
directories; the repository contract is only read.
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

from deployment.infra_evidence import EvidenceError, count_scopes, pin_targets  # noqa: E402
from deployment.infra_subscription_preflight import lint  # noqa: E402

DEPLOY = ROOT / "deployment"
STAGE7, STAGE8 = DEPLOY / "infra_stage7_deploy.sh", DEPLOY / "infra_stage8_teardown.sh"
COST = DEPLOY / "infra_stage8_cost_check.sh"
CONTRACT = ROOT / "infra/azure-validation/contract.json"
# Synthetic fixture GUIDs, built at runtime so no GUID literal appears in this file's text.
SUB = "-".join(["1a2b3c4d", "5e6f", "4a1b", "8c2d", "0123456789ab"])
OTHER = "-".join(["ffffffff", "0000", "4000", "8000", "000000000001"])
APPROVED = "sha256:" + hashlib.sha256(("infraval-subscription-v1:" + SUB).encode()).hexdigest()
RG, RUN, U = "rg-claims-infraval-uks-tmp01", "infraval-20261125-01", "abcdefghij123"
NOW = datetime.now(UTC).replace(microsecond=0)
Z = "%Y-%m-%dT%H:%M:%SZ"
START, END = (NOW - timedelta(minutes=10)).strftime(Z), (NOW + timedelta(minutes=100)).strftime(Z)
EXPIRES = (NOW + timedelta(minutes=160)).strftime(Z)
FILES = (
    "contract.json",
    "execution.json",
    "infra_evidence.py",
    "infra_subscription_preflight.py",
    "infra_validation.py",
    "parameters.json",
    "reviewed.json",
    "whatif.json",
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
    "parameters": {
        "provisioningApproved": {"type": "bool", "defaultValue": False, "allowedValues": [False]}
    },
    "resources": [{"type": t, "condition": "[parameters('provisioningApproved')]"} for t in TYPES],
}
EXECUTION: dict[str, Any] = copy.deepcopy(REVIEWED)
EXECUTION["parameters"]["provisioningApproved"]["allowedValues"] = [False, True]
PROV = f"/subscriptions/{SUB}/resourceGroups/{RG}/providers"
VAULT, WORKSPACE, BUDGET = f"nsval{U}kv", f"nsval-{U}-logs", f"nsval-{U}-budget"
IDS = {
    "nsg": f"{PROV}/Microsoft.Network/networkSecurityGroups/nsval-{U}-nsg",
    "vnet": f"{PROV}/Microsoft.Network/virtualNetworks/nsval-{U}-vnet",
    "id": f"{PROV}/Microsoft.ManagedIdentity/userAssignedIdentities/nsval-{U}-id",
    "kv": f"{PROV}/Microsoft.KeyVault/vaults/{VAULT}",
    "ws": f"{PROV}/Microsoft.OperationalInsights/workspaces/{WORKSPACE}",
    "diag": f"{PROV}/Microsoft.KeyVault/vaults/{VAULT}/providers/"
    "Microsoft.Insights/diagnosticSettings/vault-audit",
    "budget": f"{PROV}/Microsoft.Consumption/budgets/{BUDGET}",
}
WHATIF = {
    "status": "Succeeded",
    "changes": [{"resourceId": i, "changeType": "Create"} for i in IDS.values()],
}
GROUP_TAGS = {"purpose": "infrastructure-validation", "infravalRun": RUN, "expiresAt": EXPIRES}

STUB = r"""#!/usr/bin/env python3
import json, os, re, sys
args = sys.argv[1:]
line = " ".join(args)
path = os.environ["AZSTATE"]
st = json.load(open(path))
open(os.environ["CALLS"], "a").write(line + "\n")
def save(): json.dump(st, open(path, "w"))
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default
def out(value):
    q = opt("--query")
    if q is not None:
        m = re.fullmatch(r"length\(\[\?name=='(.*)'\]\)", q)
        if q in ("length(@)",): value = len(value)
        elif q == "length(value)": value = len(value["value"])
        elif m: value = sum(1 for v in value if v["name"] == m.group(1))
        elif q == "[].id": value = [v["id"] for v in value]
        elif q == "[].scope": value = [v["scope"] for v in value]
        elif q.startswith("tags"): value = value.get("tags")
        elif q == "location": value = value["location"]
        elif q == "name": value = value["name"]
        elif q == "properties.provisioningState": value = value["properties"]["provisioningState"]
        elif q == "properties.vaultId": value = value["properties"]["vaultId"]
        else: sys.exit("stub: unknown query " + q)
    if opt("-o") == "tsv": print(str(value).lower() if isinstance(value, bool) else value)
    else: print(json.dumps(value))
def fault(key):
    f = st["faults"].get(key)
    if f == "fail": print("ERROR: injected failure", file=sys.stderr); sys.exit(1)
    return f
def group():
    return st["group"] if st["group"] and opt("-n", opt("-g")) == st["group"]["name"] else None
g = st["group"]
if line == "account show --query id -o tsv": print(st["session"]); sys.exit()
if line.startswith("account show --subscription"):
    print(json.dumps({"id": st["account"], "name": st["name"], "state": "Enabled"})); sys.exit()
if line.startswith("group exists"):
    print("true" if group() else "false"); sys.exit()
if line.startswith("group show"):
    if not group(): sys.exit("ResourceGroupNotFound")
    out({"name": g["name"], "location": "uksouth", "tags": g["tags"], "properties": {"provisioningState": "Succeeded"}}); sys.exit()
if line.startswith("lock list"): out([{"name": "lock"}] * g["locks"]); sys.exit()
if line.startswith("resource list"):
    if "-g" in args:
        items = [r for r in g["resources"] if opt("--resource-type") is None or opt("--resource-type") + "/" in r["id"]]
    else:
        items = (g["resources"] if g else []) + st["elsewhere"]
        if opt("--tag"):
            k, v = opt("--tag").split("=")
            items = [r for r in items if r["tags"].get(k) == v]
    out(items); sys.exit()
if line.startswith("deployment group list"): out(list(g["deployments"].values())); sys.exit()
if line.startswith("deployment group create"):
    f = fault("create")
    if f and f.startswith("partial"):
        keys = f.split(":")[1].split(",")
        g["resources"] = [{"id": st["ids"][k], "tags": st["rtags"]} for k in keys]
        g["deployments"][opt("-n")] = {"name": opt("-n"), "properties": {"provisioningState": st["faults"].get("partial_state", "Failed")}}
        save(); print("ERROR: deployment failed", file=sys.stderr); sys.exit(1)
    g["resources"] = [{"id": st["ids"][k], "tags": st["rtags"]} for k in ("nsg", "vnet", "id", "kv", "ws")] + st["extra"]
    g["budgets"] = [st["budget"]]
    g["deployments"][opt("-n")] = {"name": opt("-n"), "properties": {"provisioningState": st["faults"].get("state", "Succeeded"), "outputResources": [{"id": i} for i in st["ids"].values()]}}
    save(); out(g["deployments"][opt("-n")]); sys.exit()
if line.startswith("deployment group show"):
    d = g["deployments"].get(opt("-n")) if g else None
    if not d: sys.exit("DeploymentNotFound")
    out(d); sys.exit()
if line.startswith("deployment group cancel"):
    g["deployments"][opt("-n")]["properties"]["provisioningState"] = "Canceled"; save(); sys.exit()
if line.startswith("rest"):
    url = opt("--url").replace("{subscriptionId}", opt("--subscription"))
    if "infraval-uks-tmp01-budget" in url:
        if opt("--method") != "get": sys.exit("stub: subscription budget write")
        if not st["sub_budget"]: sys.exit("NotFound")
        out(st["sub_budget"]); sys.exit()
    if not g: sys.exit("ResourceGroupNotFound")
    if opt("--method") == "delete":
        name = url.split("/budgets/")[1].split("?")[0]
        g["budgets"] = [b for b in g["budgets"] if b != name]; save(); sys.exit()
    out({"value": [{"name": b} for b in g["budgets"]]}); sys.exit()
if line.startswith("role assignment list"): out([{"scope": s} for s in st["roles"]]); sys.exit()
if line.startswith("monitor log-analytics workspace delete"):
    fault("workspace_delete")
    g["resources"] = [r for r in g["resources"] if not r["id"].endswith("/" + opt("-n"))]
    if st["faults"].get("workspace_soft"): st["deleted_ws"].append({"name": opt("-n")})
    save(); sys.exit()
if line.startswith("monitor log-analytics workspace list-deleted-workspaces"): out(st["deleted_ws"]); sys.exit()
if line.startswith("group delete"):
    fault("group_delete")
    for r in g["resources"]:
        if "/vaults/" in r["id"] and "/providers/microsoft.insights" not in r["id"].lower():
            st["deleted_vaults"].append({"name": r["id"].split("/")[-1], "properties": {"vaultId": st["faults"].get("vault_id", r["id"])}})
        if "/workspaces/" in r["id"]: st["deleted_ws"].append({"name": r["id"].split("/")[-1]})
    st["group"] = None; save(); sys.exit()
if line.startswith("keyvault show-deleted"):
    m = [v for v in st["deleted_vaults"] if v["name"] == opt("--name")]
    if not m: sys.exit("VaultNotFound")
    out(m[0]); sys.exit()
if line.startswith("keyvault purge"):
    fault("purge")
    st["deleted_vaults"] = [v for v in st["deleted_vaults"] if v["name"] != opt("--name")]; save(); sys.exit()
if line.startswith("keyvault list-deleted"): out(st["deleted_vaults"]); sys.exit()
sys.exit("stub: unexpected az call: " + line)
"""


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def contract(**overrides: Any) -> dict[str, Any]:
    """Synthetic APPROVED_FOR_EXECUTION_WINDOW contract, stages 1-8 approved."""
    c: dict[str, Any] = json.loads(CONTRACT.read_text())
    c["status"], c["provisioning_allowed"] = "APPROVED_FOR_EXECUTION_WINDOW", True
    for key in ("cloud_validation", "provisioning", "teardown"):
        c["approvals"][key].update(
            status="APPROVED",
            approval_identity="repository-owner",
            approval_time="2026-11-25T12:00:00Z",
            evidence_sha256="e" * 64,
        )
    c["approved_values"].update(subscription_id=APPROVED, expires_at=EXPIRES)
    c["execution"].update(run_id=RUN, resource_group=RG, window_start_utc=START, window_end_utc=END)
    for key, value in overrides.items():
        target, _, field = key.partition(".")
        if field:
            c[target][field] = value
        else:
            c[key] = value
    return c


def parameters(c: dict[str, Any]) -> bytes:
    v = c["approved_values"]
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


def azstate(**overrides: Any) -> dict[str, Any]:
    rtags = {"purpose": "infrastructure-validation", "owner": "repository-owner"}
    state: dict[str, Any] = {
        "session": SUB,
        "account": SUB,
        "name": "OctoCAT-Agentic-AI",
        "group": {
            "name": RG,
            "tags": GROUP_TAGS,
            "locks": 0,
            "resources": [],
            "deployments": {},
            "budgets": [],
        },
        "ids": IDS,
        "rtags": rtags,
        "budget": BUDGET,
        "extra": [],
        "elsewhere": [],
        "roles": [],
        "deleted_vaults": [],
        "deleted_ws": [],
        "sub_budget": {
            "name": "infraval-uks-tmp01-budget",
            "properties": {"currentSpend": {"amount": 0.0, "unit": "GBP"}},
        },
        "faults": {},
    }
    state.update(overrides)
    return state


class Shell:
    """One Cloud Shell-shaped working directory plus a stateful stub `az`."""

    def __init__(self, tmp: Path, c: dict[str, Any] | None = None, **state: Any) -> None:
        self.tmp, self.work = tmp, tmp / "work"
        self.work.mkdir()
        c = contract() if c is None else c
        reviewed, execution = json.dumps(REVIEWED).encode(), json.dumps(EXECUTION).encode()
        params, whatif = parameters(c), json.dumps(WHATIF).encode()
        if c["status"] != "PREPARATION_ONLY":
            c["execution"].update(
                reviewed_template_sha256=sha(reviewed),
                approved_template_sha256=sha(execution),
                approved_parameters_sha256=sha(params),
                approved_whatif_sha256=sha(whatif),
            )
        for name in ("infra_evidence.py", "infra_subscription_preflight.py", "infra_validation.py"):
            shutil.copy(DEPLOY / name, self.work / name)
        for script in (STAGE7, STAGE8, COST):
            shutil.copy(script, self.work / script.name)
        (self.work / "contract.json").write_text(json.dumps(c))
        (self.work / "reviewed.json").write_bytes(reviewed)
        (self.work / "execution.json").write_bytes(execution)
        (self.work / "parameters.json").write_bytes(params)
        (self.work / "whatif.json").write_bytes(whatif)
        self.sums()
        bin_dir = tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "az").write_text(STUB)
        (bin_dir / "az").chmod(0o755)
        (bin_dir / "python3").symlink_to(sys.executable)
        self.state_path, self.calls_path = tmp / "azstate.json", tmp / "calls.log"
        self.state_path.write_text(json.dumps(azstate(**state)))
        self.calls_path.write_text("")
        self.path = f"{bin_dir}:/usr/bin:/bin:/usr/sbin:/sbin"

    def sums(self) -> None:
        text = "".join(f"{sha((self.work / n).read_bytes())}  {n}\n" for n in FILES)
        (self.work / "SHA256SUMS").write_text(text)

    def edit(self, **changes: Any) -> None:
        st = json.loads(self.state_path.read_text())
        for key, value in changes.items():
            if key.startswith("group."):
                st["group"][key[6:]] = value
            else:
                st[key] = value
        self.state_path.write_text(json.dumps(st))

    def az(self) -> dict[str, Any]:
        return dict(json.loads(self.state_path.read_text()))

    def run(self, script: Path, **env: str) -> tuple[int, str]:
        result = subprocess.run(
            ["/bin/bash", script.name],
            cwd=self.work,
            env={
                "PATH": self.path,
                "AZSTATE": str(self.state_path),
                "CALLS": str(self.calls_path),
                **env,
            },
            capture_output=True,
            text=True,
            check=False,
        )
        output = result.stdout + result.stderr
        assert SUB not in output and OTHER not in output  # the raw ID is never printed
        return result.returncode, output

    def calls(self) -> list[str]:
        return self.calls_path.read_text().splitlines()

    def count(self, prefix: str) -> int:
        return sum(c.startswith(prefix) for c in self.calls())


WRITES = (
    "deployment group create",
    "deployment group cancel",
    "group create",
    "group delete",
    "monitor log-analytics workspace delete",
    "keyvault purge",
    "keyvault delete",
    "rest --method delete",
    "rest --method put",
    "provider register",
    "lock delete",
)


def writes(shell: Shell) -> list[str]:
    return [c for c in shell.calls() if c.startswith(WRITES)]


# --- static checks ---------------------------------------------------------------------------


@pytest.mark.parametrize("script", [STAGE7, STAGE8, COST])
def test_procedures_pass_strict_lint(script: Path) -> None:
    assert lint(script.read_text()) == []


def test_stage7_never_deletes_and_stage8_never_deploys() -> None:
    seven, eight, cost = STAGE7.read_text(), STAGE8.read_text(), COST.read_text()
    for word in (" delete", " purge", " cancel"):
        assert f"az{word}" not in seven and word + " -" not in seven.split("set -E")[1]
    assert "deployment group create" not in eight and "group create" not in eight
    for text in (seven, eight, cost):
        assert "provider register" not in text and "--no-wait" not in text
        assert "az account set" not in text and "--mode Complete" not in text
    for word in (" delete", " purge", " create", " cancel", "--method delete", "--method put"):
        assert word not in cost.split("set -euo pipefail")[1]


def test_subscription_budget_is_only_ever_read() -> None:
    for script in (STAGE7, STAGE8, COST):
        for line in script.read_text().splitlines():
            if "SUB_BUDGET_URL" in line or "infraval-uks-tmp01-budget?" in line:
                assert "--method delete" not in line and "--method put" not in line


# --- stage 7 ---------------------------------------------------------------------------------


def test_stage7_deploys_once_and_pins_targets(tmp_path: Path) -> None:
    shell = Shell(tmp_path)
    code, out = shell.run(STAGE7)
    assert code == 0, out
    assert "STAGE7_DEPLOYED: PASS" in out
    assert writes(shell) == [c for c in shell.calls() if c.startswith("deployment group create")]
    assert shell.count("deployment group create") == 1
    create = next(c for c in shell.calls() if c.startswith("deployment group create"))
    assert "--mode Incremental" in create and "--template-file execution.json" in create
    assert "--parameters @parameters.json" in create and f"-n {RUN}-deploy" in create
    assert shell.calls()[0] == "account show --query id -o tsv"
    assert all(f"--subscription {SUB}" in c for c in shell.calls()[1:])
    targets = json.loads((shell.work / "targets.json").read_text())
    assert (targets["vault"], targets["workspace"], targets["budget"]) == (VAULT, WORKSPACE, BUDGET)
    masked = (shell.work / "evidence-masked/deployment.json").read_text()
    assert SUB not in masked and "<masked>" in masked


@pytest.mark.parametrize(
    "c",
    [
        json.loads(CONTRACT.read_text()),  # the repository contract: PREPARATION_ONLY
        contract(status="APPROVED_FOR_VALIDATION", provisioning_allowed=False),  # stage 6 only
        contract(**{"execution.window_start_utc": (NOW + timedelta(hours=1)).strftime(Z)}),
        contract(**{"execution.window_end_utc": (NOW - timedelta(minutes=1)).strftime(Z)}),
    ],
)
def test_stage7_refuses_without_execution_approval_before_any_az_call(
    tmp_path: Path, c: dict[str, Any]
) -> None:
    for record in ("provisioning",):
        if c["status"] == "APPROVED_FOR_VALIDATION":
            c["approvals"][record].update(
                status="PENDING", approval_identity=None, approval_time=None, evidence_sha256=None
            )
    shell = Shell(tmp_path, c)
    code, _ = shell.run(STAGE7)
    assert code != 0 and shell.calls() == []


def test_stage7_refuses_unapproved_whatif_before_any_az_call(tmp_path: Path) -> None:
    shell = Shell(tmp_path)
    (shell.work / "whatif.json").write_text(json.dumps({**WHATIF, "status": "Other"}))
    code, _ = shell.run(STAGE7)  # manifest mismatch
    assert code != 0 and shell.calls() == []
    shell.sums()  # even with a regenerated manifest the contract's what-if hash refuses
    code, _ = shell.run(STAGE7)
    assert code != 0 and shell.calls() == []


@pytest.mark.parametrize("state", [{"account": OTHER}, {"name": "Other-Subscription"}])
def test_stage7_failed_preflight_stops_before_other_az_calls(
    tmp_path: Path, state: dict[str, Any]
) -> None:
    shell = Shell(tmp_path, **state)
    code, _ = shell.run(STAGE7)
    assert code == 78 and all(c.startswith("account show") for c in shell.calls())


@pytest.mark.parametrize(
    "change",
    [
        {"group": None},
        {"group.tags": {**GROUP_TAGS, "infravalRun": "infraval-other"}},
        {"group.resources": [{"id": IDS["nsg"], "tags": {}}]},
        {"group.locks": 1},
        {"group.deployments": {"x": {"name": "x", "properties": {"provisioningState": "Failed"}}}},
    ],
)
def test_stage7_unexpected_group_state_never_deploys(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    shell = Shell(tmp_path)
    shell.edit(**change)
    code, _ = shell.run(STAGE7)
    assert code != 0 and writes(shell) == []


def test_stage7_second_run_refuses(tmp_path: Path) -> None:
    shell = Shell(tmp_path)
    assert shell.run(STAGE7)[0] == 0
    code, _ = shell.run(STAGE7)
    assert code != 0 and shell.count("deployment group create") == 1


@pytest.mark.parametrize(
    "state",
    [
        {"faults": {"create": "fail"}},
        {"faults": {"state": "Failed"}},
        {"extra": [{"id": f"{PROV}/Microsoft.Storage/storageAccounts/x", "tags": {}}]},
        {"roles": [f"/subscriptions/{SUB}/resourceGroups/{RG}"]},
    ],
)
def test_stage7_failed_or_unexpected_deployment_stops_without_deleting(
    tmp_path: Path, state: dict[str, Any]
) -> None:
    shell = Shell(tmp_path, **state)
    code, out = shell.run(STAGE7)
    assert code != 0 and "STAGE7_STOPPED" in out and "STAGE7_DEPLOYED" not in out
    assert writes(shell) == [c for c in shell.calls() if c.startswith("deployment group create")]


# --- stage 8 ---------------------------------------------------------------------------------


def deployed(tmp_path: Path, **state: Any) -> Shell:
    shell = Shell(tmp_path, **state)
    assert shell.run(STAGE7)[0] == 0
    return shell


def test_stage8_full_teardown_in_order(tmp_path: Path) -> None:
    shell = deployed(tmp_path)
    code, out = shell.run(STAGE8)
    assert code == 0, out
    assert "STAGE8_TEARDOWN_VERIFIED: PASS (WITHIN_EXPIRY)" in out
    order = [c.split(" -")[0] for c in writes(shell)]
    assert order == [
        "deployment group create",
        "rest",
        "monitor log-analytics workspace delete",
        "group delete",
        "keyvault purge",
    ]
    budget_delete = next(c for c in shell.calls() if c.startswith("rest --method delete"))
    assert (
        f"/budgets/{BUDGET}?" in budget_delete and "infraval-uks-tmp01-budget" not in budget_delete
    )
    assert "--force true" in next(c for c in shell.calls() if "workspace delete" in c)
    assert not any("NetworkWatcherRG" in c and "delete" in c for c in shell.calls())
    az = shell.az()
    assert az["group"] is None and az["deleted_vaults"] == [] and az["deleted_ws"] == []
    assert az["sub_budget"]["name"] == "infraval-uks-tmp01-budget"
    assert (shell.work / "teardown-receipt.json").exists()


def test_stage8_refuses_without_teardown_approval_before_any_az_call(tmp_path: Path) -> None:
    shell = deployed(tmp_path)
    c = json.loads((shell.work / "contract.json").read_text())
    c["approvals"]["teardown"].update(
        status="PENDING", approval_identity=None, approval_time=None, evidence_sha256=None
    )
    c["status"], c["provisioning_allowed"] = "APPROVED_FOR_VALIDATION", False
    (shell.work / "contract.json").write_text(json.dumps(c))
    shell.sums()
    before = len(shell.calls())
    code, _ = shell.run(STAGE8)
    assert code != 0 and len(shell.calls()) == before


def test_stage8_partial_deployment_deletes_only_what_exists(tmp_path: Path) -> None:
    shell = Shell(tmp_path, faults={"create": "partial:nsg,vnet"})
    assert shell.run(STAGE7)[0] != 0
    code, out = shell.run(STAGE8)
    assert code == 0, out
    teardown = writes(shell)[1:]
    assert [c.split(" -")[0] for c in teardown] == ["group delete"]


def test_stage8_running_deployment_is_cancelled_first(tmp_path: Path) -> None:
    shell = Shell(tmp_path, faults={"create": "partial:nsg", "partial_state": "Running"})
    stamp = "20261125T130000Z"
    date = tmp_path / "bin" / "date"
    date.write_text(f"#!/bin/sh\nprintf '%s\\n' {stamp}\n")
    date.chmod(0o755)
    assert shell.run(STAGE7)[0] != 0
    code, out = shell.run(STAGE8)
    assert code == 3 and "STAGE8_CANCEL_REQUESTED" in out
    assert [c.split(" -")[0] for c in writes(shell)[1:]] == ["deployment group cancel"]
    (evidence,) = shell.work.glob(f"ev8-{stamp}.????????")
    first_capture = (evidence / "group.json").read_bytes()
    code, out = shell.run(STAGE8)  # rerun after the cancel: the group goes
    assert code == 0, out
    assert shell.az()["group"] is None
    assert len(list(shell.work.glob(f"ev8-{stamp}.????????"))) == 2
    assert (evidence / "group.json").read_bytes() == first_capture


@pytest.mark.parametrize(
    "change",
    [
        {"group.locks": 1},
        {"group.tags": {"purpose": "infrastructure-validation"}},
        {"roles": [f"/subscriptions/{SUB}/resourceGroups/{RG}"]},
    ],
)
def test_stage8_unsafe_state_refuses_without_deleting(
    tmp_path: Path, change: dict[str, Any]
) -> None:
    shell = deployed(tmp_path)
    shell.edit(**change)
    code, _ = shell.run(STAGE8)
    assert code != 0 and writes(shell)[1:] == []


def test_stage8_unexpected_resource_refuses_without_deleting(tmp_path: Path) -> None:
    shell = deployed(tmp_path)
    st = shell.az()
    st["group"]["resources"].append(
        {"id": f"{PROV}/Microsoft.Storage/storageAccounts/x", "tags": st["rtags"]}
    )
    shell.edit(group=st["group"])
    code, _ = shell.run(STAGE8)
    assert code != 0 and writes(shell)[1:] == []


def test_stage8_changed_targets_refuse_without_deleting(tmp_path: Path) -> None:
    shell = deployed(tmp_path)
    targets = json.loads((shell.work / "targets.json").read_text())
    (shell.work / "targets.json").write_text(
        json.dumps({**targets, "vault": "nsvalzzzzzzzzzzzzzkv"})
    )
    code, _ = shell.run(STAGE8)
    assert code != 0 and writes(shell)[1:] == []


def test_stage8_purge_target_in_another_group_is_never_purged(tmp_path: Path) -> None:
    other = f"/subscriptions/{SUB}/resourceGroups/rg-claims-agentic-ai-dev/providers/"
    shell = deployed(tmp_path, faults={"vault_id": other + f"Microsoft.KeyVault/vaults/{VAULT}"})
    code, _ = shell.run(STAGE8)
    assert code != 0 and shell.count("keyvault purge") == 0


def test_stage8_resumes_after_a_failed_purge(tmp_path: Path) -> None:
    shell = deployed(tmp_path, faults={"purge": "fail"})
    code, out = shell.run(STAGE8)
    assert code != 0 and "STAGE8_STOPPED" in out and shell.az()["group"] is None
    shell.edit(faults={})
    code, out = shell.run(STAGE8)  # group absent: verify-only, finishes the pinned purge
    assert code == 0, out
    assert shell.count("group delete") == 1 and shell.count("keyvault purge") == 2
    assert shell.az()["deleted_vaults"] == []


@pytest.mark.parametrize(
    "fault",
    [{"workspace_soft": True}, {"group_delete": "fail"}, {"workspace_delete": "fail"}],
)
def test_stage8_failed_step_stops(tmp_path: Path, fault: dict[str, Any]) -> None:
    shell = deployed(tmp_path)
    shell.edit(faults=fault)
    code, out = shell.run(STAGE8)
    assert code != 0 and "STAGE8_TEARDOWN_VERIFIED" not in out


def test_stage8_missing_subscription_budget_fails_verification(tmp_path: Path) -> None:
    shell = deployed(tmp_path)
    shell.edit(sub_budget=None)
    code, out = shell.run(STAGE8)
    assert code != 0 and "STAGE8_TEARDOWN_VERIFIED" not in out


def test_stage8_absent_group_without_pinned_targets_refuses(tmp_path: Path) -> None:
    shell = Shell(tmp_path)
    shell.edit(group=None)
    code, _ = shell.run(STAGE8)
    assert code != 0 and writes(shell) == []


# --- +24h / +72h cost checks -------------------------------------------------------------------


def torn_down(tmp_path: Path, hours_ago: float) -> Shell:
    shell = deployed(tmp_path)
    assert shell.run(STAGE8)[0] == 0
    stamp = (NOW - timedelta(hours=hours_ago)).strftime(Z)
    (shell.work / "teardown-receipt.json").write_text(json.dumps({"teardown_verified_utc": stamp}))
    return shell


def test_cost_check_passes_after_the_checkpoint(tmp_path: Path) -> None:
    shell = torn_down(tmp_path, 73)
    shell.edit(
        sub_budget={
            "name": "infraval-uks-tmp01-budget",
            "properties": {"currentSpend": {"amount": 0.12, "unit": "GBP"}},
        }
    )
    before = writes(shell)
    for hours in ("24", "72"):
        code, out = shell.run(COST, CHECKPOINT_HOURS=hours)
        assert code == 0, out
        assert f"COST_CHECK_+{hours}h: PASS" in out and "currentSpend=0.12 GBP" in out
    assert writes(shell) == before  # read-only


@pytest.mark.parametrize("hours", ["12", "", "72; true"])
def test_cost_check_needs_a_valid_checkpoint(tmp_path: Path, hours: str) -> None:
    shell = torn_down(tmp_path, 73)
    before = len(shell.calls())
    code, _ = shell.run(COST, CHECKPOINT_HOURS=hours)
    assert code != 0 and len(shell.calls()) == before


def test_cost_check_refuses_before_it_is_due(tmp_path: Path) -> None:
    shell = torn_down(tmp_path, 23)
    before = len(shell.calls())
    code, _ = shell.run(COST, CHECKPOINT_HOURS="24")
    assert code != 0 and len(shell.calls()) == before


@pytest.mark.parametrize(
    "change",
    [
        {
            "sub_budget": {
                "name": "infraval-uks-tmp01-budget",
                "properties": {"currentSpend": {"amount": 2.0, "unit": "GBP"}},
            }
        },
        {
            "sub_budget": {
                "name": "infraval-uks-tmp01-budget",
                "properties": {"currentSpend": {"amount": 0.1, "unit": "USD"}},
            }
        },
        {"sub_budget": None},
        {"elsewhere": [{"id": IDS["kv"], "tags": {}}]},
        {
            "elsewhere": [
                {
                    "id": "/subscriptions/x/resourceGroups/rg-other/providers/A/b/c",
                    "tags": {"purpose": "infrastructure-validation"},
                }
            ]
        },
        {"deleted_vaults": [{"name": VAULT, "properties": {"vaultId": IDS["kv"]}}]},
        {"deleted_ws": [{"name": WORKSPACE}]},
    ],
)
def test_cost_check_flags_residue_or_spend(tmp_path: Path, change: dict[str, Any]) -> None:
    shell = torn_down(tmp_path, 25)
    shell.edit(**change)
    code, out = shell.run(COST, CHECKPOINT_HOURS="24")
    assert code != 0 and "COST_CHECK_" not in out


# --- helper unit checks ------------------------------------------------------------------------


def test_targets_never_include_the_subscription_budget(tmp_path: Path) -> None:
    plan = {
        "decision": "TEARDOWN_PLAN_ONLY",
        "resource_group": RG,
        "run_id": RUN,
        "actions": ["CAPTURE_EVIDENCE", "DELETE_BUDGET:infraval-uks-tmp01-budget", "VERIFY"],
    }
    with pytest.raises(EvidenceError, match="target_name:budget"):
        pin_targets({"deployment_ids": []}, plan, tmp_path / "t.json")


def test_count_scopes_matches_the_group_and_children_only() -> None:
    scopes = [
        f"/subscriptions/x/resourceGroups/{RG}".lower(),
        f"/subscriptions/x/resourceGroups/{RG}/providers/a/b/c".lower(),
        f"/subscriptions/x/resourceGroups/{RG}-other".lower(),
        "/subscriptions/x",
    ]
    assert count_scopes(RG, scopes) == 2
