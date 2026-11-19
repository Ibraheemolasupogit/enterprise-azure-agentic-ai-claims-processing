"""Pure synthetic amendment planning; no admission, identity grant or outcome execution."""

import json
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from claims_ai.models import (
    Case,
    CaseState,
    ClaimId,
    Contract,
    DocumentId,
    DocumentMetadata,
    PolicyId,
    PositiveInt,
    ScanStatus,
    Sha256,
)

# Conservative P1 budgets: M12's 64 evidence inputs, M6's default 1,024 records,
# the local Settings default 10 MiB/document and M15's default 4 MiB snapshot.
MAX_DOCUMENTS = 64
MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
MAX_EVIDENCE = 1024
MAX_CASE_BYTES = 4 * 1024 * 1024


def _canonical(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True, allow_nan=False) + "\n"
    ).encode()


def _hash(value: object) -> str:
    return sha256(_canonical(value)).hexdigest()


class AmendmentError(ValueError):
    """Fixed planning failure code; never includes document contents or credentials."""


class ProposedDocument(DocumentMetadata):
    """M6 metadata for unverified candidates, never a caller-supplied scan clearance."""

    scan_status: Literal[ScanStatus.QUARANTINED] = ScanStatus.QUARANTINED
    byte_size: Annotated[int, Field(strict=True, gt=0, le=MAX_DOCUMENT_BYTES)]


class AmendmentBinding(Contract):
    format: Literal["m25-source-binding-v1"] = "m25-source-binding-v1"
    claim_id: ClaimId
    policy_id: PolicyId
    case_revision: PositiveInt
    case_sha256: Sha256
    policy_sha256: Sha256


class AmendmentRequest(Contract):
    format: Literal["m25-amendment-request-v1"] = "m25-amendment-request-v1"
    expected: AmendmentBinding
    # Complete desired inventory, not a patch: omission means removal.
    proposed_documents: Annotated[tuple[ProposedDocument, ...], Field(max_length=MAX_DOCUMENTS)]

    @model_validator(mode="after")
    def scoped_inventory(self) -> Self:
        ids = [d.document_id for d in self.proposed_documents]
        if len(set(ids)) != len(ids):
            raise ValueError("conflicting_document_ids")
        if any(d.claim_id != self.expected.claim_id for d in self.proposed_documents):
            raise ValueError("wrong_document_claim")
        return self


class DocumentReference(Contract):
    document_id: DocumentId
    artifact_sha256: Sha256
    metadata_sha256: Sha256


class Replacement(Contract):
    previous: DocumentReference
    proposed: DocumentReference


class ReasonCode(StrEnum):
    UNCHANGED = "evidence_metadata_unchanged"
    ADDED = "document_added"
    REMOVED = "document_removed"
    REPLACED = "document_metadata_replaced"
    STALE = "source_bound_dependencies_stale"
    CLOSED = "closed_case_requires_supervisor_reopening"


class Requirement(StrEnum):
    BYTES = "verify_actual_bytes_hash_size_and_ownership"
    SCAN = "obtain_host_scan_clearance"
    EVIDENCE = "rerun_m6_provenance_validation_extraction_and_admission"
    POLICY = "reselect_and_verify_exact_policy"
    REASSESS = "rerun_provisional_rules_and_advisory"
    REVIEW = "obtain_fresh_canonical_human_review"
    CORRECTION = "use_existing_m20_correction_and_independent_revalidation"
    REOPEN = "require_m20_supervisor_reopening_before_correction"


class Invalidation(StrEnum):
    EVIDENCE = "admitted_evidence"
    FACTS = "reviewed_facts"
    POLICY = "policy_selection"
    RULES = "rule_results"
    ADVICE = "advisory"
    REVIEW = "m15_review_bindings"
    ASSIGNMENTS = "canonical_assignments"


class Precondition(StrEnum):
    SOURCE = "recheck_exact_source_hash_policy_and_revision_before_execution"
    IDENTITY = "recheck_m21_current_identity_revocation_and_canonical_scope"
    REVIEW = "use_m15_host_invalidation_and_current_review_preconditions"
    OUTCOME = "use_m20_authority_binding_and_atomic_audit_outbox"
    APPROVAL = "supply_independent_m20_approval_never_promote_advisory_approval"
    LIFECYCLE = "recheck_supported_m20_lifecycle_route_and_transition_revisions"
    RECOVERY = "use_same_runtime_and_independently_retained_recovery_trust"


class AmendmentPlan(Contract):
    format: Literal["m25-amendment-plan-v1"] = "m25-amendment-plan-v1"
    purpose: Literal["synthetic_metadata_planning_only"] = "synthetic_metadata_planning_only"
    source: AmendmentBinding
    proposal_sha256: Sha256
    added: tuple[DocumentReference, ...]
    removed: tuple[DocumentReference, ...]
    replaced: tuple[Replacement, ...]
    verification_documents: tuple[DocumentReference, ...]
    reasons: tuple[ReasonCode, ...]
    requirements: tuple[Requirement, ...]
    invalidations: tuple[Invalidation, ...]
    preconditions: tuple[Precondition, ...]
    execution_authorized: Literal[False] = False
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False


