"""Fail-closed lexical lookup; no semantic, vector, fallback or coverage inference."""

import asyncio
import re
import unicodedata

from claims_ai.knowledge.contracts import (
    KnowledgeIndex,
    KnowledgeIndexSource,
    Reason,
    RetrievalRequest,
    RetrievalResponse,
    RetrievedClause,
    fingerprint,
)
from claims_ai.knowledge.ingestion import PolicyInputError, parse_policy, register_conflicts
from claims_ai.models import Case


def abstain(request: RetrievalRequest, reason: Reason) -> RetrievalResponse:
    return RetrievalResponse(
        request_sha256=fingerprint(request.model_dump(mode="json")),
        index_sha256=request.index_sha256,
        status="abstained",
        reason=reason,
    )


def tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", unicodedata.normalize("NFKC", text).casefold()))


def retrieve(case: Case, request: RetrievalRequest, index: KnowledgeIndex) -> RetrievalResponse:
    case = Case.model_validate(case)
    request = RetrievalRequest.model_validate(request)
    try:
        index = KnowledgeIndex.model_validate(index)
        if (
            request.claim_id != case.claim.claim_id
            or index.claim_id != case.claim.claim_id
            or request.policy_id != case.claim.policy_id
            or index.policy_id != case.claim.policy_id
            or request.incident_date != case.claim.loss_at.date()
        ):
            return abstain(request, Reason.OWNERSHIP)
        if request.index_sha256 != index.index_sha256 or index.index_sha256 != fingerprint(
            index.model_dump(mode="json", exclude={"index_sha256"})
        ):
            return abstain(request, Reason.INDEX)
        if index.issues:
            return abstain(request, index.issues[0].code)
        policies = tuple(e.policy for e in index.entries)
        if register_conflicts(policies):
            return abstain(request, Reason.CONFLICT)
        # Rebuild the entire case-scoped snapshot, including citations and line/content binding.
        for entry in index.entries:
            rebuilt = parse_policy(case, entry.policy, entry.sources)
            if rebuilt != entry:
                return abstain(request, Reason.INDEX)
        if request.policy_version is None:
            return abstain(request, Reason.MISSING_VERSION)
        matches = [e for e in index.entries if e.policy.version == request.policy_version]
        if not matches:
            return abstain(request, Reason.MISSING_POLICY)
        if len(matches) != 1:
            return abstain(request, Reason.CONFLICT)
        entry = matches[0]
        if not entry.policy.effective_from <= request.incident_date < entry.policy.effective_to:
            return abstain(request, Reason.OUTSIDE_INTERVAL)
        requested_ids = set(request.clause_ids)
        if not requested_ids <= {c.clause.citation.clause_id for c in entry.chunks}:
            return abstain(request, Reason.ABSENT_CLAUSE)
        query_tokens = tokens(request.query)
        if not query_tokens or len(query_tokens) > 64:
            return abstain(request, Reason.QUERY)
        hits = []
        for chunk in entry.chunks:
            if requested_ids and chunk.clause.citation.clause_id not in requested_ids:
                continue
            overlap = tuple(sorted(query_tokens & tokens(chunk.clause.text)))
            if overlap:
                hits.append(
                    RetrievedClause(chunk=chunk, matched_terms=overlap, lexical_score=len(overlap))
                )
        hits.sort(
            key=lambda h: (-h.lexical_score, h.chunk.clause.citation.clause_id, h.chunk.chunk_id)
        )
        if not hits:
            return abstain(request, Reason.NO_MATCH)
        return RetrievalResponse(
            request_sha256=fingerprint(request.model_dump(mode="json")),
            index_sha256=index.index_sha256,
            status="retrieved",
            hits=tuple(hits[: request.limit]),
        )
    except PolicyInputError as error:
        return abstain(request, error.reason)
    except ValueError:
        return abstain(request, Reason.INDEX)


async def retrieve_from(
    source: KnowledgeIndexSource,
    case: Case,
    request: RetrievalRequest,
    *,
    timeout_seconds: float = 1.0,
) -> RetrievalResponse:
    """An unavailable store never enables broader retrieval; errors omit backend/raw text."""
    case = Case.model_validate(case)
    request = RetrievalRequest.model_validate(request)
    if not 0 < timeout_seconds <= 30:
        raise ValueError("retrieval timeout must be finite and within (0, 30] seconds")
    if (
        request.claim_id != case.claim.claim_id
        or request.policy_id != case.claim.policy_id
        or request.incident_date != case.claim.loss_at.date()
    ):
        return abstain(request, Reason.OWNERSHIP)
    try:
        index = await asyncio.wait_for(source.load(request.index_sha256), timeout=timeout_seconds)
    except Exception:
        return abstain(request, Reason.OUTAGE)
    if index is None:
        return abstain(request, Reason.MISSING_POLICY)
    return retrieve(case, request, index)
