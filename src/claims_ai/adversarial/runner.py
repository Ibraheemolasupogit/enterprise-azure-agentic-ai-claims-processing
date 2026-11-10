"""Bounded deterministic evaluation; observations never receive expected success labels."""

import asyncio
import socket
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from threading import Lock

from claims_ai.adversarial.application import ApplicationHarness
from claims_ai.adversarial.contracts import (
    CaseResult,
    Observation,
    Target,
    Verdict,
    score,
)
from claims_ai.adversarial.fixtures import load_catalog
from claims_ai.adversarial.identity import identity_probe
from claims_ai.adversarial.runtime import RuntimeHarness
from claims_ai.rules.specification import digest
from claims_ai.workflow.engine import code_fingerprint

_network_lock = Lock()


@contextmanager
def offline_guard() -> Iterator[list[str]]:
    """A guard rejection is harness failure/NOT_TESTED, never an application's blocked attack."""
    with _network_lock:
        attempts: list[str] = []
        connect, bind = socket.socket.connect, socket.socket.bind

        def forbidden(*args: object, **kwargs: object) -> None:
            attempts.append("socket_operation")
            raise RuntimeError("offline evaluation prohibits socket operations")

        socket.socket.connect = forbidden  # type: ignore[method-assign]
        socket.socket.bind = forbidden  # type: ignore[method-assign]
        try:
            yield attempts
        finally:
            socket.socket.connect, socket.socket.bind = connect, bind  # type: ignore[method-assign]


def unavailable(reason: str, *, error: bool = False) -> Observation:
    return Observation(
        execution="NOT_EXECUTED",
        facts={},
        evidence_note="No runtime protection conclusion is drawn.",
        unavailable_reason=reason,
        harness_error=error,
    )


def evaluate(fixture_root: Path, spec_root: Path) -> dict[str, object]:
    catalog = load_catalog(fixture_root)
    rows: list[CaseResult] = []
    application: ApplicationHarness | None = None
    with offline_guard() as attempts, ExitStack() as stack:
        runtime = RuntimeHarness(spec_root)
        for case in catalog.cases:
            before = len(attempts)
            try:
                if case.target == Target.PRODUCTION:
                    observation = unavailable(case.residual_risk)
                elif case.target in {Target.APPLICATION, Target.REVIEW}:
                    if application is None:
                        application = ApplicationHarness(spec_root, stack)
                    observation = (
                        application.review_probe(case)
                        if case.target == Target.REVIEW
                        else application.run(case)
                    )
                elif case.target == Target.IDENTITY:
                    observation = identity_probe(case)
                else:
                    handler = {
                        Target.CONTENT: runtime.content,
                        Target.AGENT: runtime.agent,
                        Target.TOOLS: runtime.tools,
                        Target.MCP: runtime.mcp,
                    }[case.target]
                    observation = asyncio.run(handler(case))
            except Exception as error:
                observation = unavailable(
                    "Harness/setup failure: " + type(error).__name__, error=True
                )
            if len(attempts) != before:
                observation = unavailable(
                    (
                        "A socket operation was attempted; the network guard is not "
                        "runtime protection evidence."
                    ),
                    error=True,
                )
            rows.append(score(case, observation))
        no_outcomes = application is None or all(
            record.current_case.decision is None and record.current_case.assessment is None
            for record in application.fixture.backend._records.values()
        )
    counts = {v.value: sum(row.verdict == v for row in rows) for v in Verdict}
    complete = not attempts and not any(row.observed.harness_error for row in rows)
    no_outcomes = no_outcomes and not any(
        row.observed.facts.get("no_outcome") is False for row in rows
    )
    values: dict[str, object] = {
        "report_version": "claims-adversarial-v1",
        "evaluation_mode": "OFFLINE_SYNTHETIC_RUNTIME_BOUNDARIES",
        "label_status": catalog.label_status,
        "semantic_live_model_resistance": "NOT_TESTED",
        "owasp_mapping": "LLM_TOP10_2025_PINNED",
        "atlas_mapping": "ATLAS_5.6.0_REFERENCE_PINNED_DEPRECATED_SNAPSHOT",
        "catalog_sha256": sha256((fixture_root / "scenarios.json").read_bytes()).hexdigest(),
        "catalog_manifest_sha256": sha256(
            (fixture_root / "manifest.json").read_bytes()
        ).hexdigest(),
        "runtime_sha256": code_fingerprint(),
        "spec_manifest_sha256": sha256((spec_root / "manifest.json").read_bytes()).hexdigest(),
        "python_boundary": "ASGI_AND_DIRECT_RUNTIME_NOT_TCP_OR_BROWSER",
        "framework_version": version("agent-framework-core"),
        "mcp_version": version("mcp"),
        "network_attempts": len(attempts),
        "network_guard_scope": (
            "Python socket.connect/bind instrumentation, not an OS/native egress sandbox."
        ),
        "azure_operations": 0,
        "live_model_calls": 0,
        "operational_outcomes_observed": not no_outcomes,
        "harness_complete": complete,
        "counts": counts,
        "case_count": len(rows),
        "cases": [r.model_dump(mode="json") for r in rows],
        "m8_historical_failures_preserved": ["Q-007", "Q-012", "Q-015", "Q-029"],
        "evidence_normalization": (
            "Semantic attempts and minimized observations; credential bytes, "
            "keys, nonces, volatile timing and opaque transport IDs excluded."
        ),
    }
    return {**values, "report_sha256": digest(values)}
