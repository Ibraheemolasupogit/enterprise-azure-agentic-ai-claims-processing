"""Offline engineering infrastructure; no candidate review or release-quality claim."""

import json
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
from opentelemetry import trace
from opentelemetry.sdk.metrics.export import Histogram
from opentelemetry.trace import Status, StatusCode
from pydantic import ValidationError

from claims_ai.quality_ops.alerts import alert_controls, check_alerts, dashboard, load_specs
from claims_ai.quality_ops.development_inputs import inputs
from claims_ai.quality_ops.evaluation import (
    ScoringNotAuthorised,
    evaluate_development,
    pending_cases,
    predict_development,
    require_independent_scoring,
    summarize,
)
from claims_ai.quality_ops.operational_contracts import DevelopmentInput, DevelopmentPrediction
from claims_ai.quality_ops.telemetry import (
    BOUNDARIES,
    LocalSink,
    Telemetry,
    extract_parent,
    inject_parent,
)

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = ROOT / "data/evaluation/m22/v1"
OPERATIONS = ROOT / "data/operations/m22/v1"
CORRELATION = UUID("22222222-2222-4222-8222-222222222222")
SECRET = "Bearer private-token; NARRATIVE=private-loss; tid=private-tenant"


@pytest.mark.parametrize(
    "approval", [None, True, {"status": "APPROVED"}, {"signature": "invented"}, "approved.json"]
)
def test_unconfigured_independent_review_never_accepts_claimed_approval(approval: object) -> None:
    with pytest.raises(ScoringNotAuthorised, match="unconfigured"):
        require_independent_scoring(approval)


def test_all_candidates_and_cohorts_remain_pending_without_published_rates() -> None:
    rows = pending_cases(CANDIDATES)
    assert len(rows) == 60 and all(r.verdict == "NOT_TESTED" for r in rows)
    assert all(r.correct_fields is None and r.classification == "PENDING_REVIEW" for r in rows)
    cohorts = summarize(rows)
    assert [r["cases"] for r in cohorts.values()] == [15, 10, 10, 10, 10, 5]  # type: ignore[index]
    assert all(r["rate"] is r["numerator"] is None for r in cohorts.values())  # type: ignore[index]


def test_development_predictions_are_real_parser_outputs_but_explicitly_simulated() -> None:
    values = predict_development(inputs())
    rows = evaluate_development(values)
    assert len(rows) == 6 and all(r.verdict == "PASS" for r in rows)
    assert all(r.classification == "SIMULATED_DEVELOPMENT" for r in rows)
    assert values[2].fields["currency"] is None
    assert all("NOTE" not in p.fields and "TOKEN" not in p.fields for p in values)


def test_missing_development_predictions_stay_in_eligible_denominators() -> None:
    rows = evaluate_development(())
    assert all(r.verdict == "FAIL" and r.correct_fields == 0 for r in rows)
    assert sum(r.eligible_fields for r in rows) == sum(r.missing_predictions for r in rows) == 30


def test_harness_error_is_not_evidence_of_a_blocked_attack() -> None:
    rows = evaluate_development((), harness_error=True)
    assert all(r.verdict == "NOT_TESTED" and r.correct_fields is None for r in rows)
    assert all("harness_error" in r.failures for r in rows)


@pytest.mark.parametrize("field", ["cohort", "reference", "expected", "approval", "path"])
def test_public_development_inputs_reject_reference_or_filesystem_fields(field: str) -> None:
    with pytest.raises(ValidationError):
        DevelopmentInput.model_validate({**inputs()[0].model_dump(), field: "untrusted"})


def test_duplicate_or_foreign_predictions_are_rejected() -> None:
    value = predict_development(inputs()[:1])[0]
    with pytest.raises(ValueError, match="roster"):
        evaluate_development((value, value))
    with pytest.raises(ValueError, match="roster"):
        evaluate_development((DevelopmentPrediction(case_id="DEV-999", fields=value.fields),))


def test_real_sdk_traces_and_metrics_are_local_and_do_not_change_global_providers() -> None:
    original = trace.get_tracer_provider()
    telemetry = Telemetry()
    with telemetry.boundary("workflow", CORRELATION):
        with telemetry.boundary("policy", CORRELATION):
            pass
    raw = telemetry.raw()
    assert isinstance(raw["spans"], list)
    assert len(raw["spans"]) == 2
    records = telemetry.sink.records
    child, parent = records
    assert child["parent_span_id"] == parent["span_id"]
    assert child["trace_id"] == parent["trace_id"]
    assert any(r["name"] == "claims.operations" for r in telemetry.metrics())
    sdk_data = telemetry.reader.get_metrics_data()
    assert sdk_data is not None
    histograms = [
        metric.data
        for r in sdk_data.resource_metrics
        for s in r.scope_metrics
        for metric in s.metrics
        if isinstance(metric.data, Histogram)
    ]
    assert histograms and all(p.sum > 0 for h in histograms for p in h.data_points)
    telemetry.close()
    assert trace.get_tracer_provider() is original


