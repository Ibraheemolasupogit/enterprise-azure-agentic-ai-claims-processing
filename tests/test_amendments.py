"""Authored development metadata only; no historical stores or application demonstrations."""

import ast
from collections.abc import Callable
from datetime import timedelta
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.amendments import (
    MAX_DOCUMENT_BYTES,
    AmendmentBinding,
    AmendmentError,
    AmendmentPlan,
    AmendmentRequest,
    Invalidation,
    Precondition,
    ProposedDocument,
    ReasonCode,
    Requirement,
    canonical_plan,
    plan_amendment,
    source_binding,
)
from claims_ai.models import Case, CaseState, DocumentMetadata, ScanStatus


def proposal(document: DocumentMetadata, **changes: object) -> ProposedDocument:
    return ProposedDocument.model_validate(
        {**document.model_dump(), "scan_status": "quarantined", **changes}
    )


def request_for(case: Case, *documents: ProposedDocument) -> AmendmentRequest:
    return AmendmentRequest(expected=source_binding(case), proposed_documents=documents)


def extra_document(document: DocumentMetadata, number: int = 2) -> ProposedDocument:
    doc_id = f"NS-DOC-{number:08X}"
    return proposal(
        document,
        document_id=doc_id,
        artifact_ref=f"synthetic/{document.claim_id}/{doc_id}.pdf",
        kind="repair_estimate",
        sha256=sha256(f"authored-development-{number}".encode()).hexdigest(),
    )


def test_unchanged_inventory_is_noop_not_scan_downgrade(case: Case) -> None:
    result = plan_amendment(case, request_for(case, *(proposal(d) for d in case.documents)))
    assert result.reasons == (ReasonCode.UNCHANGED,)
    assert not (result.added or result.removed or result.replaced or result.requirements)
    assert not result.invalidations and not result.verification_documents
    assert case.documents[0].scan_status == ScanStatus.ACCEPTED
    assert result.preconditions == tuple(Precondition)
    assert result.execution_authorized is False
    assert result.final_outcome is None and result.settlement_authorized is False


def test_added_missing_estimate_requires_fresh_validation(case: Case) -> None:
    added = extra_document(case.documents[0])
    result = plan_amendment(case, request_for(case, proposal(case.documents[0]), added))
    assert [r.document_id for r in result.added] == [added.document_id]
    assert result.added[0].artifact_sha256 == added.sha256
    assert result.reasons == (ReasonCode.ADDED, ReasonCode.STALE)
    assert {Requirement.BYTES, Requirement.SCAN, Requirement.EVIDENCE} <= set(result.requirements)
    assert len(result.verification_documents) == 2  # M20 clears all admitted evidence.
    assert result.invalidations == tuple(Invalidation)


def test_replaced_bytes_invalidate_all_derived_material(case: Case) -> None:
    changed = proposal(case.documents[0], sha256="d" * 64)
    result = plan_amendment(case, request_for(case, changed))
    assert len(result.replaced) == 1
    assert not result.added and not result.removed
    assert result.replaced[0].previous.artifact_sha256 == case.documents[0].sha256
    assert result.replaced[0].proposed.artifact_sha256 == changed.sha256
    assert (
        result.replaced[0].previous.metadata_sha256 != result.replaced[0].proposed.metadata_sha256
    )
    assert {Invalidation.FACTS, Invalidation.ADVICE, Invalidation.REVIEW} <= set(
        result.invalidations
    )
    assert {Requirement.CORRECTION, Requirement.REASSESS, Requirement.REVIEW} <= set(
        result.requirements
    )


def test_removal_never_implies_missing_evidence_is_satisfied(case: Case) -> None:
    result = plan_amendment(case, request_for(case))
    assert result.removed[0].document_id == case.documents[0].document_id
    assert result.reasons == (ReasonCode.REMOVED, ReasonCode.STALE)
    assert not result.verification_documents
    assert Requirement.REASSESS in result.requirements and Requirement.REVIEW in result.requirements
    assert Requirement.BYTES not in result.requirements


def test_same_bytes_changed_metadata_is_still_replacement(case: Case) -> None:
    doc = case.documents[0]
    changed = proposal(doc, uploaded_at=doc.uploaded_at + timedelta(seconds=1))
    result = plan_amendment(case, request_for(case, changed))
    assert len(result.replaced) == 1
    assert result.reasons == (ReasonCode.REPLACED, ReasonCode.STALE)


