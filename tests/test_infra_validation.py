"""Offline checks for the infrastructure-only Azure validation template (no Azure calls)."""

import copy
import json
import shutil
import socket
import subprocess
import sys
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from deployment.infra_validation import (  # noqa: E402
    APPROVALS,
    CHECKLIST,
    CONTRACT,
    M23_MAIN,
    TEMPLATE,
    ValidationError,
    authorize_execution,
    authorize_validation,
    check_whatif,
    gate_only_difference,
    load_contract,
    plan_teardown,
    refuse_provisioning,
    resource_type,
    sha256,
    validate_contract,
    validate_repository,
    validate_template,
    verify_purge_target,
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
            approval_identity="someone",
            approval_time="2026-11-19T00:00:00Z",
            evidence_sha256="e" * 64,
            status="APPROVED",
        )
    value["approved_values"]["budget_amount"] = 10
    # Even fully approved records never make the false-only repository template deployable.
    with pytest.raises(ValidationError, match="provisioning_refused_preparation_only"):
        refuse_provisioning(value)


def test_incomplete_approval_records_are_rejected() -> None:
    # Records are written explicitly so the test doesn't depend on any live approval state.
    empty = {"approval_identity": None, "approval_time": None, "evidence_sha256": None}
    value = contract()
    value["approvals"]["scope"] = {**empty, "approval_identity": "someone", "status": "APPROVED"}
    with pytest.raises(ValidationError, match="approval_incomplete_record"):
        validate_contract(value)
    value = contract()
    value["approvals"]["scope"] = {**empty, "approval_identity": "someone", "status": "PENDING"}
    with pytest.raises(ValidationError, match="pending_approval_has_values"):
        validate_contract(value)


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


# ---------------------------------------------------------------------------
# Contract-bound authorisation, strict what-if and fail-closed teardown planning.
# Synthetic fixtures only: no compiled artifact, Azure call or credential is used.
# ---------------------------------------------------------------------------

SUB = "/subscriptions/00000000-0000-0000-0000-000000000000"
RG = "rg-claims-infraval-uks-tmp01"
PROV = f"{SUB}/resourceGroups/{RG}/providers"
NAME = "nsval-abc123"
VAULT = "nsvalabc123kv"
IDS = {
    "nsg": f"{PROV}/Microsoft.Network/networkSecurityGroups/{NAME}-nsg",
    "vnet": f"{PROV}/Microsoft.Network/virtualNetworks/{NAME}-vnet",
    "id": f"{PROV}/Microsoft.ManagedIdentity/userAssignedIdentities/{NAME}-id",
    "kv": f"{PROV}/Microsoft.KeyVault/vaults/{VAULT}",
    "ws": f"{PROV}/Microsoft.OperationalInsights/workspaces/{NAME}-logs",
    "diag": f"{PROV}/Microsoft.KeyVault/vaults/{VAULT}/providers/"
    "Microsoft.Insights/diagnosticSettings/vault-audit",
    "budget": f"{PROV}/Microsoft.Consumption/budgets/{NAME}-budget",
}
ALL = ("nsg", "vnet", "id", "kv", "ws", "diag", "budget")
RUN = "infraval-202611201000"
NOW = datetime(2026, 11, 20, 10, 30, tzinfo=UTC)
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
        "provisioningApproved": {"type": "bool", "defaultValue": False, "allowedValues": [False]},
        "logDailyQuotaGb": {"type": "int", "minValue": 1, "maxValue": 5},
    },
    "resources": [{"type": t, "condition": "[parameters('provisioningApproved')]"} for t in TYPES],
}
EXEC: dict[str, Any] = copy.deepcopy(REVIEWED)
EXEC["parameters"]["provisioningApproved"]["allowedValues"] = [False, True]
EXEC["metadata"]["_generator"]["templateHash"] = "2"
REVIEWED_BYTES = json.dumps(REVIEWED).encode()
EXEC_BYTES = json.dumps(EXEC).encode()
VALUES: dict[str, Any] = {
    "location": "uksouth",
    "owner": "owner@example.invalid",
    "expiresAt": "2026-11-20T12:00:00+00:00",
    "budgetAmount": 2,
    "budgetContactEmails": ["owner@example.invalid"],
    "budgetStartDate": "2026-11-01",
    "budgetEndDate": "2026-11-30",
    "logDailyQuotaGb": 1,
    "includeContainerEnvironment": False,
    "provisioningApproved": True,
}


