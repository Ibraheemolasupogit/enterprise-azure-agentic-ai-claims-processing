"""Known-value scoring checks, not provider or insurance accuracy results."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.benchmark.contracts import (
    Capabilities,
    Confidence,
    DocumentStatus,
    ExtractedField,
    ExtractionResponse,
    FieldKind,
    Provider,
    ProviderIdentity,
    Rate,
    SourceReference,
    Usage,
)
from claims_ai.benchmark.scoring import (
    date_equal,
    normalized_text,
    numeric_equal,
    score_fields,
    summarize,
)
from claims_ai.dataset.schema import FieldTruth, GroundTruth
from claims_ai.models import DocumentKind


@pytest.fixture(scope="module")
def truth() -> GroundTruth:
    return GroundTruth.model_validate_json(
        Path("data/synthetic/motor/v1/ground_truth.json").read_bytes()
    )


def response_for(
    truth: FieldTruth, value: str | None, sources: tuple[SourceReference, ...] | None = None
) -> ExtractionResponse:
    expected = truth.expected
    return ExtractionResponse(
        request_id=expected.document_id,
        document_id=expected.document_id,
        artifact_sha256=expected.artifact_sha256,
        provider=ProviderIdentity(
            provider=Provider.FIXTURE,
            model_version="test-only",
            adapter_version="1.0",
            execution_mode="SIMULATED",
        ),
        fields=(
            ExtractedField(
                name=expected.field_name,
                value=value,
                sources=sources
                if sources is not None
                else (
                    SourceReference(
                        document_id=expected.document_id,
                        artifact_sha256=expected.artifact_sha256,
                        page=1,
                        source_line=truth.source_line,
                        location_kind=truth.location_kind,
                    ),
                ),
            ),
        ),
    )


@pytest.fixture
def caps() -> Capabilities:
    return Capabilities(
        media_types=("application/pdf", "image/png"),
        document_kinds=tuple(DocumentKind),
        page_references=True,
        source_lines=True,
    )


@pytest.mark.parametrize(
    "predicted,expected,correct",
    [
        ("1,234.50", "1234.5", True),
        ("001.000", "1", True),
        ("-2.5", "-2.50", True),
        ("1,23", "123", False),
        ("GBP 1", "1", False),
        ("NaN", "1", False),
        ("Infinity", "1", False),
        ("1.004", "1.00", False),
        ("1e3", "1000", False),
    ],
)
def test_numeric_correctness_has_no_rounding_or_currency_guess(
    predicted: str,
    expected: str,
    correct: bool,
) -> None:
    assert numeric_equal(predicted, expected) is correct


@pytest.mark.parametrize(
    "predicted,expected,kind,correct",
    [
        ("2026-01-02", "2026-01-02", FieldKind.DATE, True),
        ("02/01/2026", "2026-01-02", FieldKind.DATE, False),
        ("2026-02-30", "2026-02-28", FieldKind.DATE, False),
        ("2026-01-02T11:00:00+01:00", "2026-01-02T10:00:00Z", FieldKind.DATETIME, True),
        ("2026-01-02T10:00:00", "2026-01-02T10:00:00Z", FieldKind.DATETIME, False),
        ("2026-01-02T10:00:01Z", "2026-01-02T10:00:00Z", FieldKind.DATETIME, False),
    ],
)
def test_date_correctness_is_explicit_and_timezone_aware(
    predicted: str,
    expected: str,
    kind: FieldKind,
    correct: bool,
) -> None:
    assert date_equal(predicted, expected, kind) is correct


def test_normalization_is_conservative_and_matches_m4_caption_rule() -> None:
    assert normalized_text("  ＦＲＯＮＴ\nBUMPER ", "damage_location") == "front bumper"
    assert normalized_text("front_bumper", "damage_location") == "front bumper"
    assert normalized_text("a_b", "policy_id") != normalized_text("a b", "policy_id")
    assert normalized_text("-1", "claimed_amount") != normalized_text("1", "claimed_amount")


def test_exact_and_normalized_scores_are_separate(truth: GroundTruth, caps: Capabilities) -> None:
    expected = next(
        f
        for s in truth.samples
        for f in s.extraction_fields
        if f.expected.field_name == "damage_location"
    )
    score = score_fields(
        (expected,), response_for(expected, "  front_bumper  "), caps, DocumentStatus.OK
    )[0]
    assert score.exact is False and score.normalized_text is True
    assert score.provenance_correct is True and score.source_location_correct is True
    assert score.numeric_correct is None and score.date_correct is None


@pytest.mark.parametrize("value", [None, "", "   "])
def test_blank_null_and_missing_values_are_errors(
    truth: GroundTruth,
    caps: Capabilities,
    value: str | None,
) -> None:
    expected = truth.samples[0].extraction_fields[0]
    score = score_fields((expected,), response_for(expected, value), caps, DocumentStatus.OK)[0]
    assert score.status == "missing" and score.exact is False and score.provenance_correct is False
    empty = ExtractionResponse.model_validate(
        {**response_for(expected, value).model_dump(), "fields": []}
    )
    assert summarize(score_fields((expected,), empty, caps, DocumentStatus.OK)).missing_fields == 1


@pytest.mark.parametrize(
    "changes",
    [
        {"document_id": "NS-DOC-00000099"},
        {"artifact_sha256": "f" * 64},
        {"page": 2},
        {"source_line": 99},
        {"location_kind": "image_caption"},
    ],
)
def test_provenance_and_location_checks(
    truth: GroundTruth, caps: Capabilities, changes: dict[str, object]
) -> None:
    expected = truth.samples[0].extraction_fields[0]
    base = response_for(expected, expected.expected.observed_value)
    source = SourceReference.model_validate({**base.fields[0].sources[0].model_dump(), **changes})
    response = response_for(expected, expected.expected.observed_value, (source,))
    score = score_fields((expected,), response, caps, DocumentStatus.OK)[0]
    assert score.exact is True and score.source_location_correct is False
    assert score.provenance_correct is (
        not bool(set(changes) & {"document_id", "artifact_sha256", "page"})
    )


def test_unavailable_and_failed_denominators(truth: GroundTruth, caps: Capabilities) -> None:
    expected = (truth.samples[0].extraction_fields[0],)
    metrics = summarize(score_fields(expected, None, caps, DocumentStatus.UNSUPPORTED))
    assert (
        metrics.exact.denominator == 0
        and metrics.exact.value is None
        and metrics.unsupported_fields == 1
    )
    failed = summarize(score_fields(expected, None, caps, DocumentStatus.TIMEOUT))
    assert failed.exact.denominator == 1 and failed.exact.value == 0 and failed.failed_fields == 1
    no_source = Capabilities.model_validate(
        {**caps.model_dump(), "page_references": False, "source_lines": False}
    )
    score = score_fields(
        expected,
        response_for(expected[0], expected[0].expected.observed_value),
        no_source,
        DocumentStatus.OK,
    )[0]
    assert score.provenance_correct is None and score.source_location_correct is None


@pytest.mark.parametrize(
    "model,data",
    [
        (Confidence, {"value": 1.1, "basis": "provider_reported"}),
        (Confidence, {"value": float("nan"), "basis": "provider_reported"}),
        (Confidence, {"value": True, "basis": "provider_reported"}),
        (Usage, {"input_tokens": -1}),
        (Usage, {"input_tokens": True}),
        (Usage, {"cost_amount": "NaN", "cost_currency": "GBP"}),
        (Usage, {"cost_amount": "1.0"}),
        (Rate, {"numerator": 2, "denominator": 1}),
        (Rate, {"numerator": 1, "denominator": 1, "value": 0.5}),
    ],
)
def test_metadata_and_metric_validation(
    model: type[Confidence] | type[Usage] | type[Rate], data: dict[str, object]
) -> None:
    with pytest.raises(ValidationError):
        model.model_validate(data)


def test_metadata_none_and_zero_are_distinct() -> None:
    assert Usage().input_tokens is None and Usage().cost_amount is None
    assert (
        Usage(input_tokens=0, output_tokens=0, cost_amount="0", cost_currency="GBP").input_tokens
        == 0
    )
    rate = Rate(numerator=0, denominator=0)
    assert Rate.model_validate_json(rate.model_dump_json()).value is None
