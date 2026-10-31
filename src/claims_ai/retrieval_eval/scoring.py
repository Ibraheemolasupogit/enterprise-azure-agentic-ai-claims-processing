"""Rank metrics and independent source/citation/scope checks; invalid hits earn no credit."""

from hashlib import sha256
from math import log2

from claims_ai.dataset.generator import json_bytes
from claims_ai.knowledge.contracts import Reason, RetrievalRequest, RetrievalResponse
from claims_ai.retrieval_eval.contracts import (
    Cohort,
    Fault,
    GoldenQuery,
    HitEvaluation,
    QueryEvaluation,
    RankingMetrics,
)
from claims_ai.retrieval_eval.dataset import Context, source_chunk


def ranking_metrics(
    retrieved: tuple[str | None, ...],
    relevance: dict[str, int],
    k: int,
) -> RankingMetrics | None:
    if k < 1 or any(grade < 1 or grade > 3 for grade in relevance.values()):
        raise ValueError("ranking needs positive k and relevance grades within 1–3")
    if not relevance:
        return None
    seen: set[str] = set()
    gains = []
    relevant_ranks = []
    for rank, chunk_id in enumerate(retrieved[:k], start=1):
        grade = relevance.get(chunk_id, 0) if chunk_id is not None and chunk_id not in seen else 0
        if chunk_id is not None:
            seen.add(chunk_id)
        gains.append((2**grade - 1) / log2(rank + 1))
        if grade:
            relevant_ranks.append(rank)
    ideal = sum(
        (2**grade - 1) / log2(rank + 1)
        for rank, grade in enumerate(sorted(relevance.values(), reverse=True)[:k], start=1)
    )
    return RankingMetrics(
        k=k,
        relevant_total=len(relevance),
        returned_at_k=len(retrieved[:k]),
        relevant_at_k=len(relevant_ranks),
        precision_at_k=len(relevant_ranks) / k,
        recall_at_k=len(relevant_ranks) / len(relevance),
        mrr_at_k=1 / relevant_ranks[0] if relevant_ranks else 0.0,
        ndcg_at_k=sum(gains) / ideal,
    )


def classify(reason: Reason | None, fault: Fault) -> str:
    if reason is None:
        return "retrieved"
    if reason == Reason.OUTAGE or (
        reason == Reason.MISSING_POLICY and fault == Fault.MISSING_INDEX
    ):
        return "technical_failure"
    if reason == Reason.QUERY:
        return "invalid_query"
    if reason in {Reason.NO_MATCH, Reason.ABSENT_CLAUSE}:
        return "no_answer"
    return "safety_block"


