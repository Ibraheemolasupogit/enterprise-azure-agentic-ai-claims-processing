"""Model-neutral benchmark contracts; intentionally separate from operational processing."""

from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, StringConstraints, model_validator

from claims_ai.models import (
    Contract,
    Coordinate,
    DocumentId,
    DocumentKind,
    DocumentMetadata,
    PositiveInt,
    Sha256,
    Version,
)

Value = Annotated[str, StringConstraints(strict=True, max_length=4000)]
FieldName = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,63}$")]
Count = Annotated[StrictInt, Field(ge=0)]
MediaType = Literal["application/pdf", "image/png", "image/jpeg"]
ErrorCode = Literal[
    "schema_invalid", "identity_mismatch", "timeout", "unsupported_document", "adapter_error"
]


class Provider(StrEnum):
    FIXTURE = "fixture"
    AZURE_DOCUMENT_INTELLIGENCE = "azure_document_intelligence"
    MISTRAL_DOCUMENT_AI = "mistral_document_ai"
    GPT_MULTIMODAL = "gpt_multimodal"


class FieldKind(StrEnum):
    TEXT = "text"
    NUMERIC = "numeric"
    DATE = "date"
    DATETIME = "datetime"


class ProviderIdentity(Contract):
    provider: Provider
    model_version: Version
    adapter_version: Version
    execution_mode: Literal["SIMULATED", "LIVE"]


class Capabilities(Contract):
    media_types: tuple[MediaType, ...]
    document_kinds: tuple[DocumentKind, ...]
    field_kinds: tuple[FieldKind, ...] = tuple(FieldKind)
    page_references: bool = False
    source_lines: bool = False
    confidence: bool = False
    latency: bool = False
    token_usage: bool = False
    cost: bool = False

    @model_validator(mode="after")
    def distinct(self) -> Self:
        for values in (self.media_types, self.document_kinds, self.field_kinds):
            if not values or len(values) != len(set(values)):
                raise ValueError("capability sets must be nonempty and unique")
        if self.source_lines and not self.page_references:
            raise ValueError("source-line comparison requires page references")
        return self


class AdapterProfile(Contract):
    identity: ProviderIdentity
    capabilities: Capabilities


class FieldSpec(Contract):
    name: FieldName
    kind: FieldKind


class ExtractionRequest(Contract):
    request_id: Version
    purpose: Literal["offline_synthetic_benchmark"] = "offline_synthetic_benchmark"
    document: DocumentMetadata
    fields: tuple[FieldSpec, ...]
    content: bytes = Field(repr=False, exclude=True)

    @model_validator(mode="after")
    def valid_bytes(self) -> Self:
        if (
            len(self.content) != self.document.byte_size
            or sha256(self.content).hexdigest() != self.document.sha256
        ):
            raise ValueError("request bytes must match the pinned document metadata")
        if len({field.name for field in self.fields}) != len(self.fields):
            raise ValueError("requested field names must be unique")
        return self


class SourceReference(Contract):
    document_id: DocumentId
    artifact_sha256: Sha256
    page: PositiveInt | None = None
    source_line: PositiveInt | None = None
    location_kind: Literal["pdf_line", "image_caption"] | None = None
    bounding_region: tuple[Coordinate, Coordinate, Coordinate, Coordinate] | None = None

    @model_validator(mode="after")
    def ordered_region(self) -> Self:
        if self.bounding_region is not None:
            left, top, right, bottom = self.bounding_region
            if left >= right or top >= bottom:
                raise ValueError("source rectangle must have increasing coordinates")
        return self


class Confidence(Contract):
    value: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]
    basis: Literal["provider_reported", "fixture_assigned"]
    calibrated: Literal[False] = False


class Usage(Contract):
    input_tokens: Count | None = None
    output_tokens: Count | None = None
    cost_amount: (
        Annotated[str, StringConstraints(strict=True, pattern=r"^\d+(?:\.\d+)?$")] | None
    ) = None
    cost_currency: Literal["GBP", "USD", "EUR"] | None = None

    @model_validator(mode="after")
    def cost_pair(self) -> Self:
        if (self.cost_amount is None) != (self.cost_currency is None):
            raise ValueError("reported cost needs both decimal amount and currency")
        return self


