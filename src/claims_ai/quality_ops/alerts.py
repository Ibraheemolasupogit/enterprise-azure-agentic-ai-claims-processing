"""Versioned local snapshot dashboard/alerts, no remote query or notification delivery."""

from pathlib import Path
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from claims_ai.models import Contract
from claims_ai.quality_ops.prediction_access import bounded_bytes

Signal = Literal[
    "dependency_failures",
    "storage_failures",
    "stale_denials",
    "outbox_dead",
    "export_failures",
    "telemetry_drops",
    "tool_denials",
    "review_backlog",
]


class Alert(Contract):
    alert_id: str
    signal: Signal
    threshold: Annotated[int, Field(strict=True, ge=1, le=1000000)]
    owner: Literal["operator", "security_reviewer", "supervisor"]
    severity: Literal["warning", "critical"]
    runbook: str
    window: Literal["current_local_snapshot"] = "current_local_snapshot"


class AlertSpec(Contract):
    format: Literal["m22-alerts-v1"] = "m22-alerts-v1"
    classification: Literal["LOCAL_SYNTHETIC_NOT_PRODUCTION_SLO"]
    rules: Annotated[tuple[Alert, ...], Field(min_length=1, max_length=16)]

    @model_validator(mode="after")
    def unique_rules(self) -> Self:
        if len({a.alert_id for a in self.rules}) != len(self.rules):
            raise ValueError("duplicate alert")
        if any(not a.runbook.startswith("docs/operations/m22-runbooks.md#") for a in self.rules):
            raise ValueError("invalid local runbook")
        return self


class Panel(Contract):
    panel_id: str
    signal: Signal
    unit: Literal["count"] = "count"


class DashboardSpec(Contract):
    format: Literal["m22-dashboard-v1"] = "m22-dashboard-v1"
    panels: Annotated[tuple[Panel, ...], Field(min_length=1, max_length=16)]
    unavailable: Literal["null_not_zero"] = "null_not_zero"


def load_specs(root: Path) -> tuple[AlertSpec, DashboardSpec]:
    return (
        AlertSpec.model_validate_json(bounded_bytes(root / "alerts.json", 65536)),
        DashboardSpec.model_validate_json(bounded_bytes(root / "dashboard.json", 65536)),
    )


def check_alerts(spec: AlertSpec, signals: dict[str, int]) -> list[dict[str, object]]:
    if any(type(v) is not int or not 0 <= v <= 1000000 for v in signals.values()):
        raise ValueError("invalid local signal")
    return [
        {
            "alert_id": a.alert_id,
            "owner": a.owner,
            "severity": a.severity,
            "runbook": a.runbook,
            "observed": signals.get(a.signal),
            "status": "NOT_TESTED"
            if a.signal not in signals
            else ("TRIGGERED" if signals[a.signal] >= a.threshold else "CLEAR"),
        }
        for a in spec.rules
    ]


def alert_controls(spec: AlertSpec) -> list[dict[str, object]]:
    rows = []
    for rule in spec.rules:
        positive = check_alerts(spec, {rule.signal: rule.threshold})
        negative = check_alerts(spec, {rule.signal: rule.threshold - 1})
        rows.append(
            {
                "alert_id": rule.alert_id,
                "execution": "SIMULATED_BOUNDARY_INPUTS",
                "positive": next(
                    r["status"] == "TRIGGERED" for r in positive if r["alert_id"] == rule.alert_id
                ),
                "negative": next(
                    r["status"] == "CLEAR" for r in negative if r["alert_id"] == rule.alert_id
                ),
            }
        )
    return rows


def dashboard(spec: DashboardSpec, signals: dict[str, int]) -> dict[str, object]:
    return {
        "format": spec.format,
        "panels": [
            {"panel_id": p.panel_id, "value": signals.get(p.signal), "unit": p.unit}
            for p in spec.panels
        ],
        "independent_quality": None,
        "live_model_quality": None,
        "gbp_cost": None,
        "cloud_ingestion": "DISABLED",
    }
