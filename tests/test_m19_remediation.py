"""Real MCP consumers and outside-directory CLI guards for the two M19 findings."""

import asyncio
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from mcp import Client, types

from claims_ai.adversarial.authoring import contaminated
from claims_ai.adversarial.fixtures import load_catalog
from claims_ai.agent_tools.__main__ import demo_grant
from claims_ai.agent_tools.contracts import ToolName
from claims_ai.agents.__main__ import demo_input
from claims_ai.agents.contracts import AssessmentInput
from claims_ai.mcp_server.client import arguments, checked
from claims_ai.mcp_server.contracts import ServerReply
from claims_ai.mcp_server.server import GovernedMCP
from claims_ai.rules import __main__ as rules_cli

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "data/rules/motor/v1"
ATTACK = next(
    case
    for case in load_catalog(ROOT / "data/security/adversarial/v1").cases
    if case.case_id == "ADV-MCP-09"
)


def sdk_reads(value: AssessmentInput) -> dict[ToolName, types.CallToolResult]:
    async def run() -> dict[ToolName, types.CallToolResult]:
        server = GovernedMCP(value, demo_grant(value, "m19-remediation"))
        async with Client(server.server, mode="legacy") as client:
            return {
                name: await client.call_tool(name.value, arguments(value, name))
                for name in ToolName
            }

    return asyncio.run(run())


@pytest.fixture(scope="module")
def canonical() -> tuple[AssessmentInput, dict[ToolName, types.CallToolResult]]:
    value = demo_input(SPEC, "valid-v1")
    return value, sdk_reads(value)


def envelope(payload: dict[str, object], *, text: str | None = None) -> types.CallToolResult:
    reply = ServerReply.model_validate(payload)
    return types.CallToolResult.model_validate(
        {
            "isError": False,
            "structuredContent": reply.model_dump(mode="json"),
            "content": [{"type": "text", "text": text or reply.model_dump_json()}],
        }
    )


@pytest.mark.parametrize("tool", list(ToolName))
def test_real_sdk_legitimate_results_match_independent_host_sources(
    canonical: tuple[AssessmentInput, dict[ToolName, types.CallToolResult]], tool: ToolName
) -> None:
    value, results = canonical
    reply = checked(results[tool], value=value, tool=tool)
    assert reply.status == "ok" and reply.result is not None
    assert reply.result.tool == tool and reply.final_outcome is None
    assert reply.human_approval_required and not reply.settlement_authorized


@pytest.mark.parametrize("missing", ["all", "snapshot", "tool"])
def test_successful_read_cannot_fall_back_to_unbound_parser(
    canonical: tuple[AssessmentInput, dict[ToolName, types.CallToolResult]], missing: str
) -> None:
    value, results = canonical
    with pytest.raises(ValueError, match="independent trusted context"):
        checked(
            results[ToolName.POLICY],
            value=None if missing in {"all", "snapshot"} else value,
            tool=None if missing in {"all", "tool"} else ToolName.POLICY,
        )


@pytest.mark.parametrize(
    "mutation",
    [
        "content",
        "claim",
        "policy",
        "version",
        "document",
        "artifact",
        "clause",
        "page",
        "line",
        "chunk",
        "packet",
        "omitted",
        "duplicated",
        "partial_text",
        "partial_structured",
    ],
)
def test_consistent_and_partial_policy_manipulation_fails_closed(
    canonical: tuple[AssessmentInput, dict[ToolName, types.CallToolResult]], mutation: str
) -> None:
    value, results = canonical
    original = checked(results[ToolName.POLICY], value=value, tool=ToolName.POLICY)
    payload = original.model_dump(mode="json")
    chunk = payload["result"]["data"]["clauses"][0]
    citation = chunk["clause"]["citation"]
    if mutation in {"content", "partial_text", "partial_structured"}:
        chunk["clause"]["text"] = ATTACK.payload
    elif mutation == "claim":
        chunk["claim_id"] = "NS-CLM-00000000"
    elif mutation in {"policy", "version", "document", "artifact", "clause", "page"}:
        field, replacement = {
            "policy": ("policy_id", "NS-POL-00000000"),
            "version": ("policy_version", "forged-version"),
            "document": ("document_id", "NS-DOC-00000000"),
            "artifact": ("artifact_sha256", "f" * 64),
            "clause": ("clause_id", "R99"),
            "page": ("page", 2),
        }[mutation]
        citation[field] = replacement
    elif mutation == "line":
        chunk["source_line_start"] += 1
        chunk["source_line_end"] += 1
    elif mutation == "chunk":
        chunk["chunk_id"] = "f" * 64
    elif mutation == "packet":
        payload["result"]["packet_sha256"] = "f" * 64
    elif mutation == "omitted":
        payload["result"]["data"]["clauses"].pop()
    else:
        payload["result"]["data"]["clauses"].append(chunk)
    changed = envelope(payload)
    if mutation == "partial_text":
        changed = changed.model_copy(
            update={"structured_content": original.model_dump(mode="json")}
        )
    elif mutation == "partial_structured":
        changed = envelope(payload, text=original.model_dump_json())
    with pytest.raises(ValueError):
        checked(changed, value=value, tool=ToolName.POLICY)


