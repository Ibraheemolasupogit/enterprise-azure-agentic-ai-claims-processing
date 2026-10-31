"""Strict parsing of byte-verifiable, single-page M4 policy fixtures, without activation."""

import re
from hashlib import sha256

from claims_ai.dataset.generator import WARNING
from claims_ai.dataset.render import render_document
from claims_ai.knowledge.contracts import (
    IngestionRequest,
    KnowledgeIndex,
    KnowledgeIssue,
    PolicyChunk,
    PolicyKnowledge,
    PolicySource,
    Reason,
    fingerprint,
)
from claims_ai.models import Case, DocumentKind, Policy, PolicyCitation, PolicyClause

SECTIONS = {"C": "clause", "X": "exclusion_candidate", "R": "review", "V": "revision"}
SCHEDULE_NOTES = (
    "Dataset intervals are start-inclusive/end-exclusive metadata.",
    "No binding coverage or financial terms are approved.",
)
WORDING_NOTE = "All clauses are fictional discussion text, not approved executable rules."


class PolicyInputError(ValueError):
    def __init__(self, reason: Reason) -> None:
        self.reason = reason
        super().__init__(reason.value)


def _require(condition: bool, reason: Reason) -> None:
    if not condition:
        raise PolicyInputError(reason)


def parse_policy(case: Case, policy: Policy, sources: tuple[PolicySource, ...]) -> PolicyKnowledge:
    """Rebuild all chunks from pinned source bytes/metadata; source prose is never executed."""
    _require(policy.policy_id == case.claim.policy_id, Reason.OWNERSHIP)
    _require(not policy.endorsements, Reason.UNSUPPORTED)
    _require(
        policy.index_version == "fixture-not-indexed"
        and policy.rule_pack_version == "unapproved-no-rules",
        Reason.METADATA,
    )
    by_id = {s.document.document_id: s for s in sources}
    _require(len(by_id) == len(sources) == 2, Reason.UNVERIFIED)
    owned = {d.document_id: d for d in case.documents}
    for artifact, kind in (
        (policy.schedule, DocumentKind.POLICY_SCHEDULE),
        (policy.wording, DocumentKind.POLICY_WORDING),
    ):
        item = by_id.get(artifact.document_id)
        _require(item is not None, Reason.UNVERIFIED)
        assert item is not None
        document, source = item.document, item.source
        _require(
            document.claim_id == case.claim.claim_id
            and owned.get(document.document_id) == document,
            Reason.OWNERSHIP,
        )
        _require(
            document.kind == kind
            and document.media_type == "application/pdf"
            and document.page_count == 1
            and source.rendering == "pdf-text",
            Reason.UNSUPPORTED,
        )
        content = render_document(source)
        _require(
            source.document_id == document.document_id
            and document.sha256 == artifact.sha256 == sha256(content).hexdigest()
            and document.byte_size == len(content),
            Reason.UNVERIFIED,
        )
        _require(
            source.lines[:3]
            == (
                WARNING,
                f"document_id: {document.document_id}",
                f"claim_id: {case.claim.claim_id}",
            ),
            Reason.METADATA,
        )
    schedule = by_id[policy.schedule.document_id].source
    _require(
        schedule.title == "NORTHSTAR | DRAFT MOTOR POLICY SCHEDULE"
        and schedule.lines[3:]
        == (
            f"policy_id: {policy.policy_id}",
            f"policy_version: {policy.version}",
            f"effective_from: {policy.effective_from.isoformat()}",
            f"effective_to: {policy.effective_to.isoformat()}",
            f"vehicle_reference: {case.claim.vehicle_reference}",
            *SCHEDULE_NOTES,
        ),
        Reason.METADATA,
    )
    wording = by_id[policy.wording.document_id].source
    _require(
        wording.title == "NORTHSTAR | DRAFT MOTOR POLICY WORDING"
        and wording.lines[3:6]
        == (
            f"policy_version: {policy.version}",
            f"product: {policy.product}",
            f"jurisdiction: {policy.jurisdiction}",
        )
        and wording.lines[-1] == WORDING_NOTE,
        Reason.METADATA,
    )
    chunks = []
    ids: set[str] = set()
    for line_number, line in enumerate(wording.lines[6:-1], start=7):
        match = re.fullmatch(r"([CXRV][0-9]{2}) - (.+)", line)
        _require(match is not None, Reason.MALFORMED)
        assert match is not None
        clause_id, text = match.groups()
        _require(clause_id not in ids, Reason.CLAUSE_CONFLICT)
        ids.add(clause_id)
        payload = {
            "schema_version": "1.0",
            "synthetic": True,
            "parser_version": "fixture-clauses-v1",
            "claim_id": case.claim.claim_id,
            "clause": PolicyClause(
                citation=PolicyCitation(
                    policy_id=policy.policy_id,
                    policy_version=policy.version,
                    document_id=policy.wording.document_id,
                    artifact_sha256=policy.wording.sha256,
                    clause_id=clause_id,
                    page=1,
                ),
                text=text,
            ).model_dump(mode="json"),
            "section": clause_id[0],
            "category": SECTIONS[clause_id[0]],
            "effective_from": policy.effective_from.isoformat(),
            "effective_to": policy.effective_to.isoformat(),
            "source_line_start": line_number,
            "source_line_end": line_number,
        }
        chunks.append(PolicyChunk.model_validate({**payload, "chunk_id": fingerprint(payload)}))
    _require(bool(chunks), Reason.MALFORMED)
    return PolicyKnowledge(
        policy=policy,
        sources=tuple(sorted(sources, key=lambda s: s.document.document_id)),
        chunks=tuple(sorted(chunks, key=lambda c: c.clause.citation.clause_id)),
    )


