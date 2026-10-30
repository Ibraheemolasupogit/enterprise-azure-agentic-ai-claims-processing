"""Deterministic field comparisons. No semantic judge, policy or financial decisions."""

import re
import unicodedata
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from claims_ai.benchmark.contracts import (
    Capabilities,
    DocumentStatus,
    ExtractionResponse,
    FieldKind,
    FieldScore,
    Metrics,
    Rate,
)
from claims_ai.dataset.schema import FieldTruth


def field_kind(name: str) -> FieldKind:
    if name in {"claimed_amount", "estimate_amount"}:
        return FieldKind.NUMERIC
    if name in {"effective_from", "effective_to"}:
        return FieldKind.DATE
    if name in {"loss_at", "estimate_issued_at"}:
        return FieldKind.DATETIME
    return FieldKind.TEXT


def normalized_text(value: str, name: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    if name == "damage_location":
        value = value.replace("_", " ")  # M4 explicitly labels these captions with underscores.
    return " ".join(value.split())


def numeric_equal(predicted: str, expected: str) -> bool:
    pattern = r"[+-]?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?"
    if not re.fullmatch(pattern, predicted.strip()) or not re.fullmatch(pattern, expected.strip()):
        return False
    try:
        return Decimal(predicted.replace(",", "").strip()) == Decimal(
            expected.replace(",", "").strip()
        )
    except InvalidOperation:
        return False


def date_equal(predicted: str, expected: str, kind: FieldKind) -> bool:
    try:
        if kind == FieldKind.DATE:
            if not all(
                re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value.strip())
                for value in (predicted, expected)
            ):
                return False
            return date.fromisoformat(predicted.strip()) == date.fromisoformat(expected.strip())
        values = [
            datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
            for value in (predicted, expected)
        ]
        return all(value.utcoffset() is not None for value in values) and values[0].astimezone(
            UTC
        ) == values[1].astimezone(UTC)
    except (ValueError, OverflowError):
        return False


def score_fields(
    expected: tuple[FieldTruth, ...],
    response: ExtractionResponse | None,
    capabilities: Capabilities,
    status: DocumentStatus,
) -> tuple[FieldScore, ...]:
    actual = {field.name: field for field in response.fields} if response is not None else {}
    result = []
    for truth in expected:
        evidence = truth.expected
        kind = field_kind(evidence.field_name)
        unsupported = status == DocumentStatus.UNSUPPORTED or kind not in capabilities.field_kinds
        field = actual.get(evidence.field_name) if status == DocumentStatus.OK else None
        present = field is not None and field.value is not None and bool(field.value.strip())
        value = field.value if field is not None else None
        exact = bool(present and value == evidence.observed_value)
        normalized = bool(
            present
            and value is not None
            and normalized_text(value, evidence.field_name)
            == normalized_text(
                evidence.normalized_value or evidence.observed_value, evidence.field_name
            )
        )
        sources = field.sources if field is not None else ()
        provenance = (
            present
            and bool(sources)
            and all(
                source.document_id == evidence.document_id
                and source.artifact_sha256 == evidence.artifact_sha256
                and source.page == evidence.page
                for source in sources
            )
        )
        location = provenance and all(
            source.source_line == truth.source_line and source.location_kind == truth.location_kind
            for source in sources
        )
        result.append(
            FieldScore(
                name=evidence.field_name,
                kind=kind,
                expected_value=evidence.observed_value,
                expected_normalized=evidence.normalized_value or evidence.observed_value,
                predicted_value=value,
                status="unsupported"
                if unsupported
                else "failed"
                if status != DocumentStatus.OK
                else "present"
                if present
                else "missing",
                exact=None if unsupported else exact,
                normalized_text=None if unsupported else normalized,
                numeric_correct=None
                if unsupported or kind != FieldKind.NUMERIC
                else bool(
                    present and value is not None and numeric_equal(value, evidence.observed_value)
                ),
                date_correct=None
                if unsupported or kind not in {FieldKind.DATE, FieldKind.DATETIME}
                else bool(
                    present
                    and value is not None
                    and date_equal(value, evidence.observed_value, kind)
                ),
                provenance_correct=None
                if unsupported or not capabilities.page_references
                else provenance,
                source_location_correct=None
                if unsupported or not capabilities.source_lines
                else location,
            )
        )
    return tuple(result)


def summarize(fields: tuple[FieldScore, ...]) -> Metrics:
    def rate(name: str) -> Rate:
        values = [getattr(field, name) for field in fields]
        return Rate(
            numerator=sum(value is True for value in values),
            denominator=sum(value is not None for value in values),
        )

    return Metrics(
        exact=rate("exact"),
        normalized_text=rate("normalized_text"),
        numeric_correct=rate("numeric_correct"),
        date_correct=rate("date_correct"),
        provenance_correct=rate("provenance_correct"),
        source_location_correct=rate("source_location_correct"),
        missing_fields=sum(f.status == "missing" for f in fields),
        failed_fields=sum(f.status == "failed" for f in fields),
        unsupported_fields=sum(f.status == "unsupported" for f in fields),
    )
