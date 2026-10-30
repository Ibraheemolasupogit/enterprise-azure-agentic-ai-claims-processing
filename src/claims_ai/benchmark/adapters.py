"""Adapter protocols and explicit oracle fixture. No vendor clients are implemented."""

from typing import Literal, Protocol

from claims_ai.benchmark.contracts import (
    AdapterProfile,
    Capabilities,
    ExtractedField,
    ExtractionRequest,
    ExtractionResponse,
    Provider,
    ProviderIdentity,
    SourceReference,
)
from claims_ai.dataset.schema import FieldTruth, GroundTruth
from claims_ai.models import DocumentKind


class ExtractionAdapter(Protocol):
    @property
    def profile(self) -> AdapterProfile: ...

    @property
    def provider(self) -> Provider: ...

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        """Return validated common fields; requests contain no expected values or truth paths."""
        ...


class AzureDocumentIntelligenceAdapter(ExtractionAdapter, Protocol):
    @property
    def provider(self) -> Literal[Provider.AZURE_DOCUMENT_INTELLIGENCE]: ...


class MistralDocumentAIAdapter(ExtractionAdapter, Protocol):
    @property
    def provider(self) -> Literal[Provider.MISTRAL_DOCUMENT_AI]: ...


class GPTMultimodalAdapter(ExtractionAdapter, Protocol):
    @property
    def provider(self) -> Literal[Provider.GPT_MULTIMODAL]: ...


class FixtureAdapter:
    """SIMULATED ground-truth echo to test plumbing, not an extractor or accuracy baseline."""

    provider: Literal[Provider.FIXTURE] = Provider.FIXTURE

    def __init__(self, truth: GroundTruth, *, pdf_only: bool = False) -> None:
        self._profile = AdapterProfile(
            identity=ProviderIdentity(
                provider=self.provider,
                model_version="ground-truth-echo-v1",
                adapter_version="1.0",
                execution_mode="SIMULATED",
            ),
            capabilities=Capabilities(
                media_types=("application/pdf",) if pdf_only else ("application/pdf", "image/png"),
                document_kinds=(
                    DocumentKind.CLAIM_FORM,
                    DocumentKind.REPAIR_ESTIMATE,
                    DocumentKind.POLICY_SCHEDULE,
                    DocumentKind.POLICY_WORDING,
                    DocumentKind.DAMAGE_PHOTO,
                ),
                page_references=True,
                source_lines=True,
            ),
        )
        fields: dict[str, list[FieldTruth]] = {}
        for sample in truth.samples:
            for field in sample.extraction_fields:
                document_id = field.expected.document_id
                fields.setdefault(document_id, [])
                if field not in fields[document_id]:
                    fields[document_id].append(field)
        self._fields = fields

    @property
    def profile(self) -> AdapterProfile:
        return self._profile

    async def extract(self, request: ExtractionRequest) -> ExtractionResponse:
        names = {field.name for field in request.fields}
        return ExtractionResponse(
            request_id=request.request_id,
            document_id=request.document.document_id,
            artifact_sha256=request.document.sha256,
            provider=self.profile.identity,
            fields=tuple(
                ExtractedField(
                    name=field.expected.field_name,
                    value=field.expected.observed_value,
                    sources=(
                        SourceReference(
                            document_id=field.expected.document_id,
                            artifact_sha256=field.expected.artifact_sha256,
                            page=field.expected.page,
                            source_line=field.source_line,
                            location_kind=field.location_kind,
                        ),
                    ),
                )
                for field in self._fields[request.document.document_id]
                if field.expected.field_name in names
            ),
        )