def test_mixed_inventory_has_exact_sorted_deltas(case: Case) -> None:
    first = case.documents[0]
    second, third = extra_document(first, 2), extra_document(first, 3)
    current = Case.model_validate(
        {
            **case.model_dump(),
            "claim": {
                **case.claim.model_dump(),
                "document_ids": (first.document_id, second.document_id),
            },
            "documents": (first, second),
        }
    )
    result = plan_amendment(current, request_for(current, third, proposal(first, sha256="d" * 64)))
    assert [r.document_id for r in result.added] == [third.document_id]
    assert [r.document_id for r in result.removed] == [second.document_id]
    assert [r.previous.document_id for r in result.replaced] == [first.document_id]
    assert result.reasons == (
        ReasonCode.ADDED,
        ReasonCode.REMOVED,
        ReasonCode.REPLACED,
        ReasonCode.STALE,
    )


def test_repeat_and_proposal_order_produce_byte_identical_plans(
    case: Case,
    record_property: Callable[[str, object], None],
) -> None:
    docs = (
        extra_document(case.documents[0], 3),
        proposal(case.documents[0]),
        extra_document(case.documents[0], 2),
    )
    first = canonical_plan(plan_amendment(case, request_for(case, *docs)))
    for _ in range(10):
        assert canonical_plan(plan_amendment(case, request_for(case, *reversed(docs)))) == first
    decoded = AmendmentPlan.model_validate_json(first)
    assert canonical_plan(decoded) == first
    assert [d.document_id for d in decoded.added] == sorted(d.document_id for d in docs[::2])
    record_property("canonical_plan_sha256", sha256(first).hexdigest())
    record_property("canonical_plan_bytes", len(first))
    record_property("source_case_sha256", decoded.source.case_sha256)
    record_property("proposal_sha256", decoded.proposal_sha256)
    record_property("repetitions_with_reversed_inventory", 10)


def test_inputs_and_nested_results_are_immutable(case: Case) -> None:
    request = request_for(case, proposal(case.documents[0], sha256="d" * 64))
    before_case, before_request = case.model_dump_json(), request.model_dump_json()
    result = plan_amendment(case, request)
    assert case.model_dump_json() == before_case and request.model_dump_json() == before_request
    for record, field, value in (
        (request, "proposed_documents", ()),
        (request.proposed_documents[0], "sha256", "e" * 64),
        (result, "reasons", ()),
        (result.replaced[0].previous, "artifact_sha256", "e" * 64),
    ):
        with pytest.raises(ValidationError, match="frozen"):
            setattr(record, field, value)


@pytest.mark.parametrize(
    "field,value,code",
    [
        ("claim_id", "NS-CLM-99999999", "wrong_claim_binding"),
        ("policy_id", "NS-POL-99999999", "wrong_policy_binding"),
        ("case_revision", 2, "stale_case_revision"),
        ("case_sha256", "0" * 64, "source_hash_mismatch"),
        ("policy_sha256", "0" * 64, "source_hash_mismatch"),
    ],
)
def test_binding_mismatches_fail_closed(case: Case, field: str, value: object, code: str) -> None:
    expected = AmendmentBinding.model_validate({**source_binding(case).model_dump(), field: value})
    with pytest.raises(AmendmentError, match=f"^{code}$"):
        plan_amendment(case, AmendmentRequest(expected=expected, proposed_documents=()))


def test_changed_source_at_same_revision_is_not_a_duplicate_receipt(case: Case) -> None:
    request = request_for(case, proposal(case.documents[0], sha256="d" * 64))
    changed = Case.model_validate(
        {**case.model_dump(), "claim": {**case.claim.model_dump(), "narrative": "changed source"}}
    )
    with pytest.raises(AmendmentError, match="source_hash_mismatch"):
        plan_amendment(changed, request)


def test_original_source_inventory_order_is_not_normalized(case: Case) -> None:
    doc = extra_document(case.documents[0])
    current = Case.model_validate(
        {
            **case.model_dump(),
            "claim": {
                **case.claim.model_dump(),
                "document_ids": (*case.claim.document_ids, doc.document_id),
            },
            "documents": (*case.documents, doc),
        }
    )
    request = request_for(current, proposal(case.documents[0]), doc)
    reordered = Case.model_validate(
        {**current.model_dump(), "documents": tuple(reversed(current.documents))}
    )
    with pytest.raises(AmendmentError, match="source_hash_mismatch"):
        plan_amendment(reordered, request)


@pytest.mark.parametrize("conflicting", [False, True])
def test_duplicate_document_ids_rejected(case: Case, conflicting: bool) -> None:
    doc = proposal(case.documents[0])
    other = proposal(doc, sha256="d" * 64) if conflicting else doc
    with pytest.raises(ValidationError, match="conflicting_document_ids"):
        request_for(case, doc, other)