def register_conflicts(policies: tuple[Policy, ...]) -> bool:
    return any(
        first.version == second.version
        or max(first.effective_from, second.effective_from)
        < min(first.effective_to, second.effective_to)
        for pos, first in enumerate(policies)
        for second in policies[pos + 1 :]
    )


def ingest(request: IngestionRequest) -> KnowledgeIndex:
    request = IngestionRequest.model_validate(request)
    entries = []
    issues = []
    docs = {d.document.document_id: d for d in request.documents}
    if not request.policies:
        issues.append(KnowledgeIssue(code=Reason.MISSING_POLICY, action="request_policy"))
    if len(docs) != len(request.documents) or register_conflicts(request.policies):
        issues.append(KnowledgeIssue(code=Reason.CONFLICT, action="verify_register_and_sources"))
    for policy in sorted(
        request.policies, key=lambda p: (p.version, fingerprint(p.model_dump(mode="json")))
    ):
        try:
            sources = []
            for artifact in policy.artifacts:
                item = docs.get(artifact.document_id)
                _require(item is not None, Reason.UNVERIFIED)
                assert item is not None
                _require(item.source.rendering == "pdf-text", Reason.UNSUPPORTED)
                _require(item.content == render_document(item.source), Reason.UNVERIFIED)
                sources.append(PolicySource(document=item.document, source=item.source))
            entries.append(parse_policy(request.case, policy, tuple(sources)))
        except PolicyInputError as error:
            issues.append(
                KnowledgeIssue(
                    code=error.reason,
                    policy_version=policy.version,
                    action="verify_register_and_sources",
                )
            )
    payload = {
        "schema_version": "1.0",
        "synthetic": True,
        "format_version": "lexical-fixture-v1",
        "knowledge_status": "unapproved_fixture_only",
        "claim_id": request.case.claim.claim_id,
        "policy_id": request.case.claim.policy_id,
        "entries": [e.model_dump(mode="json") for e in entries],
        "issues": [i.model_dump(mode="json") for i in issues],
    }
    return KnowledgeIndex.model_validate({**payload, "index_sha256": fingerprint(payload)})
