"""Opt-in genuine SDK providers with bounded, allowlisted, memory-only evidence."""

import json
import math
import re
import time
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from threading import RLock
from uuid import UUID

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import Histogram, InMemoryMetricReader, Sum
from opentelemetry.sdk.metrics.view import View
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import ReadableSpan, SpanLimits, TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ALWAYS_ON
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from claims_ai.logging import correlation_scope

BOUNDARIES = frozenset(
    {
        "evaluation",
        "prediction",
        "workflow",
        "intake",
        "evidence",
        "policy",
        "rules",
        "agent",
        "routing",
        "tool.evidence",
        "tool.policy",
        "tool.rules",
        "api.request",
        "mcp.request",
        "review.action",
        "outcome.commit",
        "outcome.read",
        "recovery",
        "identity.check",
    }
)
RESULTS = frozenset({"ok", "failed", "timeout", "denied"})
TRACEPARENT = re.compile(r"00-([a-f0-9]{32})-([a-f0-9]{16})-([a-f0-9]{2})")
_correlation: ContextVar[UUID | None] = ContextVar("m22_safe_correlation", default=None)


@dataclass
class BoundaryStatus:
    result: str = "ok"


def extract_parent(carrier: Mapping[str, str]) -> otel_context.Context:
    """Accept only a single bounded W3C traceparent. Baggage/claims are never propagated."""
    value = carrier.get("traceparent", "")
    match = TRACEPARENT.fullmatch(value) if len(value) == 55 else None
    if match is None or int(match[1], 16) == 0 or int(match[2], 16) == 0:
        return otel_context.Context()
    return TraceContextTextMapPropagator().extract({"traceparent": value})


def inject_parent() -> dict[str, str]:
    carrier: dict[str, str] = {}
    TraceContextTextMapPropagator().inject(carrier)
    return {k: v for k, v in carrier.items() if k == "traceparent"}


def propagation_headers() -> dict[str, str]:
    carrier = inject_parent()
    correlation = _correlation.get()
    if carrier and correlation is not None:
        carrier["X-Correlation-ID"] = str(correlation)
    return carrier


class LocalSink(SpanExporter):
    def __init__(
        self, *, max_spans: int = 4096, max_bytes: int = 4194304, per_correlation: int = 128
    ) -> None:
        if (
            not 1 <= max_spans <= 4096
            or not 64 <= max_bytes <= 4194304
            or not (1 <= per_correlation <= 128)
        ):
            raise ValueError("invalid telemetry budget")
        self.max_spans, self.max_bytes, self.per_correlation = max_spans, max_bytes, per_correlation
        self.records: list[dict[str, object]] = []
        self.used_bytes = self.dropped = self.export_failures = 0
        self.fail = False
        self._counts: Counter[str] = Counter()
        self._lock = RLock()

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        with self._lock:
            for span in spans:
                if self.fail:
                    self.export_failures = min(self.export_failures + 1, 1000000)
                    continue
                if len(self.records) >= self.max_spans:
                    self.dropped = min(self.dropped + 1, 1000000)
                    continue
                attributes = span.attributes or {}
                correlation = attributes.get("correlation_id")
                result = attributes.get("result")
                if (
                    span.name not in BOUNDARIES
                    or result not in RESULTS
                    or not isinstance(correlation, str)
                ):
                    self.dropped = min(self.dropped + 1, 1000000)
                    continue
                try:
                    if str(UUID(correlation)) != correlation:
                        raise ValueError("noncanonical correlation")
                    context = span.get_span_context()
                    if context is None:
                        raise ValueError("missing span context")
                    record: dict[str, object] = {
                        "boundary": span.name,
                        "result": result,
                        "correlation_id": correlation,
                        "trace_id": format(context.trace_id, "032x"),
                        "span_id": format(context.span_id, "016x"),
                        "parent_span_id": format(span.parent.span_id, "016x")
                        if span.parent
                        else None,
                        "duration_ms": max(0, (span.end_time or 0) - (span.start_time or 0))
                        / 1000000,
                    }
                    size = len(json.dumps(record, allow_nan=False).encode())
                    if self._counts[correlation] >= self.per_correlation or (
                        self.used_bytes + size > self.max_bytes // 2
                    ):
                        self.dropped = min(self.dropped + 1, 1000000)
                        continue
                    self.records.append(record)
                    self._counts[correlation] += 1
                    self.used_bytes += size
                except Exception:
                    self.export_failures = min(self.export_failures + 1, 1000000)
            return SpanExportResult.FAILURE if self.fail else SpanExportResult.SUCCESS

    def shutdown(self) -> None:
        pass


class SafeExporter(SpanExporter):
    """Contain exporter exceptions before SDK exception logging can see payload details."""

    def __init__(self, sink: LocalSink) -> None:
        self.sink = sink

    def export(self, spans: Sequence[ReadableSpan]) -> SpanExportResult:
        try:
            return self.sink.export(spans)
        except Exception:
            self.sink.export_failures = min(self.sink.export_failures + 1, 1000000)
            return SpanExportResult.FAILURE

    def shutdown(self) -> None:
        pass