def test_coherent_forgery_rehashing_real_sources_does_not_replace_trusted_context(
    canonical: tuple[AssessmentInput, dict[ToolName, types.CallToolResult]],
) -> None:
    value, results = canonical
    forged = contaminated(value, ATTACK.payload, policy=True)
    result = sdk_reads(forged)[ToolName.POLICY]
    # The attack has coherent source bytes, citations, chunk/index/packet hashes and
    # matching JSON representations. Only the independent host snapshot distinguishes it.
    accepted_under_other_context = checked(result, value=forged, tool=ToolName.POLICY)
    assert ATTACK.payload in accepted_under_other_context.model_dump_json()
    assert accepted_under_other_context != checked(
        results[ToolName.POLICY], value=value, tool=ToolName.POLICY
    )
    with pytest.raises(ValueError, match="trusted source snapshot"):
        checked(result, value=value, tool=ToolName.POLICY)
    # Copying the expected packet hash into an otherwise coherent forgery still
    # cannot replace exact source-derived data comparison.
    payload = accepted_under_other_context.model_dump(mode="json")
    original = checked(results[ToolName.POLICY], value=value, tool=ToolName.POLICY)
    assert original.result is not None
    payload["result"]["packet_sha256"] = original.result.packet_sha256
    with pytest.raises(ValueError, match="trusted source snapshot"):
        checked(envelope(payload), value=value, tool=ToolName.POLICY)


def test_wrong_tool_or_other_real_case_cannot_substitute_a_successful_response(
    canonical: tuple[AssessmentInput, dict[ToolName, types.CallToolResult]],
) -> None:
    value, results = canonical
    with pytest.raises(ValueError, match="trusted source snapshot"):
        checked(results[ToolName.EVIDENCE], value=value, tool=ToolName.POLICY)
    other = demo_input(SPEC, "valid-v2")
    result = sdk_reads(other)[ToolName.POLICY]
    assert checked(result, value=other, tool=ToolName.POLICY).status == "ok"
    with pytest.raises(ValueError, match="trusted source snapshot"):
        checked(result, value=value, tool=ToolName.POLICY)


def test_corrupted_local_source_fails_closed_before_accepting_legitimate_response(
    canonical: tuple[AssessmentInput, dict[ToolName, types.CallToolResult]],
) -> None:
    value, results = canonical
    index = value.rule_request.index
    assert index is not None
    entry = index.entries[0]
    source = entry.sources[0]
    changed = source.model_copy(
        update={"source": source.source.model_copy(update={"title": "CORRUPTED LOCAL SOURCE"})}
    )
    entry = entry.model_copy(update={"sources": (changed, *entry.sources[1:])})
    altered = value.model_copy(
        update={
            "rule_request": value.rule_request.model_copy(
                update={"index": index.model_copy(update={"entries": (entry, *index.entries[1:])})}
            )
        }
    )
    with pytest.raises(ValueError):
        checked(results[ToolName.POLICY], value=altered, tool=ToolName.POLICY)


def cli_command(spec: Path) -> list[str]:
    package = Path(rules_cli.__file__).resolve().parents[2]
    return [
        sys.executable,
        "-I",
        "-B",
        "-c",
        "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.rules',run_name='__main__')",
        str(package),
        "--spec-root",
        str(spec),
    ]