def _checked_case(case: Case) -> Case:
    case = Case.model_validate(case)
    if (
        len(case.documents) > MAX_DOCUMENTS
        or len(case.evidence) > MAX_EVIDENCE
        or any(d.byte_size > MAX_DOCUMENT_BYTES for d in case.documents)
        or len(_canonical(case.model_dump(mode="json"))) > MAX_CASE_BYTES
    ):
        raise AmendmentError("source_capacity_exceeded")
    return case


def _binding(case: Case) -> AmendmentBinding:
    return AmendmentBinding(
        claim_id=case.claim.claim_id,
        policy_id=case.claim.policy_id,
        case_revision=case.revision,
        case_sha256=_hash(case.model_dump(mode="json")),
        policy_sha256=_hash(case.policy.model_dump(mode="json") if case.policy else None),
    )


def source_binding(case: Case) -> AmendmentBinding:
    """Bind the host-supplied source; a matching hash is not authentication."""
    return _binding(_checked_case(case))


def _metadata(document: DocumentMetadata) -> dict[str, object]:
    # Quarantined proposals cannot grant scan clearance. An otherwise identical
    # proposal preserves the original source status; it is not a status update.
    return document.model_dump(mode="json", exclude={"scan_status"})


def _reference(document: DocumentMetadata) -> DocumentReference:
    return DocumentReference(
        document_id=document.document_id,
        artifact_sha256=document.sha256,
        metadata_sha256=_hash(_metadata(document)),
    )


def plan_amendment(case: Case, request: AmendmentRequest) -> AmendmentPlan:
    """Compare metadata only. All later execution needs fresh existing authority gates.

    No case, review binding, assignment, receipt or durable outcome is changed.
    Changed inputs conservatively invalidate all derived material, not just the
    changed document's fields. No transition/replacement Case is manufactured.
    """
    case = _checked_case(case)
    request = AmendmentRequest.model_validate(request)
    binding = _binding(case)
    if request.expected.claim_id != binding.claim_id:
        raise AmendmentError("wrong_claim_binding")
    if request.expected.policy_id != binding.policy_id:
        raise AmendmentError("wrong_policy_binding")
    if request.expected.case_revision != binding.case_revision:
        raise AmendmentError("stale_case_revision")
    if request.expected != binding:
        raise AmendmentError("source_hash_mismatch")

    previous = {d.document_id: d for d in case.documents}
    proposed = {d.document_id: d for d in request.proposed_documents}
    # Identical bytes cannot simultaneously assert incompatible intrinsic metadata.
    by_hash: dict[str, tuple[str, int, int]] = {}
    for document in (*case.documents, *request.proposed_documents):
        intrinsic = (document.media_type, document.byte_size, document.page_count)
        if document.sha256 in by_hash and by_hash[document.sha256] != intrinsic:
            raise AmendmentError("conflicting_artifact_metadata")
        by_hash[document.sha256] = intrinsic

    added = tuple(_reference(proposed[key]) for key in sorted(proposed.keys() - previous.keys()))
    removed = tuple(_reference(previous[key]) for key in sorted(previous.keys() - proposed.keys()))
    replaced = tuple(
        Replacement(previous=_reference(previous[key]), proposed=_reference(proposed[key]))
        for key in sorted(previous.keys() & proposed.keys())
        if _metadata(previous[key]) != _metadata(proposed[key])
    )
    changed = bool(added or removed or replaced)
    reasons: list[ReasonCode] = []
    for present, reason in (
        (bool(added), ReasonCode.ADDED),
        (bool(removed), ReasonCode.REMOVED),
        (bool(replaced), ReasonCode.REPLACED),
    ):
        if present:
            reasons.append(reason)
    requirements: list[Requirement] = []
    if changed:
        reasons.append(ReasonCode.STALE)
        if case.state == CaseState.CLOSED:
            reasons.append(ReasonCode.CLOSED)
            requirements.append(Requirement.REOPEN)
        requirements.append(Requirement.CORRECTION)
        if proposed:
            requirements.extend((Requirement.BYTES, Requirement.SCAN, Requirement.EVIDENCE))
        requirements.extend((Requirement.POLICY, Requirement.REASSESS, Requirement.REVIEW))
    else:
        reasons.append(ReasonCode.UNCHANGED)

    return AmendmentPlan(
        source=binding,
        proposal_sha256=_hash([proposed[key].model_dump(mode="json") for key in sorted(proposed)]),
        added=added,
        removed=removed,
        replaced=replaced,
        verification_documents=tuple(_reference(proposed[key]) for key in sorted(proposed))
        if changed
        else (),
        reasons=tuple(reasons),
        requirements=tuple(requirements),
        invalidations=tuple(Invalidation) if changed else (),
        preconditions=tuple(Precondition),
    )


def canonical_plan(plan: AmendmentPlan) -> bytes:
    """Deterministic serialization, not a signature or a trusted execution receipt."""
    return _canonical(AmendmentPlan.model_validate(plan).model_dump(mode="json"))
