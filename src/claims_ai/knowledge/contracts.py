"""Case-scoped draft knowledge contracts, separate from approved operational policy bundles."""

from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal, Protocol, Self

from pydantic import Field, model_validator

from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.schema import SourceDocument
from claims_ai.models import (
    Case,
    ClaimId,
    Contract,
    DocumentMetadata,
    Policy,
    PolicyClause,
    PolicyId,
    PositiveInt,
    Sha256,
    Text,
    Version,
)


def fingerprint(value: object) -> str:
    return sha256(json_bytes(value)).hexdigest()


class Reason(StrEnum):
    MISSING_VERSION = "missing_policy_version"
    MISSING_POLICY = "missing_policy"
    CONFLICT = "conflicting_policy_versions"
    MALFORMED = "malformed_policy_document"
    UNVERIFIED = "unverifiable_policy_source"
    OWNERSHIP = "scope_mismatch"
    METADATA = "policy_metadata_mismatch"
    CLAUSE_CONFLICT = "duplicate_or_conflicting_clause"
    UNSUPPORTED = "unsupported_policy_format_or_endorsement"
    OUTSIDE_INTERVAL = "incident_outside_policy_interval"
    INDEX = "index_integrity_mismatch"
    ABSENT_CLAUSE = "requested_clause_absent"
    NO_MATCH = "no_lexical_match"
    QUERY = "query_token_limit_or_empty"
    OUTAGE = "retrieval_unavailable"


class KnowledgeIssue(Contract):
    code: Reason
    policy_version: Version | None = None
    action: Literal["verify_register_and_sources", "request_policy", "human_review"]


class PolicyDocument(Contract):
    document: DocumentMetadata
    source: SourceDocument = Field(repr=False)
    content: bytes = Field(repr=False, exclude=True)


class IngestionRequest(Contract):
    case: Case
    policies: Annotated[tuple[Policy, ...], Field(max_length=16)]
    documents: Annotated[tuple[PolicyDocument, ...], Field(max_length=64)]


class PolicySource(Contract):
    document: DocumentMetadata
    source: SourceDocument = Field(repr=False)


class PolicyChunk(Contract):
    chunk_id: Sha256
    parser_version: Literal["fixture-clauses-v1"] = "fixture-clauses-v1"
    claim_id: ClaimId
    clause: PolicyClause
    section: Literal["C", "X", "R", "V"]
    category: Literal["clause", "exclusion_candidate", "review", "revision"]
    effective_from: date
    effective_to: date
    source_line_start: PositiveInt
    source_line_end: PositiveInt


class PolicyKnowledge(Contract):
    policy: Policy
    sources: Annotated[tuple[PolicySource, ...], Field(min_length=2, max_length=2)]
    chunks: Annotated[tuple[PolicyChunk, ...], Field(min_length=1, max_length=32)]


class KnowledgeIndex(Contract):
    format_version: Literal["lexical-fixture-v1"] = "lexical-fixture-v1"
    knowledge_status: Literal["unapproved_fixture_only"] = "unapproved_fixture_only"
    claim_id: ClaimId
    policy_id: PolicyId
    entries: Annotated[tuple[PolicyKnowledge, ...], Field(max_length=16)]
    issues: Annotated[tuple[KnowledgeIssue, ...], Field(max_length=64)] = ()
    index_sha256: Sha256


class RetrievalRequest(Contract):
    claim_id: ClaimId
    policy_id: PolicyId
    policy_version: Version | None
    incident_date: date
    index_sha256: Sha256
    query: Text = Field(repr=False)
    clause_ids: Annotated[tuple[Version, ...], Field(max_length=16)] = ()
    limit: Annotated[int, Field(strict=True, ge=1, le=10)] = 5

    @model_validator(mode="after")
    def unique_clauses(self) -> Self:
        if len(self.clause_ids) != len(set(self.clause_ids)):
            raise ValueError("clause filters must be unique")
        return self


class RetrievedClause(Contract):
    chunk: PolicyChunk
    matched_terms: tuple[str, ...]
    lexical_score: PositiveInt

    @model_validator(mode="after")
    def valid_score(self) -> Self:
        if self.matched_terms != tuple(
            sorted(set(self.matched_terms))
        ) or self.lexical_score != len(self.matched_terms):
            raise ValueError("lexical score must count distinct sorted matched terms")
        return self


class RetrievalResponse(Contract):
    request_sha256: Sha256
    index_sha256: Sha256
    method: Literal["distinct_token_overlap_v1"] = "distinct_token_overlap_v1"
    knowledge_status: Literal["unapproved_fixture_only"] = "unapproved_fixture_only"
    status: Literal["retrieved", "abstained"]
    reason: Reason | None = None
    hits: Annotated[tuple[RetrievedClause, ...], Field(max_length=10)] = ()

    @model_validator(mode="after")
    def valid_status(self) -> Self:
        if self.status == "retrieved":
            if not self.hits or self.reason is not None:
                raise ValueError("retrieved results need hits and no abstention reason")
        elif self.hits or self.reason is None:
            raise ValueError("abstention needs a reason and cannot expose hits")
        return self


class KnowledgeIndexSource(Protocol):
    async def load(self, index_sha256: str) -> KnowledgeIndex | None:
        """Load exactly the requested immutable snapshot; never substitute a newer index."""
        ...


class AzureAISearchAdapter(Protocol):
    async def retrieve(self, request: RetrievalRequest, *, case: Case) -> RetrievalResponse:
        """Future boundary only: enforce case/policy/version/date/index filters.

        Validate every returned citation before exposing results.
        No client, embedding, vector query, credentials or hybrid implementation is supplied.
        Draft fixture indexes must never be published as approved operational knowledge.
        """
        ...