def test_foreign_document_is_rejected(case: Case) -> None:
    doc = proposal(
        case.documents[0],
        claim_id="NS-CLM-99999999",
        artifact_ref="synthetic/NS-CLM-99999999/NS-DOC-00000001.pdf",
    )
    with pytest.raises(ValidationError, match="wrong_document_claim"):
        request_for(case, doc)


@pytest.mark.parametrize(
    "field,value", [("byte_size", 1025), ("page_count", 3), ("media_type", "image/png")]
)
def test_same_hash_with_incompatible_intrinsic_metadata_rejected(
    case: Case,
    field: str,
    value: object,
) -> None:
    changes: dict[str, object] = {field: value}
    if field == "media_type":
        changes.update(page_count=1, artifact_ref=case.documents[0].artifact_ref[:-3] + "png")
    with pytest.raises(AmendmentError, match="conflicting_artifact_metadata"):
        plan_amendment(case, request_for(case, proposal(case.documents[0], **changes)))


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "not-a-hash"),
        ("byte_size", 0),
        ("byte_size", True),
        ("byte_size", MAX_DOCUMENT_BYTES + 1),
        ("page_count", -1),
        ("artifact_ref", "../../private.pdf"),
        ("artifact_ref", "https://example.invalid/a.pdf"),
        ("uploaded_at", "2026-01-01"),
        ("synthetic", False),
        ("schema_version", "2.0"),
        ("scan_status", "accepted"),
        ("scan_status", "rejected"),
        ("policy_id", "NS-POL-00000001"),
    ],
)
def test_malformed_or_authority_bearing_document_rejected(
    case: Case,
    field: str,
    value: object,
) -> None:
    with pytest.raises(ValidationError):
        proposal(case.documents[0], **{field: value})


@pytest.mark.parametrize(
    "field",
    [
        "approval_id",
        "approved_by",
        "role",
        "grant",
        "identity",
        "assignee_id",
        "decision",
        "replacement",
        "execution_authorized",
        "final_outcome",
        "settlement_authorized",
    ],
)
def test_request_cannot_supply_execution_authority(case: Case, field: str) -> None:
    with pytest.raises(ValidationError, match="Extra inputs"):
        AmendmentRequest.model_validate({**request_for(case).model_dump(), field: "untrusted"})


def test_inventory_capacity_and_document_byte_boundary(case: Case) -> None:
    assert proposal(case.documents[0], byte_size=MAX_DOCUMENT_BYTES).byte_size == MAX_DOCUMENT_BYTES
    docs = tuple(extra_document(case.documents[0], n) for n in range(2, 66))
    assert len(request_for(case, *docs).proposed_documents) == 64
    with pytest.raises(ValidationError, match="64"):
        request_for(case, *docs, extra_document(case.documents[0], 66))


def test_oversized_source_is_rejected(case: Case) -> None:
    doc = DocumentMetadata.model_validate(
        {**case.documents[0].model_dump(), "byte_size": MAX_DOCUMENT_BYTES + 1}
    )
    current = Case.model_validate({**case.model_dump(), "documents": (doc,)})
    with pytest.raises(AmendmentError, match="source_capacity_exceeded"):
        source_binding(current)


def test_closed_case_requires_supervisor_reopening(
    awaiting_case: Case,
    decision: object,
) -> None:
    closed = Case.model_validate(
        {**awaiting_case.model_dump(), "state": "closed", "revision": 6, "decision": decision}
    )
    result = plan_amendment(closed, request_for(closed))
    assert result.requirements[0] == Requirement.REOPEN
    assert ReasonCode.CLOSED in result.reasons
    assert closed.state == CaseState.CLOSED and closed.decision is not None
    assert result.final_outcome is None


def test_review_state_is_not_approved_by_planning(awaiting_case: Case) -> None:
    result = plan_amendment(awaiting_case, request_for(awaiting_case))
    assert Requirement.REVIEW in result.requirements
    assert Invalidation.REVIEW in result.invalidations
    assert awaiting_case.assessment is not None
    assert result.execution_authorized is False


def test_unvalidated_model_copies_are_revalidated(case: Case) -> None:
    request = request_for(case)
    bad_request = request.model_copy(update={"expected": {"case_revision": True}})
    with pytest.raises(ValidationError):
        plan_amendment(case, bad_request)
    bad_case = case.model_copy(update={"documents": ()})
    with pytest.raises(ValidationError):
        plan_amendment(bad_case, request)


def test_proposed_nested_model_copy_cannot_smuggle_scan_authority(case: Case) -> None:
    forged = proposal(case.documents[0]).model_copy(update={"scan_status": "accepted"})
    request = request_for(case).model_copy(update={"proposed_documents": (forged,)})
    with pytest.raises(ValidationError):
        plan_amendment(case, request)


