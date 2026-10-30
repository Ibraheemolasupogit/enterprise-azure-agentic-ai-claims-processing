"""Fail-closed JSON events: arbitrary messages, exception text and payloads are never emitted."""

import json
import logging
import math
import re
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import UTC, datetime
from enum import StrEnum
from typing import TextIO
from uuid import UUID, uuid4

_correlation_id: ContextVar[UUID | None] = ContextVar("claims_ai_correlation_id", default=None)
REDACTED = "[REDACTED]"


class LogEvent(StrEnum):
    CASE_TRANSITION = "case_transition"
    DOCUMENT_VALIDATED = "document_validated"
    VALIDATION_FAILED = "validation_failed"
    CONFIGURATION_LOADED = "configuration_loaded"
    SERVICE_ERROR = "service_error"


def redact_fields(fields: Mapping[str, object]) -> dict[str, object]:
    """Allow only validated operational fields; omit unknown keys as well as their values."""
    clean: dict[str, object] = {}
    redacted = 0
    id_patterns = {
        "claim_id": r"NS-CLM-[A-Z0-9]{8}",
        "document_id": r"NS-DOC-[A-Z0-9]{8}",
        "assessment_id": r"NS-ASM-[A-Z0-9]{8}",
    }
    for key, value in fields.items():
        valid = False
        if key in id_patterns:
            valid = isinstance(value, str) and re.fullmatch(id_patterns[key], value) is not None
        elif key in {"revision", "attempt", "byte_size"}:
            valid = type(value) is int and 0 <= value <= 2**63 - 1
        elif key == "duration_ms":
            valid = (
                isinstance(value, (int, float))
                and not isinstance(value, bool)
                and 0 <= value <= 1e12
                and math.isfinite(value)
            )
        elif key == "status":
            valid = isinstance(value, str) and value in {"ok", "invalid", "denied", "failed"}
        if valid:
            clean[key] = value
        elif key in id_patterns or key in {
            "revision",
            "attempt",
            "byte_size",
            "duration_ms",
            "status",
        }:
            clean[key] = REDACTED
            redacted += 1
        else:
            redacted += 1
    if redacted:
        clean["redacted_fields"] = redacted
    return clean


@contextmanager
def correlation_scope(correlation_id: UUID | None = None) -> Iterator[UUID]:
    if correlation_id is not None and not isinstance(correlation_id, UUID):
        raise ValueError("correlation ID must be a UUID")
    value = correlation_id or uuid4()
    token = _correlation_id.set(value)
    try:
        yield value
    finally:
        _correlation_id.reset(token)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        event = record.msg.value if isinstance(record.msg, LogEvent) else REDACTED
        fields = getattr(record, "fields", {})
        correlation_id = getattr(record, "correlation_id", None)
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": logging.getLevelName(record.levelno),
            "event": event,
            "correlation_id": str(correlation_id) if isinstance(correlation_id, UUID) else None,
            "fields": redact_fields(fields) if isinstance(fields, dict) else {},
            "exception": bool(record.exc_info),
        }
        return json.dumps(payload, allow_nan=False)


def configure_logging(*, level: int = logging.INFO, stream: TextIO | None = None) -> logging.Logger:
    """Explicit setup for this package only; importing the package has no logging side effects."""
    logger = logging.getLogger("claims_ai")
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    for existing in logger.handlers[:]:
        logger.removeHandler(existing)
        existing.close()
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger


def log_event(
    logger: logging.Logger,
    event: LogEvent,
    *,
    fields: Mapping[str, object] | None = None,
    level: int = logging.INFO,
) -> None:
    logger.log(
        level,
        event,
        extra={"fields": dict(fields or {}), "correlation_id": _correlation_id.get()},
    )