class Telemetry:
    """Providers are private instances: no set_*_provider, detectors, remote export or atexit."""

    def __init__(self, *, sink: LocalSink | None = None, sampled: bool = True) -> None:
        self.sink = sink or LocalSink()
        resource = Resource({"service.name": "claims-ai-offline", "execution.mode": "OFFLINE"})
        self.provider = TracerProvider(
            resource=resource,
            sampler=ALWAYS_ON if sampled else ALWAYS_OFF,
            shutdown_on_exit=False,
            span_limits=SpanLimits(
                max_attributes=16, max_events=0, max_links=0, max_attribute_length=128
            ),
        )
        self.provider.add_span_processor(SimpleSpanProcessor(SafeExporter(self.sink)))
        self.tracer = self.provider.get_tracer("claims_ai.quality_ops", "m22-v1")
        self.reader = InMemoryMetricReader()
        self.meter_provider = MeterProvider(
            metric_readers=[self.reader],
            resource=resource,
            shutdown_on_exit=False,
            views=[
                View(
                    instrument_name="claims.*",
                    attribute_keys={"boundary", "result"},
                    aggregation_cardinality_limit=32,
                )
            ],
        )
        meter = self.meter_provider.get_meter("claims_ai.quality_ops", "m22-v1")
        self.counter = meter.create_counter("claims.operations", unit="1")
        self.duration = meter.create_histogram("claims.duration", unit="ms")
        self._series: set[tuple[str, str]] = set()
        self.metric_drops = self.instrumentation_failures = 0
        self._lock = RLock()

    @contextmanager
    def boundary(
        self, name: str, correlation: UUID, *, parent: Mapping[str, str] | None = None
    ) -> Iterator[BoundaryStatus]:
        span = None
        token = None
        result = "ok"
        started = time.perf_counter()
        safe_correlation = correlation if isinstance(correlation, UUID) else UUID(int=0)
        status = BoundaryStatus()
        try:
            if name not in BOUNDARIES or not isinstance(correlation, UUID):
                raise ValueError("invalid instrumentation metadata")
            span = self.tracer.start_span(
                name,
                context=extract_parent(parent) if parent is not None else None,
                attributes={"correlation_id": str(correlation)},
            )
            token = otel_context.attach(trace.set_span_in_context(span))
        except Exception:
            self.instrumentation_failures = min(self.instrumentation_failures + 1, 1000000)
        try:
            # No exception message, payload or identity claims are sent to the SDK.
            with correlation_scope(safe_correlation):
                correlation_token = _correlation.set(safe_correlation)
                try:
                    yield status
                finally:
                    _correlation.reset(correlation_token)
        except TimeoutError:
            result = "timeout"
            raise
        except Exception:
            result = "failed"
            raise
        finally:
            if result == "ok" and status.result in RESULTS:
                result = status.result
            try:
                if span is not None:
                    span.set_attribute("result", result)
                    if result != "ok":
                        span.set_status(trace.Status(trace.StatusCode.ERROR))
                    span.end()
            except Exception:
                self.instrumentation_failures = min(self.instrumentation_failures + 1, 1000000)
            try:
                if token is not None:
                    otel_context.detach(token)
                with self._lock:
                    key = (name, result)
                    if name in BOUNDARIES and (key in self._series or len(self._series) < 32):
                        self._series.add(key)
                        self.counter.add(1, {"boundary": name, "result": result})
                        self.duration.record(
                            max(0, time.perf_counter() - started) * 1000,
                            {"boundary": name, "result": result},
                        )
                    else:
                        self.metric_drops = min(self.metric_drops + 1, 1000000)
            except Exception:
                self.instrumentation_failures = min(self.instrumentation_failures + 1, 1000000)

    def metrics(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        try:
            data = self.reader.get_metrics_data()
            if data is None:
                return rows
            for resource in data.resource_metrics:
                for scope in resource.scope_metrics:
                    for metric in scope.metrics:
                        if metric.name not in {
                            "claims.operations",
                            "claims.duration",
                        } or not isinstance(metric.data, (Sum, Histogram)):
                            continue
                        for point in metric.data.data_points:
                            attrs = point.attributes or {}
                            if (
                                attrs.get("boundary") not in BOUNDARIES
                                or attrs.get("result") not in RESULTS
                            ):
                                self.metric_drops = min(self.metric_drops + 1, 1000000)
                                continue
                            row: dict[str, object] = {
                                "name": metric.name,
                                "boundary": attrs.get("boundary"),
                                "result": attrs.get("result"),
                            }
                            if hasattr(point, "value"):
                                if not isinstance(point.value, (int, float)) or not math.isfinite(
                                    point.value
                                ):
                                    self.metric_drops = min(self.metric_drops + 1, 1000000)
                                    continue
                                row["value"] = point.value
                            if hasattr(point, "count"):
                                row["count"] = point.count
                            rows.append(row)
            return sorted(rows, key=lambda r: str((r["name"], r["boundary"], r["result"])))[:64]
        except Exception:
            self.instrumentation_failures = min(self.instrumentation_failures + 1, 1000000)
            return []

    def canonical(self) -> dict[str, object]:
        metrics = self.metrics()
        return {
            "spans": len(self.sink.records),
            "boundaries": dict(
                sorted(Counter(str(r["boundary"]) for r in self.sink.records).items())
            ),
            "dropped": self.sink.dropped,
            "export_failures": self.sink.export_failures,
            "metric_drops": self.metric_drops,
            "instrumentation_failures": self.instrumentation_failures,
            "metrics": metrics,
        }

    def raw(self) -> dict[str, object]:
        # Operational logs contain the same allowlisted event fields, never domain dumps.
        return {
            "format": "m22-local-telemetry-v1",
            "spans": list(self.sink.records),
            "logs": [
                {k: row[k] for k in ("boundary", "result", "correlation_id", "trace_id", "span_id")}
                for row in self.sink.records
            ],
            "metrics": self.metrics(),
            "health": self.canonical(),
        }

    def close(self) -> None:
        for provider in (self.provider, self.meter_provider):
            try:
                provider.shutdown()
            except Exception:
                self.instrumentation_failures = min(self.instrumentation_failures + 1, 1000000)
