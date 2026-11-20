"""Fail-closed evidence helper for the stage 7 and stage 8 procedures (stdlib only, offline).

Runs in Azure Cloud Shell next to `infra_validation.py`, on files that the procedures captured
with read-only `az` commands. It never calls Azure, deletes or deploys. Every refusal exits 78
with a fixed code and never prints a subscription ID.

  state EV_DIR                  assemble the validator's teardown state from captured files
  targets STATE PLAN TARGETS    pin teardown targets once; later runs must match the record
  expect-full PLAN STATE        stage 7: exactly the seven deployed types, deployment Succeeded
  actions PLAN TARGETS          print the plan's actions after checking them against the targets
  get FILE KEY...               print one safe string field
  get-optional FILE KEY         print one safe string field, or "none" if it's absent
  count-ids TARGETS             stdin: JSON list of live IDs; print how many recorded IDs remain
  count-scopes GROUP            stdin: JSON list of role-assignment scopes; print those in GROUP
  mask SRC_DIR DST_DIR          copy *.json with every GUID replaced by "<masked>"
  receipt FILE                  write the teardown-verified UTC time (refuses to overwrite)
  elapsed FILE HOURS            refuse unless HOURS have passed since the receipt
  spend FILE CONTRACT           print the budget's current spend; refuse unless GBP and below
                                the contract's approved budget amount
"""

from __future__ import annotations

import json
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))  # the hash-checked validator copy

from infra_validation import (  # type: ignore[import-not-found]  # noqa: E402
    DEPLOYED_TYPES,
    resource_type,
)

REFUSED = 78
GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
SAFE = re.compile(r"[A-Za-z0-9._:-]{1,90}")
NAMES = {
    "budget": re.compile(r"nsval-[a-z0-9]{13}-budget"),
    "workspace": re.compile(r"nsval-[a-z0-9]{13}-logs"),
    "vault": re.compile(r"nsval[a-z0-9]{13}kv"),
}
SUBSCRIPTION_BUDGET = "infraval-uks-tmp01-budget"
TOP_LEVEL = DEPLOYED_TYPES - {
    "microsoft.insights/diagnosticsettings",
    "microsoft.consumption/budgets",
}
FULL_PLAN = (
    "CAPTURE_EVIDENCE",
    "DELETE_BUDGET:",
    "FORCE_DELETE_WORKSPACE:",
    "DELETE_GROUP:",
    "VERIFY_PURGE_TARGET_THEN_PURGE_VAULT:",
    "VERIFY",
)
ACTION = re.compile(
    r"(CAPTURE_EVIDENCE|VERIFY|VERIFY:group_absent|CANCEL_DEPLOYMENT_THEN_REPLAN"
    r"|(DELETE_BUDGET|FORCE_DELETE_WORKSPACE|DELETE_GROUP|VERIFY_PURGE_TARGET_THEN_PURGE_VAULT)"
    r":([A-Za-z0-9-]+))"
)


class EvidenceError(Exception):
    """A fail-closed refusal with a fixed code."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise EvidenceError(code)


def load(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError(f"unreadable:{path.name}") from error


def build_state(ev: Path) -> dict[str, Any]:
    """The validator's teardown state from captured `az` output (group present)."""
    group, locks, resources = (
        load(ev / "group.json"),
        load(ev / "locks.json"),
        load(ev / "resources.json"),
    )
    deployment, budgets = load(ev / "deployment.json"), load(ev / "budgets.json")
    require(isinstance(group, dict) and isinstance(group.get("name"), str), "group_shape")
    require(isinstance(locks, list) and isinstance(resources, list), "list_shape")
    require(isinstance(budgets, dict) and isinstance(budgets.get("value"), list), "budget_shape")
    props = deployment.get("properties") if isinstance(deployment, dict) else None
    require(isinstance(props, dict), "deployment_shape")
    assert isinstance(props, dict)
    outputs = props.get("outputResources")
    ids = [o["id"] for o in outputs] if isinstance(outputs, list) and outputs else None
    return {
        "group": {
            "name": group["name"],
            "tags": group.get("tags") or {},
            "locks": [lock.get("name", "?") for lock in locks],
        },
        "resources": [{"id": r["id"], "tags": r.get("tags") or {}} for r in resources],
        "deployment_ids": ids,
        "deployment_state": props.get("provisioningState"),
        "budgets": [b["name"] for b in budgets["value"]],
    }