@pytest.mark.parametrize("revision", [True, 0, "1"])
def test_revision_is_a_strict_positive_integer(case: Case, revision: object) -> None:
    with pytest.raises(ValidationError):
        AmendmentBinding.model_validate(
            {**source_binding(case).model_dump(), "case_revision": revision}
        )


def test_wrong_source_policy_binding_is_rejected(case: Case) -> None:
    assert case.policy is not None
    forged_policy = case.policy.model_copy(update={"policy_id": "NS-POL-99999999"})
    forged_case = case.model_copy(update={"policy": forged_policy})
    with pytest.raises(ValidationError, match="policy ID"):
        plan_amendment(forged_case, request_for(case))


def test_source_document_and_evidence_capacity(case: Case) -> None:
    docs = tuple(extra_document(case.documents[0], n) for n in range(2, 67))
    current = Case.model_validate(
        {
            **case.model_dump(),
            "claim": {
                **case.claim.model_dump(),
                "document_ids": tuple(d.document_id for d in docs),
            },
            "documents": docs,
            "evidence": (),
        }
    )
    with pytest.raises(AmendmentError, match="source_capacity_exceeded"):
        source_binding(current)
    evidence = tuple(
        case.evidence[0].model_copy(update={"evidence_id": f"NS-EVD-{n:08X}"}) for n in range(1025)
    )
    current = Case.model_validate({**case.model_dump(), "evidence": evidence})
    with pytest.raises(AmendmentError, match="source_capacity_exceeded"):
        source_binding(current)


def test_source_serialized_byte_capacity(case: Case) -> None:
    evidence = tuple(
        case.evidence[0].model_copy(
            update={
                "evidence_id": f"NS-EVD-{n:08X}",
                "observed_value": "x" * 4000,
                "normalized_value": "y" * 4000,
            }
        )
        for n in range(1024)
    )
    current = Case.model_validate({**case.model_dump(), "evidence": evidence})
    with pytest.raises(AmendmentError, match="source_capacity_exceeded"):
        source_binding(current)


def test_conflicting_metadata_between_new_documents_is_rejected(case: Case) -> None:
    first = extra_document(case.documents[0], 2)
    second = proposal(extra_document(case.documents[0], 3), sha256=first.sha256, byte_size=1025)
    with pytest.raises(AmendmentError, match="conflicting_artifact_metadata"):
        plan_amendment(case, request_for(case, first, second))


@pytest.mark.parametrize("level", ["request", "binding", "document"])
def test_unknown_versions_and_nested_authority_are_rejected(case: Case, level: str) -> None:
    request = request_for(case, proposal(case.documents[0])).model_dump()
    if level == "binding":
        request["expected"]["role"] = "supervisor"
    elif level == "document":
        request["proposed_documents"][0]["approval_id"] = "untrusted"
    else:
        request["format"] = "m25-amendment-request-v2"
    with pytest.raises(ValidationError):
        AmendmentRequest.model_validate(request)


def test_planning_needs_no_files_network_or_database(
    case: Case,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = request_for(case, proposal(case.documents[0], sha256="d" * 64))

    def denied(*args: object, **kwargs: object) -> None:
        raise AssertionError("pure planning attempted external access")

    # In-process regression checks only, not proof of host/process containment.
    with monkeypatch.context() as guard:
        guard.setattr("builtins.open", denied)
        guard.setattr(Path, "open", denied)
        guard.setattr("socket.socket", denied)
        guard.setattr("sqlite3.connect", denied)
        payload = canonical_plan(plan_amendment(case, request))
    assert payload


def test_output_contains_no_source_narrative_or_observed_values(case: Case) -> None:
    payload = canonical_plan(plan_amendment(case, request_for(case)))
    assert case.claim.narrative.encode() not in payload
    assert case.evidence[0].observed_value.encode() not in payload
    assert b"artifact_ref" not in payload and b"uploaded_at" not in payload


def test_planner_dependency_surface_is_pure() -> None:
    # Static dependency guard, not an OS sandbox or an M24 containment claim.
    path = Path(__file__).resolve().parents[1] / "src/claims_ai/amendments.py"
    tree = ast.parse(path.read_text())
    imports = {
        node.module if isinstance(node, ast.ImportFrom) else alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert imports == {"json", "enum", "hashlib", "typing", "pydantic", "claims_ai.models"}
    # Models and all their mutable-looking collections expose only frozen contracts/tuples.
    assert AmendmentRequest.model_config["frozen"] is True
    assert ProposedDocument.model_config["extra"] == "forbid"