def score(
    gold: GoldenQuery,
    context: Context,
    request: RetrievalRequest,
    raw: object,
    *,
    technical_error: bool = False,
) -> QueryEvaluation:
    response = None
    schema_valid = False
    binding = False
    failures = []
    observed = "technical_failure"
    hits = []
    credited: list[str | None] = []
    relevance = {r.chunk.chunk_id: r.grade for r in gold.relevant}
    if not technical_error:
        try:
            response = RetrievalResponse.model_validate(raw)
            schema_valid = True
        except ValueError:
            failures.append("malformed_response")
    else:
        failures.append("engine_exception_or_timeout")
    if response is not None:
        binding = (
            response.request_sha256
            == sha256(json_bytes(request.model_dump(mode="json"))).hexdigest()
            and response.index_sha256 == request.index_sha256
        )
        if not binding:
            failures.append("response_binding_mismatch")
        observed = classify(response.reason, gold.fault)
        if len(response.hits) > request.limit:
            failures.append("limit_exceeded")
        seen: set[str] = set()
        for rank, hit in enumerate(response.hits, start=1):
            chunk = hit.chunk
            citation = chunk.clause.citation
            citation_valid = False
            try:
                expected = source_chunk(
                    context, citation.policy_version, citation.clause_id, chunk.source_line_start
                )
                citation_valid = chunk == expected
            except (ValueError, StopIteration, IndexError, KeyError):
                pass
            cross_policy = (
                citation.policy_id != context.case.claim.policy_id
                or citation.policy_id != request.policy_id
            )
            cross_claim = (
                chunk.claim_id != context.case.claim.claim_id or chunk.claim_id != request.claim_id
            )
            matching_versions = [
                p for p in context.policies if p.version == citation.policy_version
            ]
            active_versions = [
                p
                for p in context.policies
                if p.effective_from <= request.incident_date < p.effective_to
            ]
            version_valid = (
                citation.policy_version == request.policy_version
                and request.incident_date == context.case.claim.loss_at.date()
                and len(matching_versions) == len(active_versions) == 1
                and matching_versions[0] == active_versions[0]
            )
            duplicate = chunk.chunk_id in seen
            seen.add(chunk.chunk_id)
            valid = (
                citation_valid
                and version_valid
                and not cross_policy
                and not cross_claim
                and binding
                and not duplicate
            )
            grade = relevance.get(chunk.chunk_id, 0) if valid else 0
            hits.append(
                HitEvaluation(
                    rank=rank,
                    chunk_id=chunk.chunk_id,
                    citation_valid=citation_valid,
                    cross_policy=cross_policy,
                    cross_claim=cross_claim,
                    version_and_date_correct=version_valid,
                    relevance_grade=grade,
                )
            )
            credited.append(chunk.chunk_id if valid else None)
            for failed, code in (
                (not citation_valid, "citation_invalid"),
                (not version_valid, "wrong_version_or_date"),
                (cross_policy, "cross_policy_result"),
                (cross_claim, "cross_claim_result"),
                (duplicate, "duplicate_hit"),
            ):
                if failed:
                    failures.append(code)
        if gold.cohort == Cohort.ANSWERABLE:
            if not set(relevance) <= set(credited[: request.limit]):
                failures.append("relevant_not_retrieved_at_k")
            if any(h.relevance_grade == 0 for h in hits[: request.limit]):
                failures.append("irrelevant_returned_at_k")
        elif response.status != "abstained" or response.reason != gold.expected_reason:
            failures.append("unexpected_answer_or_abstention_reason")
        if gold.cohort == Cohort.NO_ANSWER and response.hits:
            failures.append("false_positive_retrieval")
    metrics = ranking_metrics(tuple(credited), relevance, request.limit)
    return QueryEvaluation.model_validate(
        {
            "query_id": gold.query_id,
            "scenario": gold.scenario,
            "cohort": gold.cohort,
            "fault": gold.fault,
            "request": request,
            "response": response,
            "schema_valid": schema_valid,
            "response_binding_valid": binding,
            "observed": observed,
            "hits": hits,
            "ranking": metrics,
            "expected_behavior_correct": not failures,
            "false_positive_retrieval": bool(hits)
            if gold.cohort == Cohort.NO_ANSWER and schema_valid
            else None,
            "failure_codes": tuple(sorted(set(failures))),
        }
    )


def ratio(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def summarize(rows: tuple[QueryEvaluation, ...]) -> dict[str, object]:
    all_hits = [h for row in rows for h in row.hits]
    abstentions = [r for r in rows if r.cohort != Cohort.ANSWERABLE]
    no_answer = [r for r in rows if r.cohort == Cohort.NO_ANSWER]
    ranking = {}
    for k in sorted({r.ranking.k for r in rows if r.ranking is not None}):
        metrics = [r.ranking for r in rows if r.ranking is not None and r.ranking.k == k]
        ranking[str(k)] = {
            "denominator_queries": len(metrics),
            **{
                name: sum(float(getattr(m, name)) for m in metrics) / len(metrics)
                for name in (
                    "precision_at_k",
                    "recall_at_k",
                    "mrr_at_k",
                    "ndcg_at_k",
                )
            },
        }
    return {
        "queries": len(rows),
        "returned_hits": len(all_hits),
        "expected_behavior": ratio(sum(r.expected_behavior_correct for r in rows), len(rows)),
        "response_schema_validity": ratio(sum(r.schema_valid for r in rows), len(rows)),
        "citation_validity": ratio(sum(h.citation_valid for h in all_hits), len(all_hits)),
        "policy_version_and_date_correctness": ratio(
            sum(h.version_and_date_correct for h in all_hits), len(all_hits)
        ),
        "unsafe_cross_policy": ratio(sum(h.cross_policy for h in all_hits), len(all_hits)),
        "unsafe_cross_claim": ratio(sum(h.cross_claim for h in all_hits), len(all_hits)),
        "abstention_correctness": ratio(
            sum(r.expected_behavior_correct for r in abstentions), len(abstentions)
        ),
        "no_answer_queries": len(no_answer),
        "false_positive_retrieval": ratio(
            sum(r.false_positive_retrieval is True for r in no_answer),
            sum(r.false_positive_retrieval is not None for r in no_answer),
        ),
        "ranking_answerable_only_by_k": ranking,
        "observed_technical_failures": sum(r.observed == "technical_failure" for r in rows),
        "observed_invalid_queries": sum(r.observed == "invalid_query" for r in rows),
        "failure_examples": [
            {"query_id": r.query_id, "codes": r.failure_codes} for r in rows if r.failure_codes
        ],
    }
