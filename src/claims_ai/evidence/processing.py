"""Pure mapping/quarantine boundary and guarded in-memory admission; no service clients."""

from hashlib import sha256

from claims_ai.benchmark.contracts import ExtractionResponse
from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.render import render_document
from claims_ai.evidence.contracts import (
    Disposition,
    EvidenceAdmission,
    EvidenceHistory,
    EvidenceRecord,
    IssueCode,
    ProcessingReceipt,
    ProcessingRequest,
    ProcessingResult,
    QualityMetadata,
    ValidationIssue,
)
from claims_ai.evidence.normalization import FIELDS, OPTIONAL, SHARED, normalize
from claims_ai.models import Case, CaseState, DocumentKind, Evidence, ScanStatus


def digest(value: object) -> str:
    return sha256(json_bytes(value)).hexdigest()


def _issue(
    code: IssueCode, severity: str, action: str, field: str | None = None
) -> ValidationIssue:
    return ValidationIssue.model_validate(
        {"code": code, "severity": severity, "action": action, "field_name": field}
    )


def process_extraction(
    request: ProcessingRequest, raw_response: object, history: EvidenceHistory | None = None
) -> ProcessingResult:
    request = ProcessingRequest.model_validate(request)
    case = request.case
    history = EvidenceHistory.model_validate(
        history or EvidenceHistory(claim_id=case.claim.claim_id)
    )
    if history.claim_id != case.claim.claim_id:
        raise ValueError("history ownership mismatch")
    issues: list[ValidationIssue] = []
    candidates: list[EvidenceRecord] = []
    response: ExtractionResponse | None = None
    payload = b"malformed-non-json-response"
    try:
        raw = (
            ExtractionResponse.model_validate(raw_response).model_dump(mode="json")
            if isinstance(raw_response, ExtractionResponse)
            else raw_response
        )
        if type(raw) is not dict:
            raise ValueError("expected decoded response object")
        payload = json_bytes(raw)
        if len(payload) > request.policy.max_response_bytes:
            issues.append(_issue(IssueCode.LIMIT, "reject", "correct_response"))
        else:
            fields = raw.get("fields")
            if isinstance(fields, (list, tuple)) and len(fields) > request.policy.max_fields:
                issues.append(_issue(IssueCode.LIMIT, "reject", "correct_response"))
            elif isinstance(fields, (list, tuple)) and all(isinstance(f, dict) for f in fields):
                names = [f.get("name") for f in fields]
                if all(isinstance(n, str) for n in names) and len(names) != len(set(names)):
                    issues.append(
                        _issue(IssueCode.DUPLICATE_FIELD, "quarantine", "correct_response")
                    )
            if not issues:
                response = ExtractionResponse.model_validate(raw)
    except (ValueError, TypeError, OverflowError, RecursionError):
        issues.append(_issue(IssueCode.MALFORMED, "reject", "correct_response"))
    response_hash = sha256(payload).hexdigest()
    if response is not None:
        canonical = response.model_dump(mode="json", exclude={"latency_ms", "usage"})
        canonical["fields"] = sorted(canonical["fields"], key=lambda f: f["name"])
        for field in canonical["fields"]:
            field["sources"] = sorted(field["sources"], key=json_bytes)
        response_hash = digest(canonical)
    claim_hash = digest(case.claim.model_dump(mode="json"))
    document = next((d for d in case.documents if d.document_id == request.document_id), None)
    operation_key = digest(
        {
            "claim": claim_hash,
            "document": document.model_dump(mode="json") if document else request.document_id,
            "bytes": sha256(request.content).hexdigest(),
            "response": response_hash,
            "provider": request.expected_provider.model_dump(mode="json"),
            "request_id": request.request_id,
            "source": request.fixture_source.model_dump(mode="json")
            if request.fixture_source
            else None,
            "policy": request.policy.model_dump(mode="json"),
        }
    )
    prior = next((r for r in history.receipts if r.operation_key == operation_key), None)
    if prior:
        return ProcessingResult(
            operation_key=operation_key,
            disposition=Disposition.DUPLICATE,
            candidates=(),
            issues=prior.issues,
            history=history,
            replay_of=prior.disposition,
        )
    if document is None or document.claim_id != case.claim.claim_id:
        issues.append(_issue(IssueCode.OWNERSHIP, "reject", "verify_case_and_bytes"))
    elif (
        len(request.content) != document.byte_size
        or sha256(request.content).hexdigest() != document.sha256
    ):
        issues.append(_issue(IssueCode.HASH, "reject", "verify_case_and_bytes"))
    if (
        response
        and document
        and (
            response.document_id != document.document_id
            or response.artifact_sha256 != document.sha256
            or response.request_id != request.request_id
            or response.provider != request.expected_provider
        )
    ):
        issues.append(_issue(IssueCode.IDENTITY, "reject", "verify_case_and_bytes"))
    source = request.fixture_source
    try:
        verified = bool(
            document
            and source
            and document.page_count == 1
            and source.document_id == document.document_id
            and len(source.lines) >= 3
            and source.lines[1] == f"document_id: {document.document_id}"
            and source.lines[2] == f"claim_id: {case.claim.claim_id}"
            and (
                (source.rendering == "pdf-text" and document.media_type == "application/pdf")
                or (source.rendering == "png-schematic" and document.media_type == "image/png")
            )
            and render_document(source) == request.content
        )
    except (ValueError, StopIteration):
        verified = False
    if source is not None and not verified:
        issues.append(_issue(IssueCode.SOURCE, "reject", "verify_source"))
    if not verified:
        issues.append(_issue(IssueCode.SOURCE, "quarantine", "verify_source"))
    if document and document.scan_status != ScanStatus.ACCEPTED:
        severity = "reject" if document.scan_status == ScanStatus.REJECTED else "quarantine"
        issues.append(
            _issue(
                IssueCode.SCAN,
                severity,
                "human_review" if severity == "reject" else "complete_scan",
            )
        )
    if document and document.kind.value not in FIELDS:
        issues.append(_issue(IssueCode.UNSUPPORTED, "quarantine", "human_review"))
    if response and document and not any(i.severity == "reject" for i in issues):
        required = FIELDS.get(document.kind.value, ())
        allowed = set(required) | set(OPTIONAL.get(document.kind.value, ()))
        found = {f.name for f in response.fields if f.value is not None and f.value.strip()}
        for name in required:
            if name not in found:
                issues.append(_issue(IssueCode.MISSING, "quarantine", "request_fields", name))
        for field in sorted(response.fields, key=lambda f: f.name):
            if field.name not in allowed:
                issues.append(
                    _issue(IssueCode.UNSUPPORTED, "quarantine", "human_review", field.name)
                )
                continue
            if field.value is None or not field.value.strip():
                continue
            refs = field.sources
            if any(
                s.document_id != document.document_id
                or s.artifact_sha256 != document.sha256
                or (s.page is not None and s.page > document.page_count)
                for s in refs
            ):
                issues.append(_issue(IssueCode.PROVENANCE, "reject", "verify_source", field.name))
                continue
            if not refs or any(
                s.page is None or s.source_line is None or s.location_kind is None for s in refs
            ):
                issues.append(
                    _issue(IssueCode.PROVENANCE, "quarantine", "verify_source", field.name)
                )
                continue
            valid_refs = bool(refs) and all(
                s.document_id == document.document_id
                and s.artifact_sha256 == document.sha256
                and s.page is not None
                and s.page <= document.page_count
                and (source is None or s.page == 1)
                and s.source_line is not None
                and (source is None or s.source_line <= len(source.lines))
                and s.location_kind
                == ("image_caption" if document.kind == DocumentKind.DAMAGE_PHOTO else "pdf_line")
                for s in refs
            )
            if valid_refs and source:
                valid_refs = all(
                    source.lines[s.source_line - 1] == f"{field.name}: {field.value}"
                    for s in refs
                    if s.source_line is not None
                )
            if not valid_refs:
                issues.append(_issue(IssueCode.PROVENANCE, "reject", "verify_source", field.name))
                continue
            if len({ref.page for ref in refs}) != 1:
                issues.append(
                    _issue(IssueCode.UNSUPPORTED, "quarantine", "human_review", field.name)
                )
                continue
            try:
                normalized = normalize(field.name, field.value)
            except (ValueError, OverflowError):
                issues.append(_issue(IssueCode.VALUE, "quarantine", "correct_response", field.name))
                continue
            bindings = {
                "claim_id": case.claim.claim_id,
                "document_id": document.document_id,
                "policy_id": case.claim.policy_id,
                "vehicle_reference": case.claim.vehicle_reference,
            }
            if field.name in bindings and normalized != bindings[field.name]:
                issues.append(
                    _issue(IssueCode.IDENTIFIER, "quarantine", "verify_case_and_bytes", field.name)
                )
            scope = (
                "claim"
                if document.kind in {DocumentKind.CLAIM_FORM, DocumentKind.REPAIR_ESTIMATE}
                and field.name in SHARED
                else document.document_id
            )
            baseline = {
                "loss_at": normalize("loss_at", case.claim.loss_at.isoformat()),
                "claimed_amount": f"{case.claim.claimed_amount:.2f}",
                "currency": case.claim.currency,
                "narrative": normalize("narrative", case.claim.narrative),
            }
            if scope == "claim" and field.name in baseline and normalized != baseline[field.name]:
                issues.append(_issue(IssueCode.CONFLICT, "quarantine", "human_review", field.name))
            if any(
                r.scope == scope
                and r.evidence.field_name == field.name
                and r.evidence.normalized_value != normalized
                for r in history.records
            ):
                issues.append(_issue(IssueCode.CONFLICT, "quarantine", "human_review", field.name))
            warnings = []
            if field.confidence is None:
                warnings.append(IssueCode.CONFIDENCE_MISSING)
                issues.append(
                    _issue(IssueCode.CONFIDENCE_MISSING, "warning", "human_review", field.name)
                )
            threshold = request.policy.minimum_reported_confidence
            if threshold is not None and (
                field.confidence is None or field.confidence.value < threshold
            ):
                issues.append(
                    _issue(IssueCode.CONFIDENCE_LOW, "quarantine", "human_review", field.name)
                )
            sources = tuple(sorted(refs, key=lambda r: json_bytes(r.model_dump(mode="json"))))
            record_hash = digest(
                {
                    "claim": case.claim.claim_id,
                    "document": document.document_id,
                    "raw": field.value,
                    "normalized": normalized,
                    "field": field.name,
                    "sources": [s.model_dump(mode="json") for s in sources],
                    "provider": response.provider.model_dump(mode="json"),
                    "scope": scope,
                    "confidence": field.confidence.model_dump(mode="json")
                    if field.confidence
                    else None,
                    "policy": request.policy.model_dump(mode="json"),
                }
            )
            evidence = Evidence(
                evidence_id="NS-EVD-" + record_hash[:8].upper(),
                claim_id=case.claim.claim_id,
                document_id=document.document_id,
                artifact_sha256=document.sha256,
                page=refs[0].page or 1,
                bounding_region=sources[0].bounding_region,
                field_name=field.name,
                observed_value=field.value,
                normalized_value=normalized,
                extraction_method=response.provider.provider.value,
                extraction_version=response.provider.model_version,
                confidence=field.confidence.value if field.confidence else None,
                validation_flags=("uncalibrated_confidence",)
                + (
                    ("simulated_extraction",)
                    if response.provider.execution_mode == "SIMULATED"
                    else ()
                ),
            )
            record = EvidenceRecord(
                evidence=evidence,
                raw_value=field.value,
                provider=response.provider,
                reported_confidence=field.confidence,
                sources=sources,
                scope=scope,
                record_sha256=record_hash,
                quality=QualityMetadata(
                    source_verification="fixture_render_verified"
                    if verified
                    else "structural_only",
                    confidence_status="unavailable"
                    if field.confidence is None
                    else "reported_uncalibrated",
                    minimum_reported_confidence=threshold,
                    warnings=tuple(warnings),
                ),
            )
            existing = next(
                (
                    r
                    for r in (*history.records, *candidates)
                    if r.evidence.evidence_id == evidence.evidence_id
                ),
                None,
            )
            if existing and existing.record_sha256 != record_hash:
                issues.append(_issue(IssueCode.COLLISION, "reject", "human_review", field.name))
                continue
            elif existing:
                issues.append(
                    _issue(IssueCode.DUPLICATE_EVIDENCE, "warning", "no_action", field.name)
                )
            # Proposals are retained for review; a blocking issue prevents whole-document admission.
            candidates.append(record)
    intervals = {r.evidence.field_name: r.evidence.normalized_value for r in candidates}
    start, end = intervals.get("effective_from"), intervals.get("effective_to")
    if start is not None and end is not None and start >= end:
        issues.append(_issue(IssueCode.VALUE, "quarantine", "correct_response", "effective_to"))
    disposition = (
        Disposition.REJECTED
        if any(i.severity == "reject" for i in issues)
        else (
            Disposition.QUARANTINED
            if any(i.severity == "quarantine" for i in issues)
            else Disposition.ACCEPTED
        )
    )
    additions = tuple(
        r
        for r in candidates
        if r.evidence.evidence_id not in {x.evidence.evidence_id for x in history.records}
    )
    if len(history.receipts) >= request.policy.max_receipts or (
        disposition == Disposition.ACCEPTED
        and len(history.records) + len(additions) > request.policy.max_records
    ):
        return ProcessingResult(
            operation_key=operation_key,
            disposition=Disposition.REJECTED,
            candidates=(),
            issues=(_issue(IssueCode.HISTORY_LIMIT, "reject", "archive_history"),),
            history=history,
        )
    receipt = ProcessingReceipt(
        operation_key=operation_key,
        response_sha256=response_hash,
        claim_sha256=claim_hash,
        document_id=request.document_id,
        disposition=disposition,
        candidate_ids=tuple(r.evidence.evidence_id for r in candidates),
        issues=tuple(issues),
    )
    updated = EvidenceHistory(
        claim_id=history.claim_id,
        records=history.records + (additions if disposition == Disposition.ACCEPTED else ()),
        receipts=history.receipts + (receipt,),
    )
    return ProcessingResult(
        operation_key=operation_key,
        disposition=disposition,
        candidates=tuple(candidates),
        issues=tuple(issues),
        history=updated,
    )