def test_sdk_egress_scrubs_attributes_exceptions_events_and_environment(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setenv("OTEL_RESOURCE_ATTRIBUTES", "credential=" + SECRET)
    t = Telemetry()
    with t.boundary("workflow", CORRELATION):
        with pytest.raises(ValueError):
            with t.boundary("agent", CORRELATION):
                raise ValueError(SECRET)
    span = t.tracer.start_span(
        "policy",
        attributes={
            "correlation_id": str(CORRELATION),
            "result": "ok",
            "authorization": SECRET,
            "subject": SECRET,
            "narrative": SECRET,
        },
    )
    span.add_event(SECRET, {"payload": SECRET})
    span.set_status(Status(StatusCode.ERROR, SECRET))
    span.end()
    t.counter.add(1, {"boundary": SECRET, "result": "ok", "authorization": SECRET})
    serialized = json.dumps(t.raw())
    assert SECRET not in serialized and SECRET not in caplog.text
    assert "authorization" not in serialized and "narrative" not in serialized
    assert t.metric_drops > 0
    t.close()


def test_exporter_exception_does_not_escape_log_sensitive_details_or_leak_context(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    t = Telemetry()

    def fail(*args: object) -> None:
        raise RuntimeError(SECRET)

    monkeypatch.setattr(t.sink, "export", fail)
    actions = []
    with t.boundary("outcome.commit", CORRELATION):
        actions.append("business-work")
    assert actions == ["business-work"] and t.sink.export_failures == 1
    assert not trace.get_current_span().get_span_context().is_valid
    assert SECRET not in json.dumps(t.raw()) and SECRET not in caplog.text
    t.close()


def test_business_exceptions_propagate_unchanged_without_payload_capture() -> None:
    t = Telemetry()
    error = ValueError(SECRET)
    with pytest.raises(ValueError) as caught:
        with t.boundary("outcome.commit", CORRELATION):
            raise error
    assert caught.value is error and SECRET not in json.dumps(t.raw())
    assert t.sink.records[0]["result"] == "failed"
    t.close()


def test_provider_failure_cannot_skip_business_work(monkeypatch: pytest.MonkeyPatch) -> None:
    t = Telemetry()

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(SECRET)

    monkeypatch.setattr(t.tracer, "start_span", fail)
    actions = []
    with t.boundary("outcome.commit", CORRELATION):
        actions.append(True)
    assert actions == [True] and t.instrumentation_failures > 0
    assert SECRET not in json.dumps(t.raw())
    t.close()


def test_metric_collection_failure_is_visible_in_the_same_health_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    t = Telemetry()

    def fail(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError(SECRET)

    monkeypatch.setattr(t.reader, "get_metrics_data", fail)
    health = t.canonical()
    assert health["instrumentation_failures"] == 1 and health["metrics"] == []
    assert SECRET not in json.dumps(health)
    t.close()


@pytest.mark.parametrize(
    "config",
    [
        {"max_spans": 0},
        {"max_spans": 4097},
        {"max_bytes": 63},
        {"max_bytes": 4194305},
        {"per_correlation": 0},
        {"per_correlation": 129},
    ],
)
def test_telemetry_budget_configuration_is_bounded(config: dict[str, int]) -> None:
    with pytest.raises(ValueError):
        LocalSink(**config)


@pytest.mark.parametrize("config", [{"max_spans": 1}, {"per_correlation": 1}, {"max_bytes": 64}])
def test_span_count_byte_and_correlation_limits_make_loss_visible(config: dict[str, int]) -> None:
    t = Telemetry(sink=LocalSink(**config))
    for _ in range(4):
        with t.boundary("policy", CORRELATION):
            pass
    assert len(t.sink.records) <= 1 and t.sink.dropped >= 3
    assert t.sink.used_bytes <= t.sink.max_bytes
    t.close()


def test_metric_series_limit_prevents_high_cardinality_growth() -> None:
    t = Telemetry()
    for name in sorted(BOUNDARIES):
        with t.boundary(name, CORRELATION):
            pass
        with pytest.raises(TimeoutError):
            with t.boundary(name, CORRELATION):
                raise TimeoutError()
    assert len(t.metrics()) <= 64 and t.metric_drops > 0
    t.close()


@pytest.mark.parametrize(
    "value",
    [
        "",
        SECRET,
        "x" * 1000,
        "00-" + "0" * 32 + "-" + "1" * 16 + "-01",
        "00-" + "1" * 32 + "-" + "0" * 16 + "-01",
        "ff-" + "1" * 32 + "-" + "2" * 16 + "-01",
    ],
)
def test_invalid_or_zero_w3c_context_is_not_accepted(value: str) -> None:
    assert (
        not trace.get_current_span(extract_parent({"traceparent": value}))
        .get_span_context()
        .is_valid
    )


def test_sdk_w3c_flags_round_trip_and_baggage_is_not_an_authority_channel() -> None:
    parent, child = Telemetry(), Telemetry()
    with parent.boundary("workflow", CORRELATION):
        carrier = inject_parent()
        carrier["baggage"] = SECRET
        with child.boundary("recovery", CORRELATION, parent=carrier):
            pass
    row = child.sink.records[0]
    assert row["trace_id"] == parent.sink.records[0]["trace_id"]
    assert row["parent_span_id"] == parent.sink.records[0]["span_id"]
    assert SECRET not in json.dumps(child.raw())
    parent.close()
    child.close()


def test_all_local_alerts_have_positive_negative_and_missing_signal_checks() -> None:
    spec, view = load_specs(OPERATIONS)
    assert len(spec.rules) == 8
    assert all(r["positive"] and r["negative"] for r in alert_controls(spec))
    assert all(r["status"] == "NOT_TESTED" for r in check_alerts(spec, {}))
    rendered = dashboard(view, {})
    assert rendered["independent_quality"] is rendered["gbp_cost"] is None


@pytest.mark.parametrize("value", [-1, True, 1.5, float("nan")])
def test_invalid_alert_signals_cannot_become_clear_or_triggered(value: object) -> None:
    spec, _ = load_specs(OPERATIONS)
    with pytest.raises(ValueError):
        check_alerts(spec, {"storage_failures": value})  # type: ignore[dict-item]
