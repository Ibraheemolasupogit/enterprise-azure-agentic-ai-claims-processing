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

  # Offline: a procedure must be fail-closed and verify the subscription before any Azure call
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
STRICT_MODE = "set -euo pipefail"
BOOTSTRAP_ASSIGNMENT = "SUB=$(az account show --query id -o tsv)"
PREFLIGHT = (
    'az account show --subscription "$SUB" -o json | INFRAVAL_SUB="$SUB" '
    "python3 -I infra_subscription_preflight.py check --contract contract.json"
)
READ_VERBS = frozenset({"show", "list", "exists", "show-deleted", "list-deleted"})
AZ = re.compile(r"(?:^|(?<=[\s;|&(`]))az(?=\s)")
# Patterns below run on quote-masked lines, so quoted text (JMESPath, Python) can't trip them.
VERIFICATION = re.compile(r"(?:^|(?<=[\s;|&(`]))(?:az|test|\[\[?|python3|sha256sum)(?=\s)")
CONDITIONAL = re.compile(r"^(?:if|elif|while|until|!)(?=\s)")
WEAK_TEST = re.compile(
    r"(?:^|(?<=[\s;&|(`]))(?:test|\[\[?)\s+(?:!|-[zn])(?=\s)"
    r"|(?:^|\s)!=(?=\s)|==?\s*(?:\"\"|'')(?=\s|$|\))"
)
STRICT_OFF = re.compile(r"(?:^|[;&|(]\s*)set\s+\+")
SUB_WRITE = re.compile(
    r"(?:^|(?<=[\s;&|(]))(?:(?:export|local|readonly|typeset|declare(?:\s+-\w+)?)\s+)?SUB="
    r"|(?:^|(?<=[\s;&|(]))(?:unset|read)\s[^;&|]*\bSUB\b"
)
MASKED_SUBSTITUTION = re.compile(
    r"(?:^|(?<=[\s;&|(]))(?:export|local|readonly|typeset|declare)\s[^;&|]*=\$\("
)


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


def _mask_quotes(line: str) -> tuple[str, bool]:
    """Replace quoted text with "_" but keep command substitutions inside double quotes as
    shell code, so operators in JMESPath or Python strings are ignored. Returns the masked line
    and whether every quote and substitution was closed."""
    out: list[str] = []
    stack = ["cmd"]
    index = 0
    while index < len(line):
        char, top = line[index], stack[-1]
        if top == "sq":
            out.append("'" if char == "'" else "_")
            if char == "'":
                stack.pop()
        elif char == "\\":
            out.append("__" if top == "dq" else line[index : index + 2])
            index += 2
            continue
        elif line.startswith("$(", index):
            stack.append("cmd")
            out.append("$(")
            index += 2
            continue
        elif top == "dq":
            out.append('"' if char == '"' else "_")
            if char == '"':
                stack.pop()
        elif char in "'\"":
            stack.append("sq" if char == "'" else "dq")
            out.append(char)
        elif char == "(":
            stack.append("cmd")
            out.append(char)
        elif char == ")" and len(stack) > 1:
            stack.pop()
            out.append(char)
        else:
            out.append(char)
        index += 1
    return "".join(out), stack == ["cmd"]


def _az_commands(line: str) -> list[str]:
    return [_segment(line, match.start()) for match in AZ.finditer(line)]


def _is_write(command: str) -> bool:
    """Conservative: any az command whose verb isn't a known read verb counts as a write."""
    words = []
    for word in command.split()[1:]:
        if word.startswith("-"):
            break
        words.append(word)
    return not words or words[-1] not in READ_VERBS


def lint_commands(text: str) -> list[str]:
    """Command-level rules only: explicit --subscription "$SUB" on every az command, no
    az account set, no shell tracing, no GUID literal. Enough for the one-off read-only commit
    snippet; every procedure must pass the strict `lint`."""
    violations: list[str] = []
    if GUID.search(text):
        violations.append("raw_guid_literal")
    if XTRACE.search(text):
        violations.append("xtrace_enabled")
    for number, line in _logical_lines(text):
        for command in _az_commands(line):
            if command == BOOTSTRAP:
                continue
            if command.startswith(FORBIDDEN_COMMANDS):
                violations.append(f"line {number}: forbidden_command")
            elif command.count("--subscription") != 1 or SUBSCRIPTION_FLAG not in command:
                violations.append(f"line {number}: missing_explicit_subscription")
    return violations


def lint(text: str) -> list[str]:
    """Violations in a procedure script; an empty list means compliant. Adds to `lint_commands`:

    - the first statement is exactly `set -euo pipefail`, and it's never relaxed;
    - $SUB is assigned once, by the bootstrap, and never reassigned, read or unset;
    - the exact preflight `check` runs after the bootstrap and before every other az command,
      so before the first Azure write;
    - fail-closed verification: no az, test, python3 or sha256sum statement is a condition
      (if/while/until/!) or part of an && / || list; no test can pass on empty output
      (test !, test -z, test -n, !=, = ""); no `local`/`export` masks a failing
      substitution; no --no-wait.
    """
    violations = lint_commands(text)
    lines = _logical_lines(text)
    if not lines or " ".join(lines[0][1].split()) != STRICT_MODE:
        violations.append("missing_strict_mode")
    bootstrap_seen = preflight_seen = False
    for number, line in lines:
        normalised = " ".join(line.split())
        masked, balanced = _mask_quotes(line)
        if not balanced:
            violations.append(f"line {number}: unbalanced_quotes")
        if STRICT_OFF.search(masked):
            violations.append(f"line {number}: strict_mode_disabled")
        if MASKED_SUBSTITUTION.search(masked):
            violations.append(f"line {number}: masked_substitution")
        if normalised == BOOTSTRAP_ASSIGNMENT:
            if bootstrap_seen:
                violations.append(f"line {number}: sub_reassigned")
            bootstrap_seen = True
        elif SUB_WRITE.search(masked):
            violations.append(f"line {number}: sub_reassigned")
        if VERIFICATION.search(masked):
            if CONDITIONAL.search(masked.lstrip()):
                violations.append(f"line {number}: conditional_verification")
            if "||" in masked or "&&" in masked:
                violations.append(f"line {number}: failure_suppressed")
            if WEAK_TEST.search(masked):
                violations.append(f"line {number}: weak_verification")
        if normalised == PREFLIGHT:
            if not bootstrap_seen:
                violations.append(f"line {number}: preflight_before_bootstrap")
            preflight_seen = True
            continue
        for command in _az_commands(line):
            if "--no-wait" in command.split():
                violations.append(f"line {number}: async_operation")
            if command == BOOTSTRAP:
                if normalised != BOOTSTRAP_ASSIGNMENT:
                    violations.append(f"line {number}: bootstrap_not_assigned")
            elif not preflight_seen:
                kind = "write" if _is_write(command) else "az"
                violations.append(f"line {number}: {kind}_before_preflight")
    if not bootstrap_seen:
        violations.append("bootstrap_missing")
    if not preflight_seen:
        violations.append("preflight_missing")
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