def _plan_names(plan: dict[str, Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for action in plan.get("actions", []):
        match = ACTION.fullmatch(str(action))
        require(match is not None, "unexpected_action")
        assert match is not None
        kind, name = match.group(2), match.group(3)
        key = {
            "DELETE_BUDGET": "budget",
            "FORCE_DELETE_WORKSPACE": "workspace",
            "VERIFY_PURGE_TARGET_THEN_PURGE_VAULT": "vault",
            "DELETE_GROUP": "group",
        }.get(kind or "")
        if key:
            names[key] = name
    return names


def pin_targets(state: dict[str, Any], plan: dict[str, Any], path: Path) -> str:
    """Record the teardown targets once (group present); afterwards they must match."""
    group = plan.get("resource_group")
    names = _plan_names(plan)
    if plan.get("decision") == "VERIFY_ONLY":
        require(path.exists(), "targets_missing_for_absent_group")
        return "TARGETS_FROM_RECORD"
    if plan.get("decision") == "CANCEL_FIRST":  # nothing is deleted; targets pinned on re-plan
        return "TARGETS_DEFERRED"
    require(plan.get("decision") == "TEARDOWN_PLAN_ONLY", "plan_not_teardown")
    for key, pattern in NAMES.items():
        if key in names:
            require(pattern.fullmatch(names[key]) is not None, f"target_name:{key}")
    require(names.get("budget") != SUBSCRIPTION_BUDGET, "subscription_budget_targeted")
    require(names.get("group") == group, "group_mismatch")
    derived = {"resource_group": group, "run_id": plan.get("run_id"), **names}
    if path.exists():
        recorded = load(path)
        require(isinstance(recorded, dict), "targets_shape")
        for key, value in derived.items():
            require(recorded.get(key) == value, f"targets_changed:{key}")
        return "TARGETS_MATCH"
    # A partial deployment may lack some targets or its output record: pin what exists.
    ids = state.get("deployment_ids")
    require(ids is None or isinstance(ids, list), "deployment_record_shape")
    record = {**derived, "deployment_ids": ids or []}
    path.write_text(json.dumps(record, indent=2, sort_keys=True))
    return "TARGETS_RECORDED"


def expect_full(plan: dict[str, Any], state: dict[str, Any]) -> str:
    """Stage 7 post-check: one of each deployed type, all in the record, deployment Succeeded."""
    require(state.get("deployment_state") == "Succeeded", "deployment_not_succeeded")
    actions = plan.get("actions", [])
    require(plan.get("decision") == "TEARDOWN_PLAN_ONLY", "plan_not_teardown")
    require(
        len(actions) == len(FULL_PLAN)
        and all(str(a).startswith(p) for a, p in zip(actions, FULL_PLAN, strict=True)),
        "plan_not_full",
    )
    kinds = [resource_type(i) for i in state.get("deployment_ids") or []]
    require(sorted(kinds) == sorted(DEPLOYED_TYPES), "deployment_types")
    top = sorted(resource_type(r["id"]) for r in state.get("resources", []))
    require(top == sorted(TOP_LEVEL), "group_inventory")
    require(len(state.get("budgets") or []) == 1, "budget_inventory")
    return "INVENTORY_EXACT"


def actions(plan: dict[str, Any], targets: dict[str, Any]) -> list[str]:
    require(plan.get("decision") in ("TEARDOWN_PLAN_ONLY", "VERIFY_ONLY", "CANCEL_FIRST"), "plan")
    found = _plan_names(plan)
    for key, name in found.items():
        expected = targets.get("resource_group" if key == "group" else key)
        require(name == expected, f"action_target_mismatch:{key}")
    return [str(a) for a in plan.get("actions", [])]


def get(path: Path, keys: list[str]) -> str:
    value: Any = load(path)
    for key in keys:
        require(isinstance(value, dict) and key in value, "field_missing")
        value = value[key]
    require(isinstance(value, str) and SAFE.fullmatch(value) is not None, "field_invalid")
    assert isinstance(value, str)
    return value


def _stdin_list() -> list[str]:
    try:
        value = json.loads(sys.stdin.read())
    except json.JSONDecodeError as error:
        raise EvidenceError("stdin_json") from error
    require(isinstance(value, list) and all(isinstance(v, str) for v in value), "stdin_shape")
    return [v.lower().rstrip("/") for v in value]


def count_ids(targets: dict[str, Any], live: list[str]) -> int:
    group = f"/resourcegroups/{str(targets['resource_group']).lower()}/"
    recorded = {str(i).lower().rstrip("/") for i in targets.get("deployment_ids", [])}
    return sum(1 for i in live if i in recorded or group in i + "/")


def count_scopes(group_name: str, scopes: list[str]) -> int:
    require(SAFE.fullmatch(group_name) is not None, "group_name")
    group = f"/resourcegroups/{group_name.lower()}"
    return sum(1 for s in scopes if s.endswith(group) or f"{group}/" in s)


def mask(src: Path, dst: Path) -> int:
    dst.mkdir(mode=0o700, exist_ok=True)
    files = sorted(src.glob("*.json"))
    for path in files:
        (dst / path.name).write_text(GUID.sub("<masked>", path.read_text()))
    return len(files)


def spend(path: Path, limit: float) -> str:
    props = load(path).get("properties", {})
    current = props.get("currentSpend") or {}
    amount, unit = current.get("amount"), current.get("unit")
    if not isinstance(amount, int | float) or isinstance(amount, bool):
        raise EvidenceError("spend_missing")
    require(unit == "GBP", "spend_currency")
    line = f"currentSpend={amount} {unit} (limit {limit:g} GBP)"
    require(float(amount) < limit, "spend_at_or_above_limit")
    return line


def main(argv: list[str]) -> int:
    try:
        require(len(argv) >= 1, "usage")
        mode, args = argv[0], argv[1:]
        if mode == "state":
            print(json.dumps(build_state(Path(args[0])), indent=2, sort_keys=True))
        elif mode == "targets":
            print(pin_targets(load(Path(args[0])), load(Path(args[1])), Path(args[2])))
        elif mode == "expect-full":
            print(expect_full(load(Path(args[0])), load(Path(args[1]))))
        elif mode == "actions":
            targets = load(Path(args[1])) if Path(args[1]).exists() else {}
            print(" ".join(actions(load(Path(args[0])), targets)))
        elif mode == "get":
            print(get(Path(args[0]), args[1:]))
        elif mode == "get-optional":
            print(get(Path(args[0]), args[1:2]) if args[1] in load(Path(args[0])) else "none")
        elif mode == "count-ids":
            print(count_ids(load(Path(args[0])), _stdin_list()))
        elif mode == "count-scopes":
            print(count_scopes(args[0], _stdin_list()))
        elif mode == "mask":
            print(f"masked_files={mask(Path(args[0]), Path(args[1]))}")
        elif mode == "receipt":
            path = Path(args[0])
            require(not path.exists(), "receipt_exists")
            stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            path.write_text(json.dumps({"teardown_verified_utc": stamp}))
            print(f"teardown_verified_utc={stamp}")
        elif mode == "elapsed":
            verified = datetime.fromisoformat(get(Path(args[0]), ["teardown_verified_utc"]))
            due = verified + timedelta(hours=int(args[1]))
            require(datetime.now(UTC) >= due, "too_early")
            print(f"checkpoint=+{int(args[1])}h due={due.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        elif mode == "spend":
            limit = load(Path(args[1]))["approved_values"]["budget_amount"]
            require(isinstance(limit, int) and not isinstance(limit, bool) and limit > 0, "limit")
            print(spend(Path(args[0]), float(limit)))
        else:
            raise EvidenceError("usage")
    except EvidenceError as error:
        print(json.dumps({"evidence": "REFUSED", "reason": str(error)}), file=sys.stderr)
        return REFUSED
    except (IndexError, KeyError, TypeError, ValueError, AttributeError, OSError):
        print(json.dumps({"evidence": "REFUSED", "reason": "invalid_input"}), file=sys.stderr)
        return REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
