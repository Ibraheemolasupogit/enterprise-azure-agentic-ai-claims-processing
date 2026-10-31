"""Evaluation labels are separate from engine inputs and are not adjudicated truth."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import AwareDatetime, Field, model_validator

from claims_ai.knowledge.contracts import PolicyChunk, Reason, RetrievalRequest, RetrievalResponse
from claims_ai.models import ClaimId, Contract, PolicyId, Sha256, Text, Version


class Cohort(StrEnum):
    ANSWERABLE = "answerable"
    NO_ANSWER = "no_answer"
    SAFETY = "safety_block"
    INVALID = "invalid_query"
    TECHNICAL = "technical_failure"


class Fault(StrEnum):
    NONE = "none"
    DUPLICATE_VERSION = "duplicate_version"
    SOURCE_TAMPER = "source_tamper"
    INSTRUCTION_CLAUSE = "instruction_clause"
    WRONG_SNAPSHOT = "wrong_snapshot"
    OUTAGE = "outage"
    MISSING_INDEX = "missing_index"


class QuerySpec(Contract):
    claim_id: ClaimId
    policy_id: PolicyId
    policy_version: Version | None
    incident_date: date
    query: Text = Field(repr=False)
    clause_ids: tuple[Version, ...] = ()
    k: Annotated[int, Field(strict=True, ge=1, le=10)] = 3

    @model_validator(mode="after")
    def unique_filters(self) -> Self:
        if len(self.clause_ids) != len(set(self.clause_ids)):
            raise ValueError("gold clause filters must be unique")
        return self


class Relevance(Contract):
    chunk: PolicyChunk
    grade: Annotated[int, Field(strict=True, ge=1, le=3)]


class GoldenQuery(Contract):
    query_id: Version
    case_scenario: Version
    scenario: Version
    cohort: Cohort
    fault: Fault = Fault.NONE
    incident_at_override: AwareDatetime | None = None
    request: QuerySpec
    relevant: tuple[Relevance, ...] = ()
    expected_reason: Reason | None = None
    rationale: Text

    @model_validator(mode="after")
    def consistent_expectations(self) -> Self:
        ids = [r.chunk.chunk_id for r in self.relevant]
        if len(ids) != len(set(ids)):
            raise ValueError("relevance labels must have unique chunk IDs")
        if self.cohort == Cohort.ANSWERABLE:
            if not self.relevant or self.expected_reason is not None:
                raise ValueError("answerable queries need relevance and no abstention reason")
        elif self.relevant or self.expected_reason is None:
            raise ValueError("abstention queries need an empty relevance set and explicit reason")
        allowed = {
            Cohort.NO_ANSWER: {Reason.NO_MATCH, Reason.ABSENT_CLAUSE},
            Cohort.INVALID: {Reason.QUERY},
            Cohort.TECHNICAL: {Reason.OUTAGE, Reason.MISSING_POLICY},
        }
        if self.cohort in allowed and self.expected_reason not in allowed[self.cohort]:
            raise ValueError("abstention reason does not match its evaluation cohort")
        if self.cohort == Cohort.SAFETY and self.expected_reason in {
            Reason.NO_MATCH,
            Reason.ABSENT_CLAUSE,
            Reason.QUERY,
            Reason.OUTAGE,
        }:
            raise ValueError("safety blocks cannot stand in for no-answer/invalid/outage cases")
        if (self.cohort == Cohort.TECHNICAL) != (self.fault in {Fault.OUTAGE, Fault.MISSING_INDEX}):
            raise ValueError("technical-failure scenarios require explicit simulated fault inputs")
        return self


class GoldenDataset(Contract):
    dataset_version: Literal["retrieval-gold-v1"] = "retrieval-gold-v1"
    label_status: Literal["authored_not_independently_adjudicated"] = (
        "authored_not_independently_adjudicated"
    )
    label_basis: Literal["source_clause_reading_without_retriever_outputs"] = (
        "source_clause_reading_without_retriever_outputs"
    )
    split: Literal["development_not_held_out"] = "development_not_held_out"
    corpus_manifest_sha256: Sha256
    queries: Annotated[tuple[GoldenQuery, ...], Field(min_length=1, max_length=200)]

    @model_validator(mode="after")
    def unique_queries(self) -> Self:
        ids = [q.query_id for q in self.queries]
        if len(ids) != len(set(ids)):
            raise ValueError("gold query IDs must be unique")
        return self


class GoldenManifest(Contract):
    dataset_version: Literal["retrieval-gold-v1"] = "retrieval-gold-v1"
    queries_sha256: Sha256
    corpus_manifest_sha256: Sha256


class RankingMetrics(Contract):
    k: int
    relevant_total: int
    returned_at_k: int
    relevant_at_k: int
    precision_at_k: float
    recall_at_k: float
    mrr_at_k: float
    ndcg_at_k: float


class HitEvaluation(Contract):
    rank: int
    chunk_id: Sha256
    citation_valid: bool
    cross_policy: bool
    cross_claim: bool
    version_and_date_correct: bool
    relevance_grade: int


class QueryEvaluation(Contract):
    query_id: Version
    scenario: Version
    cohort: Cohort
    fault: Fault
    request: RetrievalRequest
    response: RetrievalResponse | None
    schema_valid: bool
    response_binding_valid: bool
    observed: Literal[
        "retrieved", "no_answer", "safety_block", "invalid_query", "technical_failure"
    ]
    hits: tuple[HitEvaluation, ...]
    ranking: RankingMetrics | None
    expected_behavior_correct: bool
    false_positive_retrieval: bool | None
    failure_codes: tuple[Version, ...]