def params_bytes(**overrides: Any) -> bytes:
    values = {**VALUES, **overrides}
    return json.dumps({"parameters": {k: {"value": v} for k, v in values.items()}}).encode()


PARAMS_BYTES = params_bytes()


def whatif(
    *keys: str, change: str = "Create", extra: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {"changes": [{"resourceId": IDS[k], "changeType": change} for k in keys] + (extra or [])}


WHATIF_BYTES = json.dumps(whatif(*ALL)).encode()


def approved(status: str = "APPROVED_FOR_EXECUTION_WINDOW") -> dict[str, Any]:
    c = contract()
    c["status"] = status
    c["provisioning_allowed"] = status == "APPROVED_FOR_EXECUTION_WINDOW"
    for record in c["approvals"].values():
        record.update(
            status="APPROVED",
            approval_identity="owner",
            approval_time="2026-11-20T09:00:00Z",
            evidence_sha256="e" * 64,
        )
    c["approved_values"].update(
        location="uksouth",
        owner="owner@example.invalid",
        expires_at="2026-11-20T12:00:00+00:00",
        budget_amount=2,
        budget_contact_emails=["owner@example.invalid"],
        budget_start_date="2026-11-01",
        budget_end_date="2026-11-30",
        log_daily_quota_gb=1,
        include_container_environment=False,
        resource_group=RG,
        subscription_id="OctoCAT-Agentic-AI",
    )
    c["execution"].update(
        run_id=RUN,
        resource_group=RG,
        reviewed_template_sha256=sha256(REVIEWED_BYTES),
        approved_template_sha256=sha256(EXEC_BYTES),
        approved_parameters_sha256=sha256(PARAMS_BYTES),
        approved_whatif_sha256=sha256(WHATIF_BYTES),
        window_start_utc="2026-11-20T10:00:00+00:00",
        window_end_utc="2026-11-20T12:00:00+00:00",
    )
    return c


def mutated(
    fn: Callable[[dict[str, Any]], object], status: str = "APPROVED_FOR_EXECUTION_WINDOW"
) -> dict[str, Any]:
    c = approved(status)
    fn(c)
    return c


def old_parser(rid: str) -> str:  # the parser from the superseded execution plan
    return "/".join(rid.split("/providers/")[-1].split("/")[:2])


# --- Resource-type parsing ---------------------------------------------------------


@pytest.mark.parametrize(
    ("rid", "expected"),
    [
        (IDS["diag"], "microsoft.insights/diagnosticsettings"),
        (IDS["budget"], "microsoft.consumption/budgets"),
        (IDS["kv"], "microsoft.keyvault/vaults"),
        (f"{IDS['vnet']}/subnets/containers", "microsoft.network/virtualnetworks/subnets"),
        (f"{IDS['kv']}/secrets/leaked", "microsoft.keyvault/vaults/secrets"),
        (f"{SUB}/providers/Microsoft.Consumption/budgets/b", "microsoft.consumption/budgets"),
    ],
)
def test_parser_handles_nested_and_extension_ids(rid: str, expected: str) -> None:
    assert resource_type(rid) == expected


def test_superseded_parser_misclassified_child_resources() -> None:
    assert old_parser(f"{IDS['kv']}/secrets/leaked") == "Microsoft.KeyVault/vaults"
    assert old_parser(f"{IDS['vnet']}/subnets/containers") == "Microsoft.Network/virtualNetworks"


# --- Strict what-if ----------------------------------------------------------------


def test_whatif_accepts_exactly_the_seven_creates() -> None:
    assert len(check_whatif(whatif(*ALL), RG)) == 7


def extra(rid: str, change: str = "Create") -> list[dict[str, str]]:
    return [{"resourceId": rid, "changeType": change}]


@pytest.mark.parametrize(
    ("doc", "code"),
    [
        (whatif(*ALL[:-1]), "missing_types"),
        (whatif(*ALL, extra=extra(f"{IDS['kv']}/secrets/x")), "unexpected_type"),
        (
            whatif(*ALL, extra=extra(f"{PROV}/Microsoft.Network/publicIPAddresses/p")),
            "unexpected_type",
        ),
        (
            whatif(*ALL, extra=extra(f"{PROV}/Microsoft.App/managedEnvironments/{NAME}-cae")),
            "unexpected_type",
        ),
        (whatif(*ALL, change="Modify"), "unexpected_change_type"),
        ({"changes": extra(IDS["budget"], "Unsupported")}, "unexpected_change_type"),
        (whatif(*ALL, extra=extra(IDS["nsg"])), "duplicate_type"),
        (
            {"changes": extra(IDS["diag"].replace("vault-audit", "other"))},
            "diagnostic_setting_target",
        ),
        (
            {"changes": extra(IDS["nsg"].replace(RG, "rg-claims-agentic-ai-dev"))},
            "wrong_resource_group",
        ),
        ({"bad": []}, "whatif_shape"),
    ],
)
def test_whatif_fails_closed(doc: dict[str, Any], code: str) -> None:
    with pytest.raises(ValidationError, match=code):
        check_whatif(doc, RG)


# --- Contract-bound authorisation ----------------------------------------------------


def test_repository_contract_refuses_validation_and_execution() -> None:
    with pytest.raises(ValidationError, match="contract_not_approved_for_validation"):
        authorize_validation(contract(), REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES)
    with pytest.raises(ValidationError, match="contract_not_approved_for_execution"):
        authorize_execution(contract(), REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES, WHATIF_BYTES, NOW)


def test_fully_approved_contract_authorizes_only_the_bound_window() -> None:
    result = authorize_execution(
        approved(), REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES, WHATIF_BYTES, NOW
    )
    assert result["decision"] == "AUTHORIZED_FOR_WINDOW" and result["resource_group"] == RG


@pytest.mark.parametrize(
    ("c", "exec_bytes", "params", "now", "code"),
    [
        (
            mutated(
                lambda c: c["approvals"]["teardown"].update(
                    status="PENDING",
                    approval_identity=None,
                    approval_time=None,
                    evidence_sha256=None,
                )
            ),
            EXEC_BYTES,
            PARAMS_BYTES,
            NOW,
            "approval_incomplete:teardown",
        ),
        (
            mutated(lambda c: c["approved_values"].update(budget_amount=None)),
            EXEC_BYTES,
            PARAMS_BYTES,
            NOW,
            "approved_values_incomplete",
        ),
        (
            mutated(
                lambda c: (
                    c["approved_values"].update(resource_group="rg-claims-agentic-ai-dev"),
                    c["execution"].update(resource_group="rg-claims-agentic-ai-dev"),
                )
            ),
            EXEC_BYTES,
            PARAMS_BYTES,
            NOW,
            "resource_group_not_permitted",
        ),
        (approved(), EXEC_BYTES + b" ", PARAMS_BYTES, NOW, "template_hash_mismatch"),
        (approved(), EXEC_BYTES, params_bytes(budgetAmount=50), NOW, "parameters_hash_mismatch"),
        (
            approved(),
            EXEC_BYTES,
            PARAMS_BYTES,
            datetime(2026, 11, 20, 12, 30, tzinfo=UTC),
            "outside_execution_window",
        ),
        (
            mutated(lambda c: c["execution"].update(window_end_utc="2026-11-20T20:00:00+00:00")),
            EXEC_BYTES,
            PARAMS_BYTES,
            NOW,
            "window_too_long",
        ),
    ],
)
def test_authorization_fails_closed(
    c: dict[str, Any], exec_bytes: bytes, params: bytes, now: datetime, code: str
) -> None:
    with pytest.raises(ValidationError, match=code):
        authorize_execution(c, REVIEWED_BYTES, exec_bytes, params, WHATIF_BYTES, now)


def test_template_changed_beyond_gate_is_refused_even_if_hash_approved() -> None:
    tampered = copy.deepcopy(EXEC)
    tampered["parameters"]["logDailyQuotaGb"]["maxValue"] = 500
    blob = json.dumps(tampered).encode()
    c = mutated(lambda c: c["execution"].update(approved_template_sha256=sha256(blob)))
    with pytest.raises(ValidationError, match="template_differs_beyond_gate"):
        authorize_execution(c, REVIEWED_BYTES, blob, PARAMS_BYTES, WHATIF_BYTES, NOW)


# --- Fail-closed teardown planning -------------------------------------------------

TAG = {"purpose": "infrastructure-validation"}
GROUP: dict[str, Any] = {
    "name": RG,
    "tags": {"purpose": "infrastructure-validation", "infravalRun": RUN},
    "locks": [],
}


def res(*keys: str) -> list[dict[str, Any]]:
    return [{"id": IDS[k], "tags": TAG} for k in keys]


def state(**kw: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "group": GROUP,
        "resources": res("nsg", "vnet", "id", "kv", "ws"),
        "deployment_ids": list(IDS.values()),
        "deployment_state": "Succeeded",
        "budgets": [f"{NAME}-budget"],
    }
    return {**base, **kw}


def test_full_deployment_teardown_order() -> None:
    plan = plan_teardown(approved(), state())
    assert plan["decision"] == "TEARDOWN_PLAN_ONLY" and plan["requires_owner_execution"] is True
    assert plan["actions"] == [
        "CAPTURE_EVIDENCE",
        f"DELETE_BUDGET:{NAME}-budget",
        f"FORCE_DELETE_WORKSPACE:{NAME}-logs",
        f"DELETE_GROUP:{RG}",
        f"VERIFY_PURGE_TARGET_THEN_PURGE_VAULT:{VAULT}",
        "VERIFY",
    ]


def test_partial_failure_and_missing_outputs_still_clean_up_safely() -> None:
    plan = plan_teardown(
        approved(),
        state(
            resources=res("nsg", "vnet"), deployment_ids=None, deployment_state="Failed", budgets=[]
        ),
    )
    assert f"DELETE_GROUP:{RG}" in plan["actions"]
    assert not any(
        a.startswith(("VERIFY_PURGE", "FORCE_DELETE", "DELETE_BUDGET")) for a in plan["actions"]
    )


def test_empty_group_and_absent_group() -> None:
    assert (
        f"DELETE_GROUP:{RG}"
        in plan_teardown(approved(), state(resources=[], budgets=[], deployment_ids=None))[
            "actions"
        ]
    )
    assert plan_teardown(approved(), state(group=None))["decision"] == "VERIFY_ONLY"


def test_running_deployment_is_cancelled_before_any_deletion() -> None:
    assert plan_teardown(approved(), state(deployment_state="Running"))["actions"] == [
        "CANCEL_DEPLOYMENT_THEN_REPLAN"
    ]


@pytest.mark.parametrize(
    ("overrides", "code"),
    [
        ({"group": {**GROUP, "tags": TAG}}, "group_not_created_by_this_run"),
        ({"group": {**GROUP, "tags": {}}}, "group_not_created_by_this_run"),
        ({"group": {**GROUP, "name": "rg-claims-agentic-ai-dev"}}, "group_name_mismatch"),
        ({"group": {**GROUP, "locks": ["CanNotDelete"]}}, "group_has_locks"),
        (
            {
                "resources": res("nsg")
                + [{"id": f"{PROV}/Microsoft.Storage/storageAccounts/s", "tags": TAG}]
            },
            "unexpected_resource",
        ),
        ({"resources": res("nsg") + [{"id": IDS["ws"], "tags": {}}]}, "untagged_resource"),
        (
            {"resources": res("nsg", "vnet"), "deployment_ids": [IDS["nsg"]]},
            "resource_not_in_deployment_record",
        ),
        (
            {
                "resources": res("ws") + [{"id": IDS["ws"] + "2", "tags": TAG}],
                "deployment_ids": None,
            },
            "ambiguous_target",
        ),
        ({"budgets": ["a", "b"]}, "ambiguous_budget"),
    ],
)
def test_teardown_refuses_unsafe_states(overrides: dict[str, Any], code: str) -> None:
    with pytest.raises(ValidationError, match=code):
        plan_teardown(approved(), state(**overrides))


def test_protected_group_can_never_be_planned_for_deletion() -> None:
    c = mutated(lambda c: c["execution"].update(resource_group="rg-claims-agentic-ai-dev"))
    with pytest.raises(ValidationError, match="protected_group"):
        plan_teardown(c, state())


# --- Separated validation vs provisioning, checklist and contract states ------------


def test_validation_approval_never_authorizes_provisioning() -> None:
    c = approved("APPROVED_FOR_VALIDATION")
    result = authorize_validation(c, REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES)
    assert result["decision"] == "AUTHORIZED_FOR_VALIDATION_ONLY"
    assert result["provisioning"] == "NOT_AUTHORIZED"
    with pytest.raises(ValidationError, match="contract_not_approved_for_execution"):
        authorize_execution(c, REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES, WHATIF_BYTES, NOW)


def test_validation_needs_stages_one_to_six_but_not_provisioning() -> None:
    def pend(c: dict[str, Any], key: str) -> dict[str, Any]:
        c["approvals"][key].update(
            status="PENDING", approval_identity=None, approval_time=None, evidence_sha256=None
        )
        return c

    only_validation = mutated(
        lambda c: [pend(c, k) for k in ("provisioning", "teardown", "evidence")],
        "APPROVED_FOR_VALIDATION",
    )
    assert authorize_validation(only_validation, REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES)[
        "decision"
    ]
    no_whatif_approval = mutated(lambda c: pend(c, "cloud_validation"), "APPROVED_FOR_VALIDATION")
    with pytest.raises(ValidationError, match="approval_incomplete:cloud_validation"):
        authorize_validation(no_whatif_approval, REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES)


def test_execution_requires_provisioning_and_teardown_approvals_and_bound_whatif() -> None:
    def pend(key: str) -> dict[str, Any]:
        return mutated(
            lambda c: c["approvals"][key].update(
                status="PENDING", approval_identity=None, approval_time=None, evidence_sha256=None
            )
        )

    for key in ("provisioning", "teardown"):
        with pytest.raises(ValidationError, match=f"approval_incomplete:{key}"):
            authorize_execution(
                pend(key), REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES, WHATIF_BYTES, NOW
            )
    with pytest.raises(ValidationError, match="whatif_hash_mismatch"):
        authorize_execution(
            approved(), REVIEWED_BYTES, EXEC_BYTES, PARAMS_BYTES, WHATIF_BYTES + b" ", NOW
        )
    early = params_bytes(expiresAt="2026-11-20T11:00:00+00:00")
    c = mutated(
        lambda c: (
            c["approved_values"].update(expires_at="2026-11-20T11:00:00+00:00"),
            c["execution"].update(approved_parameters_sha256=sha256(early)),
        )
    )
    with pytest.raises(ValidationError, match="window_beyond_expiry"):
        authorize_execution(c, REVIEWED_BYTES, EXEC_BYTES, early, WHATIF_BYTES, NOW)


def test_checklist_maps_nine_stages_onto_every_approval_exactly_once() -> None:
    assert [stage for stage, _, _ in CHECKLIST] == list(range(1, 10))
    mapped = [key for _, _, keys in CHECKLIST for key in keys]
    assert sorted(mapped) == sorted(APPROVALS) and len(mapped) == len(set(mapped)) == 12
    c = contract()
    c["checklist"][6]["approvals"] = []
    with pytest.raises(ValidationError, match="checklist_mapping"):
        validate_contract(c)


@pytest.mark.parametrize(
    ("fn", "code"),
    [
        (lambda c: c["execution"].update(run_id="x"), "preparation_execution_must_be_null"),
        (
            lambda c: c.update(status="APPROVED_FOR_VALIDATION", provisioning_allowed=True),
            "provisioning_must_be_false",
        ),
        (
            lambda c: c.update(status="APPROVED_FOR_EXECUTION_WINDOW"),
            "provisioning_flag_inconsistent",
        ),
        (
            lambda c: c.update(format="azure-infrastructure-validation-contract-v1"),
            "contract_format",
        ),
    ],
)
def test_contract_states_are_internally_consistent(
    fn: Callable[[dict[str, Any]], object], code: str
) -> None:
    c = contract()
    fn(c)
    with pytest.raises(ValidationError, match=code):
        validate_contract(c)


def test_reviewed_template_must_itself_be_false_only() -> None:
    open_reviewed = json.dumps(EXEC).encode()
    c = mutated(lambda c: c["execution"].update(reviewed_template_sha256=sha256(open_reviewed)))
    with pytest.raises(ValidationError, match="reviewed_gate_not_false_only"):
        authorize_validation(c, open_reviewed, EXEC_BYTES, PARAMS_BYTES)
    assert gate_only_difference(REVIEWED, EXEC) is True


def test_container_environment_parameter_cannot_be_enabled() -> None:
    blob = params_bytes(includeContainerEnvironment=True)
    c = mutated(
        lambda c: (
            c["approved_values"].update(include_container_environment=True),
            c["execution"].update(approved_parameters_sha256=sha256(blob)),
        )
    )
    with pytest.raises(ValidationError, match="parameter_scope"):
        authorize_validation(c, REVIEWED_BYTES, EXEC_BYTES, blob)


@pytest.mark.parametrize(
    ("vault", "deleted_id", "code"),
    [
        (
            VAULT,
            f"{SUB}/resourceGroups/other-rg/providers/Microsoft.KeyVault/vaults/{VAULT}",
            "purge_wrong_group",
        ),
        ("othervault", IDS["kv"], "purge_wrong_name"),
        (VAULT, IDS["ws"], "purge_not_a_vault"),
    ],
)
def test_purge_target_identity_is_exact(vault: str, deleted_id: str, code: str) -> None:
    assert verify_purge_target(approved(), VAULT, IDS["kv"]) == "PURGE_TARGET_VERIFIED"
    with pytest.raises(ValidationError, match=code):
        verify_purge_target(approved(), vault, deleted_id)


def test_teardown_and_purge_require_their_own_approval() -> None:
    c = mutated(
        lambda c: c["approvals"]["teardown"].update(
            status="PENDING", approval_identity=None, approval_time=None, evidence_sha256=None
        )
    )
    with pytest.raises(ValidationError, match="approval_incomplete:teardown"):
        plan_teardown(c, state())
    with pytest.raises(ValidationError, match="approval_incomplete:teardown"):
        verify_purge_target(c, VAULT, IDS["kv"])


def test_repository_gate_stays_false_only_even_with_an_approved_contract(isolated: Path) -> None:
    (isolated / CONTRACT).write_text(json.dumps(approved()))
    result = validate_repository(isolated)
    assert result["repository_gate"] == "FALSE_ONLY"
    assert result["provisioning"] == "REPOSITORY_TEMPLATE_NOT_DEPLOYABLE"
    with pytest.raises(ValidationError, match="provisioning_refused_preparation_only"):
        refuse_provisioning(approved())
    bicep = isolated / TEMPLATE
    bicep.write_text(
        bicep.read_text().replace(
            "@allowed([false])\nparam provisioningApproved",
            "@allowed([false, true])\nparam provisioningApproved",
        )
    )
    with pytest.raises(ValidationError, match="hard_gate_missing"):
        validate_repository(isolated)


def test_cli_validation_and_teardown_paths(tmp_path: Path) -> None:
    files = {
        "c.json": json.dumps(approved("APPROVED_FOR_VALIDATION")).encode(),
        "r.json": REVIEWED_BYTES,
        "e.json": EXEC_BYTES,
        "p.json": PARAMS_BYTES,
    }
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
    script = str(ROOT / "deployment/infra_validation.py")
    base = [
        sys.executable,
        "-I",
        "-B",
        script,
        "--root",
        str(ROOT),
        "--contract",
        str(tmp_path / "c.json"),
    ]
    ok = subprocess.run(
        [
            *base,
            "--authorize-validation",
            "--reviewed-template",
            str(tmp_path / "r.json"),
            "--execution-template",
            str(tmp_path / "e.json"),
            "--parameters",
            str(tmp_path / "p.json"),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert ok.returncode == 0 and json.loads(ok.stdout)["provisioning"] == "NOT_AUTHORIZED"
    (tmp_path / "s.json").write_text(json.dumps(state(group={**GROUP, "tags": {}})))
    refused = subprocess.run(
        [*base, "--plan-teardown", str(tmp_path / "s.json")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert refused.returncode == 78 and "no cloud execution" in refused.stderr