def copied_spec(root: Path) -> Path:
    spec = root / "data/rules/motor/v1"
    spec.parent.mkdir(parents=True)
    shutil.copytree(SPEC, spec)
    return spec


@pytest.mark.parametrize(
    "attack",
    [
        "sibling",
        "spec",
        "traversal",
        "directory_symlink",
        "file_symlink",
        "explicit_root",
        "symlink_spec",
        "existing",
        "symlink_loop",
    ],
)
def test_real_cli_outside_repository_rejects_protected_aliases_without_writes(
    tmp_path: Path,
    attack: str,
) -> None:
    project = tmp_path / "reference"
    spec = copied_spec(project)
    launch = tmp_path / "launch"
    launch.mkdir()
    sibling = project / "data/synthetic/motor/v1"
    sibling.mkdir(parents=True)
    output = sibling / "new-report.json"
    extra: list[str] = []
    if attack == "spec":
        output = spec / "new-report.json"
    elif attack == "traversal":
        output = launch / "../reference/data/synthetic/motor/v1/new-report.json"
    elif attack == "directory_symlink":
        (launch / "alias").symlink_to(sibling, target_is_directory=True)
        output = launch / "alias/new-report.json"
    elif attack == "file_symlink":
        output = launch / "alias.json"
        output.symlink_to(sibling / "new-report.json")
    elif attack == "explicit_root":
        root = tmp_path / "nonstandard-reference"
        root.mkdir()
        output = root / "new-report.json"
        extra = ["--protected-data-root", str(root)]
    elif attack == "symlink_spec":
        # Canonical ancestry has no directory named data; lexical ancestry still
        # identifies the host's conventional data-root symlink.
        project = tmp_path / "canonical-reference"
        spec = project / "rules/v1"
        spec.parent.mkdir(parents=True)
        shutil.copytree(SPEC, spec)
        (launch / "data").symlink_to(project, target_is_directory=True)
        spec = launch / "data/rules/v1"
        output = project / "new-report.json"
    elif attack == "existing":
        output = launch / "preserve.json"
        output.write_text("PRESERVE")
    elif attack == "symlink_loop":
        output = launch / "loop.json"
        output.symlink_to(output)
    before = {p: p.read_bytes() for p in project.rglob("*") if p.is_file()}
    result = subprocess.run(
        [*cli_command(spec), *extra, "--output", str(output)],
        cwd=launch,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1 and "raw inputs omitted" in result.stderr
    assert "Traceback" not in result.stderr and not result.stdout
    assert {p: p.read_bytes() for p in project.rglob("*") if p.is_file()} == before
    if attack == "existing":
        assert output.read_text() == "PRESERVE"
    else:
        assert not output.exists()


@pytest.mark.parametrize("layout", ["conventional", "explicit"])
def test_real_cli_outside_repository_accepts_new_nonprotected_output(
    tmp_path: Path,
    layout: str,
) -> None:
    spec = copied_spec(tmp_path / "reference")
    extra: list[str] = []
    if layout == "explicit":
        spec = tmp_path / "custom-spec"
        shutil.copytree(SPEC, spec)
        root = tmp_path / "custom-data"
        root.mkdir()
        extra = ["--protected-data-root", str(root)]
    launch = tmp_path / "launch"
    launch.mkdir()
    output = tmp_path / "reports/new/report.json"
    before = {p: p.read_bytes() for p in spec.rglob("*") if p.is_file()}
    result = subprocess.run(
        [*cli_command(spec), *extra, "--output", str(output)],
        cwd=launch,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(output.read_text())
    assert len(report["fixtures"]) == 23
    assert report["final_outcomes_created"] == report["settlements_authorized"] == 0
    assert {p: p.read_bytes() for p in spec.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("kind", ["relative", "missing", "file"])
def test_invalid_explicit_data_roots_fail_closed(tmp_path: Path, kind: str) -> None:
    spec = copied_spec(tmp_path / "reference")
    root = tmp_path / "invalid-root"
    if kind == "relative":
        root = Path("relative-data")
    elif kind == "file":
        root.write_text("not a directory")
    output = tmp_path / "new.json"
    result = subprocess.run(
        [*cli_command(spec), "--protected-data-root", str(root), "--output", str(output)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 1 and not output.exists()
