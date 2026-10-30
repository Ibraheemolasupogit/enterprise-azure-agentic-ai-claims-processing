"""Evidence-processing metadata composes existing domain and extraction contracts."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from claims_ai.benchmark.contracts import (
    Confidence,
    FieldName,
    ProviderIdentity,
    SourceReference,
    Value,
)
from claims_ai.dataset.schema import SourceDocument
from claims_ai.models import (
    Case,
    ClaimId,
    Contract,
    DocumentId,
    Evidence,
    EvidenceId,
    Sha256,
    Version,
)


class Disposition(StrEnum):
    ACCEPTED = "accepted"
    QUARANTINED = "quarantined"
    REJECTED = "rejected"
    DUPLICATE = "duplicate"


class IssueCode(StrEnum):
    MALFORMED = "malformed_response"
    LIMIT = "response_limit"
    OWNERSHIP = "document_ownership"
    HASH = "artifact_hash_mismatch"
    IDENTITY = "extraction_identity_mismatch"
    PROVENANCE = "invalid_source_reference"
    SOURCE = "source_text_unverified"
    SCAN = "document_not_accepted"
    UNSUPPORTED = "unsupported_document_or_field"
    MISSING = "missing_required_field"
    VALUE = "malformed_field_value"
    IDENTIFIER = "identifier_mismatch"
    CONFLICT = "conflicting_evidence"
    DUPLICATE_FIELD = "duplicate_field"
    DUPLICATE_EVIDENCE = "duplicate_evidence"
    CONFIDENCE_MISSING = "confidence_unavailable"
    CONFIDENCE_LOW = "confidence_below_review_threshold"
    HISTORY_LIMIT = "history_capacity"
    COLLISION = "evidence_id_collision"


class ValidationIssue(Contract):
    code: IssueCode
    severity: Literal["warning", "quarantine", "reject"]
    field_name: FieldName | None = None
    action: Literal[
        "correct_response",
        "verify_case_and_bytes",
        "verify_source",
        "complete_scan",
        "request_fields",
        "human_review",
        "archive_history",
        "no_action",
    ]


class ProcessingPolicy(Contract):
    version: Literal["evidence-v1"] = "evidence-v1"
    max_response_bytes: Annotated[int, Field(strict=True, ge=1024, le=1048576)] = 131072
    max_fields: Annotated[int, Field(strict=True, ge=1, le=128)] = 64
    max_records: Annotated[int, Field(strict=True, ge=1, le=2048)] = 1024
    max_receipts: Annotated[int, Field(strict=True, ge=1, le=256)] = 128
    minimum_reported_confidence: (
        Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)] | None
    ) = None


class ProcessingRequest(Contract):
    case: Case
    document_id: DocumentId
    request_id: Version
    expected_provider: ProviderIdentity
    content: bytes = Field(repr=False, exclude=True)
    fixture_source: SourceDocument | None = Field(default=None, repr=False)
    policy: ProcessingPolicy = ProcessingPolicy()


class QualityMetadata(Contract):
    source_verification: Literal["fixture_render_verified", "structural_only"]
    confidence_status: Literal["unavailable", "reported_uncalibrated"]
    minimum_reported_confidence: float | None
    warnings: tuple[IssueCode, ...] = ()


class EvidenceRecord(Contract):
    processing_version: Literal["evidence-v1"] = "evidence-v1"
    evidence: Evidence
    raw_value: Value = Field(repr=False)
    provider: ProviderIdentity
    reported_confidence: Confidence | None = None
    sources: Annotated[tuple[SourceReference, ...], Field(min_length=1)]
    scope: Version
    quality: QualityMetadata
    record_sha256: Sha256

    @model_validator(mode="after")
    def matching_sources(self) -> Self:
        if self.evidence.evidence_id != "NS-EVD-" + self.record_sha256[:8].upper():
            raise ValueError("evidence ID must match its full record fingerprint")
        if self.evidence.confidence != (
            self.reported_confidence.value if self.reported_confidence else None
        ):
            raise ValueError("confidence metadata disagrees with mapped evidence")
        if self.evidence.observed_value != self.raw_value.strip():
            raise ValueError("raw value disagrees with domain observed value")
        for source in self.sources:
            if (
                source.document_id != self.evidence.document_id
                or source.artifact_sha256 != self.evidence.artifact_sha256
                or source.page != self.evidence.page
            ):
                raise ValueError("evidence envelope and source identity disagree")
        if (
            self.evidence.extraction_method != self.provider.provider.value
            or self.evidence.extraction_version != self.provider.model_version
        ):
            raise ValueError("evidence extraction metadata disagrees with provider")
        return self


class ProcessingReceipt(Contract):
    processing_version: Literal["evidence-v1"] = "evidence-v1"
    operation_key: Sha256
    response_sha256: Sha256
    claim_sha256: Sha256
    document_id: DocumentId
    disposition: Disposition
    candidate_ids: tuple[EvidenceId, ...]
    issues: Annotated[tuple[ValidationIssue, ...], Field(max_length=1024)]


class EvidenceHistory(Contract):
    claim_id: ClaimId
    records: Annotated[tuple[EvidenceRecord, ...], Field(max_length=2048)] = ()
    receipts: Annotated[tuple[ProcessingReceipt, ...], Field(max_length=256)] = ()

    @model_validator(mode="after")
    def unique_identity(self) -> Self:
        if any(record.evidence.claim_id != self.claim_id for record in self.records):
            raise ValueError("history cannot contain another claim's evidence")
        ids = [record.evidence.evidence_id for record in self.records]
        keys = [receipt.operation_key for receipt in self.receipts]
        if len(ids) != len(set(ids)) or len(keys) != len(set(keys)):
            raise ValueError("history record IDs and receipt keys must be unique")
        return self


class ProcessingResult(Contract):
    operation_key: Sha256
    disposition: Disposition
    candidates: tuple[EvidenceRecord, ...]
    issues: tuple[ValidationIssue, ...]
    history: EvidenceHistory
    replay_of: Disposition | None = None


class EvidenceAdmission(Contract):
    previous: Case
    current: Case
    operation_key: Sha256
    execution_mode: Literal["SIMULATED", "LIVE"]
