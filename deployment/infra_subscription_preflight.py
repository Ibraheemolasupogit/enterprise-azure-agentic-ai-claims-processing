"""Fail-closed Azure subscription preflight for the infrastructure validation (stdlib only).

Runs in Azure Cloud Shell on read-only `az account show` output piped through stdin, so the raw
subscription ID is held only in memory. It is never printed, logged or written to a file. Every
outcome is a fixed verdict code; a refusal exits 78.

  # One-off: compute the commitment the owner records (prints only "sha256:<hex>")
  SUB=$(az account show --query id -o tsv)
  az account show --subscription "$SUB" -o json | python3 -I infra_subscription_preflight.py commit

  # Each session, before any other Azure command
  SUB=$(az account show --query id -o tsv)
  az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" \\
    python3 -I infra_subscription_preflight.py check --contract contract.json

  # Offline: every az command in a procedure must carry --subscription "$SUB"
  python3 -I infra_subscription_preflight.py lint PROCEDURE.sh
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

SUBSCRIPTION_NAME = "OctoCAT-Agentic-AI"
DOMAIN = "infraval-subscription-v1:"
ENV_VAR = "INFRAVAL_SUB"
COMMITMENT = re.compile(r"sha256:[0-9a-f]{64}")
GUID = re.compile(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}")
SUBSCRIPTION_FLAG = '--subscription "$SUB"'
BOOTSTRAP = "az account show --query id -o tsv"
FORBIDDEN_COMMANDS = ("az account set", "az login --service-principal")
XTRACE = re.compile(
    r"^\s*(set\s+-[a-zA-Z]*x[a-zA-Z]*|set\s+-o\s+xtrace|bash\s+-[a-zA-Z]*x[a-zA-Z]*)(\s|$)", re.M
)
REFUSED = 78


class PreflightError(Exception):
    """A fail-closed refusal. The message is a fixed code and never contains the raw ID."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise PreflightError(code)


def commitment(subscription_id: str) -> str:
    """Domain-separated SHA-256 commitment of a subscription ID (lower-cased GUID)."""
    require(GUID.fullmatch(subscription_id) is not None, "subscription_id_format")
    digest = hashlib.sha256((DOMAIN + subscription_id.lower()).encode()).hexdigest()
    return f"sha256:{digest}"


def approved_commitment(contract: dict[str, Any]) -> str:
    value = (contract.get("approved_values") or {}).get("subscription_id")
    require(value is not None, "subscription_not_approved")
    require(isinstance(value, str) and COMMITMENT.fullmatch(value) is not None, "approved_format")
    assert isinstance(value, str)
    return value


def _account(text: str) -> dict[str, Any]:
    try:
        account = json.loads(text)
    except json.JSONDecodeError as error:
        raise PreflightError("account_json") from error
    require(isinstance(account, dict), "account_json")
    assert isinstance(account, dict)
    return account


def check(account_text: str, approved: str, session_sub: str | None) -> dict[str, str]:
    """PASS only if the account matches the approved commitment, name and Enabled state, and
    the session's $SUB (used for every --subscription) is that same subscription."""
    require(COMMITMENT.fullmatch(approved) is not None, "approved_format")
    account = _account(account_text)
    actual = account.get("id")
    require(isinstance(actual, str), "account_id_missing")
    assert isinstance(actual, str)
    require(commitment(actual) == approved, "subscription_hash_mismatch")
    require(account.get("name") == SUBSCRIPTION_NAME, "subscription_name_mismatch")
    require(account.get("state") == "Enabled", "subscription_not_enabled")
    require(bool(session_sub), "session_subscription_missing")
    assert session_sub is not None
    require(session_sub.strip().lower() == actual.lower(), "session_subscription_mismatch")
    return {"subscription_preflight": "PASS", "name": SUBSCRIPTION_NAME, "state": "Enabled"}


def _logical_lines(text: str) -> list[tuple[int, str]]:
    """Join backslash continuations; drop blank and full-line comment lines."""
    lines: list[tuple[int, str]] = []
    buffer, start = "", 0
    for number, raw in enumerate(text.splitlines(), 1):
        if not buffer:
            start = number
        if raw.rstrip().endswith("\\"):
            buffer += raw.rstrip()[:-1] + " "
            continue
        joined = (buffer + raw).strip()
        buffer = ""
        if joined and not joined.startswith("#"):
            lines.append((start, joined))
    if buffer.strip():
        lines.append((start, buffer.strip()))
    return lines


def _segment(line: str, start: int) -> str:
    """The az command beginning at `start`, up to an unquoted |, ;, &, ) or end of line."""
    quote = ""
    for index in range(start, len(line)):
        char = line[index]
        if quote:
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char in "|;&)":
            return line[start:index].strip()
    return line[start:].strip()


def lint(text: str) -> list[str]:
    """Violations in a procedure script; an empty list means compliant."""
    violations: list[str] = []
    if GUID.search(text):
        violations.append("raw_guid_literal")
    if XTRACE.search(text):
        violations.append("xtrace_enabled")
    for number, line in _logical_lines(text):
        for match in re.finditer(r"(?:^|(?<=[\s;|&(`]))az(?=\s)", line):
            command = _segment(line, match.start())
            if command == BOOTSTRAP:
                continue
            if command.startswith(FORBIDDEN_COMMANDS):
                violations.append(f"line {number}: forbidden_command")
            elif command.count("--subscription") != 1 or SUBSCRIPTION_FLAG not in command:
                violations.append(f"line {number}: missing_explicit_subscription")
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("commit", help="print the commitment of the account on stdin")
    checker = sub.add_parser("check", help="verify the account on stdin")
    source = checker.add_mutually_exclusive_group(required=True)
    source.add_argument("--contract", type=Path)
    source.add_argument("--approved")
    linter = sub.add_parser("lint", help="check a procedure script offline")
    linter.add_argument("script", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.mode == "commit":
            account = _account(sys.stdin.read())
            require(account.get("name") == SUBSCRIPTION_NAME, "subscription_name_mismatch")
            require(account.get("state") == "Enabled", "subscription_not_enabled")
            print(commitment(str(account.get("id", ""))))
        elif args.mode == "check":
            approved = (
                approved_commitment(json.loads(args.contract.read_text()))
                if args.contract
                else args.approved
            )
            print(json.dumps(check(sys.stdin.read(), approved, os.environ.get(ENV_VAR))))
        else:
            violations = lint(args.script.read_text())
            print(
                json.dumps({"lint": "PASS" if not violations else "FAIL", "violations": violations})
            )
            return 0 if not violations else REFUSED
    except PreflightError as error:
        print(json.dumps({"subscription_preflight": "REFUSED", "reason": str(error)}))
        return REFUSED
    except (OSError, ValueError, TypeError, AttributeError):
        print(json.dumps({"subscription_preflight": "REFUSED", "reason": "invalid_input"}))
        return REFUSED
    return 0


if __name__ == "__main__":
    sys.exit(main())