class ExtractedField(Contract):
    name: FieldName
    value: Value | None = Field(repr=False)
    confidence: Confidence | None = None
    sources: tuple[SourceReference, ...] = ()


class ExtractionResponse(Contract):
    request_id: Version
    document_id: DocumentId
    artifact_sha256: Sha256
    provider: ProviderIdentity
    fields: tuple[ExtractedField, ...]
    latency_ms: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)] | None = None
    usage: Usage | None = None

    @model_validator(mode="after")
    def unique_fields(self) -> Self:
        if len(self.fields) != len({field.name for field in self.fields}):
            raise ValueError("duplicate response field names are ambiguous")
        return self


class DocumentStatus(StrEnum):
    OK = "ok"
    UNSUPPORTED = "unsupported_document"
    INVALID = "invalid_response"
    TIMEOUT = "timeout"
    ADAPTER_ERROR = "adapter_error"


class FieldScore(Contract):
    name: FieldName
    kind: FieldKind
    expected_value: Value = Field(repr=False)
    expected_normalized: Value = Field(repr=False)
    predicted_value: Value | None = Field(default=None, repr=False)
    status: Literal["present", "missing", "failed", "unsupported"]
    exact: bool | None
    normalized_text: bool | None
    numeric_correct: bool | None
    date_correct: bool | None
    provenance_correct: bool | None
    source_location_correct: bool | None


class Rate(Contract):
    numerator: Count
    denominator: Count
    value: Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)] | None = None

    @model_validator(mode="after")
    def valid_count(self) -> Self:
        if self.numerator > self.denominator:
            raise ValueError("numerator cannot exceed denominator")
        expected = self.numerator / self.denominator if self.denominator else None
        if self.value is not None and self.value != expected:
            raise ValueError("rate value must match its counts")
        object.__setattr__(self, "value", expected)
        return self


class Metrics(Contract):
    exact: Rate
    normalized_text: Rate
    numeric_correct: Rate
    date_correct: Rate
    provenance_correct: Rate
    source_location_correct: Rate
    missing_fields: Count
    failed_fields: Count
    unsupported_fields: Count


class DocumentResult(Contract):
    document_id: DocumentId
    artifact_sha256: Sha256
    media_type: MediaType
    document_kind: DocumentKind
    scenario_ids: tuple[Version, ...]
    status: DocumentStatus
    error_code: ErrorCode | None = None
    schema_valid: bool | None
    metadata_missing: tuple[str, ...] = ()
    metadata_unsupported: tuple[str, ...] = ()
    unexpected_fields: tuple[FieldName, ...] = ()
    response: ExtractionResponse | None = None
    fields: tuple[FieldScore, ...]
    metrics: Metrics


class FieldSummary(Contract):
    name: FieldName
    kind: FieldKind
    metrics: Metrics


class CohortResult(Contract):
    media_type: MediaType
    document_kind: DocumentKind
    profile_sha256: Sha256
    documents: Count
    unsupported_documents: Count
    failed_documents: Count
    schema_validity: Rate
    unexpected_fields: Count
    metrics: Metrics
    per_field: tuple[FieldSummary, ...]


class BenchmarkConfig(Contract):
    timeout_seconds: Annotated[float, Field(gt=0, le=600, allow_inf_nan=False)] = 5.0


class BenchmarkReport(Contract):
    benchmark_version: Literal["benchmark-v1"] = "benchmark-v1"
    scoring_version: Literal["field-v1"] = "field-v1"
    execution_mode: Literal["SIMULATED"] = "SIMULATED"
    contains_untrusted_synthetic_text: Literal[True] = True
    run_id: Sha256
    manifest_sha256: Sha256
    ground_truth_sha256: Sha256
    benchmark_sha256: Sha256
    python_version: str
    pydantic_version: str
    config: BenchmarkConfig
    profile: AdapterProfile
    selection: Literal["unique_document_id_no_duplicate_submission_weighting"] = (
        "unique_document_id_no_duplicate_submission_weighting"
    )
    corpus_label_count: Count
    unique_label_count: Count
    documents: tuple[DocumentResult, ...]
    cohorts: tuple[CohortResult, ...]
