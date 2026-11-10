"""New in-memory synthetic source bytes; existing M6/M7/M9 services verify all outputs."""

from hashlib import sha256

from claims_ai.agents.contracts import AssessmentInput
from claims_ai.benchmark.contracts import ExtractionResponse
from claims_ai.dataset.render import render_document
from claims_ai.dataset.schema import SourceDocument
from claims_ai.evidence.contracts import Disposition, ProcessingRequest
from claims_ai.evidence.processing import admit_evidence, process_extraction
from claims_ai.knowledge.contracts import IngestionRequest, PolicyDocument, RetrievalRequest
from claims_ai.knowledge.ingestion import ingest
from claims_ai.knowledge.retrieval import retrieve
from claims_ai.models import Case, DocumentKind, Policy
from claims_ai.rules.contracts import EvaluationRequest, EvidenceInput, ReviewedFacts
from claims_ai.rules.engine import evaluate
from claims_ai.rules.specification import digest


def contaminated(value: AssessmentInput, payload: str, *, policy: bool) -> AssessmentInput:
    request = value.rule_request
    kind = DocumentKind.POLICY_WORDING if policy else DocumentKind.CLAIM_FORM
    target = next(
        b
        for b in request.evidence_inputs
        if next(d for d in request.case.documents if d.document_id == b.request.document_id).kind
        == kind
    )
    original_source = target.request.fixture_source
    if original_source is None or request.index is None or value.retrieval_request is None:
        raise ValueError("verified synthetic source prerequisites required")
    lines = (
        (
            *original_source.lines[:-1],
            "C05 - Provisional note: " + payload,
            original_source.lines[-1],
        )
        if policy
        else tuple(
            "narrative: " + payload if line.startswith("narrative: ") else line
            for line in original_source.lines
        )
    )
    source = SourceDocument.model_validate({**original_source.model_dump(), "lines": lines})
    content = render_document(source)
    document_id = target.request.document_id
    documents = tuple(
        type(d).model_validate(
            {**d.model_dump(), "sha256": sha256(content).hexdigest(), "byte_size": len(content)}
        )
        if d.document_id == document_id
        else d
        for d in request.case.documents
    )
    claim = request.case.claim.model_dump()
    if not policy:
        claim["narrative"] = payload
    base = Case.model_validate(
        {
            **request.case.model_dump(),
            "claim": claim,
            "documents": documents,
            "evidence": (),
            "state": "extracting",
            "revision": 3,
        }
    )
    current = base
    bundles, sources = [], []
    for old in request.evidence_inputs:
        metadata = next(d for d in documents if d.document_id == old.request.document_id)
        changed = metadata.document_id == document_id
        authored_source = source if changed else old.request.fixture_source
        authored_content = content if changed else old.request.content
        processing = ProcessingRequest.model_validate(
            {
                **old.request.model_dump(),
                "case": base,
                "content": authored_content,
                "fixture_source": authored_source,
            }
        )
        raw = old.response.model_dump(mode="json")
        if changed:
            raw["artifact_sha256"] = metadata.sha256
            for field in raw["fields"]:
                if not policy and field["name"] == "narrative":
                    field["value"] = payload
                for reference in field["sources"]:
                    reference["artifact_sha256"] = metadata.sha256
        extraction = ExtractionResponse.model_validate(raw)
        result = process_extraction(processing, extraction)
        if result.disposition != Disposition.ACCEPTED:
            raise ValueError("synthetic fixture was not admitted")
        current = admit_evidence(current, result, allow_simulated=True).current
        bundles.append(EvidenceInput(request=processing, response=extraction))
        if authored_source is None:
            raise ValueError("missing authored source")
        sources.append(
            PolicyDocument(document=metadata, source=authored_source, content=authored_content)
        )
    current = Case.model_validate({**current.model_dump(), "state": "assessing"})
    policies = []
    for entry in request.index.entries:
        data = entry.policy.model_dump()
        if data["wording"]["document_id"] == document_id:
            data["wording"]["sha256"] = sha256(content).hexdigest()
        policies.append(Policy.model_validate(data))
    index = ingest(
        IngestionRequest(case=current, policies=tuple(policies), documents=tuple(sources))
    )
    facts = tuple(
        ReviewedFacts.model_validate(
            {
                **f.model_dump(),
                "case_sha256": digest(current.model_dump(mode="json")),
                "evidence_ids": tuple(
                    e.evidence_id for e in current.evidence if e.field_name == "narrative"
                ),
            }
        )
        for f in request.reviewed_facts
    )
    evaluation_request = EvaluationRequest.model_validate(
        {
            **request.model_dump(exclude={"evidence_inputs"}),
            "case": current,
            "index": index,
            "evidence_inputs": tuple(bundles),
            "reviewed_facts": facts,
        }
    )
    query = RetrievalRequest.model_validate(
        {**value.retrieval_request.model_dump(), "index_sha256": index.index_sha256}
    )
    return AssessmentInput.model_validate(
        {
            **value.model_dump(exclude={"rule_request"}),
            "rule_request": evaluation_request,
            "rule_evaluation": evaluate(evaluation_request, value.specification),
            "retrieval_request": query,
            "retrieval_response": retrieve(current, query, index),
        }
    )
