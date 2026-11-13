"""Deterministic canonical reports plus separately retained real local SDK telemetry."""

import json
import platform
from hashlib import sha256
from importlib import metadata
from pathlib import Path

from claims_ai.quality_ops.alerts import alert_controls, check_alerts, dashboard, load_specs
from claims_ai.quality_ops.candidate import BASELINE
from claims_ai.quality_ops.evaluation import (
    CANDIDATE_PIN,
    evaluate_development,
    pending_cases,
    require_independent_scoring,
    summarize,
)
from claims_ai.quality_ops.operational_authority import NS
from claims_ai.quality_ops.operations import exercise
from claims_ai.quality_ops.prediction_access import bounded_bytes
from claims_ai.quality_ops.telemetry import Telemetry
from claims_ai.rules.specification import digest, load_specification
from claims_ai.workflow.engine import code_fingerprint


def operational_input_manifest(root: Path) -> dict[str, object]:
    specification = load_specification(root)
    return {
        "files": {
            name: sha256(bounded_bytes(root / name, 131072)).hexdigest()
            for name in ("manifest.json", "specification.json", "scenarios.json")
        },
        "schema_version": specification.schema_version,
        "specification_version": specification.version,
        "rule_engine_version": specification.engine_version,
        "policy_versions": sorted(t.policy_version for t in specification.terms),
        "policy_status": specification.status,
        "index_version": "source_rebuilt_local_lexical_not_azure",
    }


def evaluate(
    candidate_root: Path,
    specification_root: Path,
    operations_root: Path,
    *,
    exercise_operations: bool = True,
    score_independent: bool = False,
    review_record: object = None,
) -> tuple[dict[str, object], dict[str, object]]:
    if score_independent:
        require_independent_scoring(review_record)
    telemetry = Telemetry()
    child_spans: list[object] = []
    try:
        with telemetry.boundary("evaluation", NS):
            candidates = pending_cases(candidate_root)
            with telemetry.boundary("prediction", NS):
                development = evaluate_development()
            alert_spec, dashboard_spec = load_specs(operations_root)
            if exercise_operations:
                operational, child_spans = exercise(specification_root, telemetry)
            else:
                operational = {"rows": [], "counts": {"PASS": 0, "FAIL": 0}, "signals": {}}
        signals = operational["signals"]
        if not isinstance(signals, dict):
            raise ValueError("operational signal protocol")
        controls = alert_controls(alert_spec)
        health = telemetry.canonical()
        complete = exercise_operations and all(row.verdict != "NOT_TESTED" for row in development)
        counts = operational["counts"]
        if not isinstance(counts, dict):
            raise ValueError("operational evidence protocol")
        failed = (
            counts["FAIL"] != 0
            or any(not row["positive"] or not row["negative"] for row in controls)
            or any(
                health[k] != 0
                for k in ("dropped", "export_failures", "metric_drops", "instrumentation_failures")
            )
            or any(row.verdict == "FAIL" for row in development)
        )
        status = "NOT_TESTED" if not complete else "FAIL" if failed else "PASS"
        versions = {
            name: metadata.version(name)
            for name in (
                "agent-framework-core",
                "annotated-doc",
                "annotated-types",
                "anyio",
                "attrs",
                "cffi",
                "click",
                "cryptography",
                "fastapi",
                "h11",
                "httpcore2",
                "httpx2",
                "idna",
                "jsonschema",
                "jsonschema-specifications",
                "mcp",
                "mcp-types",
                "msgspec",
                "opentelemetry-api",
                "opentelemetry-sdk",
                "opentelemetry-semantic-conventions",
                "pycparser",
                "pydantic",
                "pydantic-core",
                "pydantic-settings",
                "pyjwt",
                "python-dotenv",
                "python-multipart",
                "pyyaml",
                "referencing",
                "regex",
                "rpds-py",
                "sse-starlette",
                "starlette",
                "tenacity",
                "truststore",
                "typing-extensions",
                "typing-inspection",
                "uvicorn",
            )
        }
        gates = json.loads(bounded_bytes(candidate_root / "gates.json", 65536))
        report: dict[str, object] = {
            "format": "m22-offline-evaluation-v1",
            "engineering_status": status,
            "harness_complete": complete,
            "benchmark_status": "PENDING_REVIEW",
            "independent_review_approved": False,
            "actual_insurance_authority": False,
            "manifest": {
                "baseline_revision": BASELINE,
                "runtime_sha256": code_fingerprint(),
                "candidate_manifest_sha256": CANDIDATE_PIN,
                "gates_sha256": digest(gates),
                "sdk_environment": versions,
                "dependency_inventory_sha256": digest(versions),
                "operational_inputs": operational_input_manifest(specification_root),
                "review_record_sha256": None,
                "pending_review_templates_sha256": sha256(
                    bounded_bytes(candidate_root / "reviews/templates.json", 1048576)
                ).hexdigest(),
                "evaluated_schema_version": "m22-offline-evaluation-v1",
                "evaluator_version": "m22-offline-engineering-v1",
                "python_version": platform.python_version(),
                "model_version": None,
                "prompt_sha256": None,
                "inference_parameters": {},
                "repetition": "deterministic_two_source_one_wheel_evidence",
                "alerts_sha256": digest(alert_spec.model_dump(mode="json")),
                "dashboard_sha256": digest(dashboard_spec.model_dump(mode="json")),
                "development_repetition": "deterministic_native_parser_not_model_quality",
                "canonical_exclusions": [
                    "trace_id",
                    "span_id",
                    "parent_span_id",
                    "correlation_id",
                    "duration_ms",
                ],
            },
            "candidate": {
                "cases": [r.model_dump(mode="json") for r in candidates],
                "cohorts": summarize(candidates),
                "counts": {"NOT_TESTED": 60},
            },
            "development": {
                "classification": "SIMULATED_DEVELOPMENT_NOT_INDEPENDENT",
                "cases": [r.model_dump(mode="json") for r in development],
                "cohorts": summarize(development),
            },
            "independent_quality": {
                m["metric_id"]: {
                    "status": "NOT_TESTED",
                    "value": None,
                    "reason": "No independent approval; live/human capability unavailable",
                }
                for m in gates["metrics"]
            },
            "operational_controls": operational,
            "telemetry": health,
            "alerts": check_alerts(alert_spec, signals),
            "alert_controls": controls,
            "dashboard": dashboard(dashboard_spec, signals),
            "external_model_calls": 0,
            "azure_operations": 0,
            "remote_export": "DISABLED",
            "historical_m19_baseline": {"PASS": 80, "FAIL": 0, "NOT_TESTED": 8},
        }
        report["report_sha256"] = digest(report)
        raw = telemetry.raw()
        raw["child_process_spans"] = child_spans
        raw["canonical_report_sha256"] = report["report_sha256"]
        return report, raw
    finally:
        telemetry.close()
