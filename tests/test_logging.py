import asyncio
import io
import json
import logging
from uuid import UUID

import pytest

from claims_ai.logging import (
    REDACTED,
    LogEvent,
    configure_logging,
    correlation_scope,
    log_event,
    redact_fields,
)


@pytest.fixture
def output() -> io.StringIO:
    return io.StringIO()


def test_structured_event_and_correlation(output: io.StringIO) -> None:
    logger = configure_logging(stream=output)
    correlation_id = UUID("40000000-0000-0000-0000-000000000001")
    with correlation_scope(correlation_id):
        log_event(
            logger,
            LogEvent.CASE_TRANSITION,
            fields={"claim_id": "NS-CLM-00000001", "revision": 2, "status": "ok"},
        )
    log_event(logger, LogEvent.CONFIGURATION_LOADED)
    first, second = [json.loads(line) for line in output.getvalue().splitlines()]
    assert first["correlation_id"] == str(correlation_id)
    assert first["fields"]["revision"] == 2
    assert second["correlation_id"] is None
    assert logger.propagate is False


def test_payloads_keys_messages_and_exception_text_never_escape(output: io.StringIO) -> None:
    logger = configure_logging(stream=output)
    secret = "SYNTHETIC-CONFIDENTIAL-CONTENT"
    log_event(
        logger,
        LogEvent.VALIDATION_FAILED,
        fields={
            "authorization": secret,
            "narrative": secret,
            "prompt": secret,
            "document": {"nested": [secret]},
            secret: secret,
            "claim_id": secret,
            "status": f"https://example.invalid/?sig={secret}",
        },
    )
    try:
        raise ValueError(secret)
    except ValueError:
        logger.exception("raw message %s", secret)
    assert secret not in output.getvalue()
    events = [json.loads(line) for line in output.getvalue().splitlines()]
    assert events[0]["fields"]["claim_id"] == REDACTED
    assert events[0]["fields"]["redacted_fields"] == 7
    assert events[1]["event"] == REDACTED and events[1]["exception"] is True


@pytest.mark.parametrize("value", [-1, True, "bad", float("nan"), float("inf"), 10**100])
def test_invalid_safe_fields_are_redacted(value: object) -> None:
    assert redact_fields({"duration_ms": value})["duration_ms"] == REDACTED


def test_nested_scopes_reset_even_after_error(output: io.StringIO) -> None:
    logger = configure_logging(stream=output)
    with correlation_scope() as outer:
        with pytest.raises(RuntimeError), correlation_scope():
            raise RuntimeError("synthetic test")
        log_event(logger, LogEvent.SERVICE_ERROR)
    assert json.loads(output.getvalue())["correlation_id"] == str(outer)


def test_async_contexts_are_isolated(output: io.StringIO) -> None:
    logger = configure_logging(stream=output)

    async def work(identifier: UUID) -> None:
        with correlation_scope(identifier):
            await asyncio.sleep(0)
            log_event(logger, LogEvent.DOCUMENT_VALIDATED)

    identifiers = [UUID(int=1), UUID(int=2)]

    async def run() -> None:
        await asyncio.gather(*(work(value) for value in identifiers))

    asyncio.run(run())
    assert {json.loads(line)["correlation_id"] for line in output.getvalue().splitlines()} == {
        str(value) for value in identifiers
    }


def test_configuration_does_not_duplicate_handlers(output: io.StringIO) -> None:
    configure_logging(stream=output)
    logger = configure_logging(stream=output)
    log_event(logger, LogEvent.CONFIGURATION_LOADED)
    assert len(output.getvalue().splitlines()) == 1
    assert logging.getLogger("claims_ai") is logger