def admit_evidence(
    case: Case, result: ProcessingResult, *, allow_simulated: bool = False
) -> EvidenceAdmission:
    case = Case.model_validate(case)
    result = ProcessingResult.model_validate(result)
    if (
        case.state not in {CaseState.EXTRACTING, CaseState.ASSESSING}
        or result.history.claim_id != case.claim.claim_id
    ):
        raise ValueError("admission requires matching case in evidence-processing state")
    receipt = next(
        (r for r in result.history.receipts if r.operation_key == result.operation_key), None
    )
    if (
        receipt is None
        or receipt.disposition != Disposition.ACCEPTED
        or receipt.claim_sha256 != digest(case.claim.model_dump(mode="json"))
    ):
        raise ValueError("quarantined/rejected/stale processing cannot enter case evidence")
    records = tuple(
        r for r in result.history.records if r.evidence.evidence_id in receipt.candidate_ids
    )
    if len(records) != len(receipt.candidate_ids):
        raise ValueError("accepted receipt must resolve every evidence record")
    simulated = any(r.provider.execution_mode == "SIMULATED" for r in records)
    if simulated and not allow_simulated:
        raise ValueError("simulation admission requires explicit local opt-in")
    existing = {e.evidence_id: e for e in case.evidence}
    for record in records:
        if (
            record.evidence.evidence_id in existing
            and existing[record.evidence.evidence_id] != record.evidence
        ):
            raise ValueError("evidence identity collision")
    additions = tuple(r.evidence for r in records if r.evidence.evidence_id not in existing)
    current = Case.model_validate(
        {
            **case.model_dump(),
            "revision": case.revision + bool(additions),
            "evidence": case.evidence + additions,
        }
    )
    return EvidenceAdmission(
        previous=case,
        current=current,
        operation_key=result.operation_key,
        execution_mode="SIMULATED" if simulated else "LIVE",
    )
