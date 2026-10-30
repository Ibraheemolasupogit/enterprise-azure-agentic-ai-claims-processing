from datetime import datetime

import pytest
from pydantic import BaseModel, ValidationError

from claims_ai.models import (
    Assessment,
    Case,
    Claim,
    DocumentKind,
    DocumentMetadata,
    Evidence,
    Policy,
    PolicyClause,
    ReviewerDecision,
    RuleResult,
    validate_required_evidence,
)


def test_json_round_trips(
    claim: Claim,
    document: DocumentMetadata,
    evidence: Evidence,
    policy: Policy,
    assessment: Assessment,
    decision: ReviewerDecision,
    awaiting_case: Case,
) -> None:
    models: tuple[BaseModel, ...] = (
        claim,
        document,
        evidence,
        policy,
        assessment,
        decision,
        awaiting_case,
        PolicyClause(citation=assessment.citations[0], text="Synthetic clause example"),
        RuleResult(
            rule_id="fixture-rule", outcome=assessment.outcome, evidence_ids=assessment.evidence_ids
        ),
    )
    for model in models:
        assert type(model).model_validate_json(model.model_dump_json()) == model
        assert type(model).model_json_schema()["additionalProperties"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"claim_id": "real-claim"},
        {"claim_id": "NS-CLM-00000001\n"},
        {"policy_id": "NS-CLM-00000001"},
        {"narrative": "  "},
        {"loss_at": "2026-01-02T12:00:00"},
        {"claimed_amount": -1},
        {"claimed_amount": "NaN"},
        {"claimed_amount": "1.234"},
        {"claimed_amount": 0.1},
        {"claimed_amount": True},
        {"currency": "USD"},
        {"document_ids": ["NS-DOC-00000001", "NS-DOC-00000001"]},
        {"synthetic": False},
        {"synthetic": 1},
        {"schema_version": "2.0"},
        {"unexpected_secret": "SYNTHETIC SECRET"},
    ],
)
def test_invalid_claim_data(claim: Claim, changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Claim.model_validate({**claim.model_dump(), **changes})


def test_frozen_and_private_representations(claim: Claim, evidence: Evidence) -> None:
    with pytest.raises(ValidationError):
        claim.narrative = "changed"  # type: ignore[misc]
    assert claim.narrative not in repr(claim)
    assert evidence.observed_value not in repr(evidence)
    with pytest.raises(ValidationError) as error:
        Claim.model_validate({**claim.model_dump(), "narrative": ""})
    assert claim.narrative not in str(error.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"artifact_ref": "../../secrets.pdf"},
        {"artifact_ref": "https://example.invalid/file.pdf?sig=SYNTHETIC"},
        {"artifact_ref": "synthetic/NS-CLM-99999999/NS-DOC-00000001.pdf"},
        {"artifact_ref": "synthetic/NS-CLM-00000001/NS-DOC-00000001.png"},
        {"sha256": "not-a-hash"},
        {"byte_size": 0},
        {"byte_size": True},
        {"page_count": -1},
        {"media_type": "application/octet-stream"},
        {"kind": "damage_photo"},
        {"uploaded_at": "2026-01-01"},
    ],
)
def test_document_validation(document: DocumentMetadata, changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        DocumentMetadata.model_validate({**document.model_dump(), **changes})


def test_image_metadata(document: DocumentMetadata) -> None:
    image = {
        **document.model_dump(),
        "kind": "damage_photo",
        "media_type": "image/jpeg",
        "artifact_ref": f"synthetic/{document.claim_id}/{document.document_id}.jpg",
        "page_count": 1,
    }
    assert DocumentMetadata.model_validate(image).page_count == 1
    with pytest.raises(ValidationError):
        DocumentMetadata.model_validate({**image, "page_count": 2})


@pytest.mark.parametrize(
    "changes",
    [
        {"confidence": -0.1},
        {"confidence": 1.1},
        {"confidence": float("nan")},
        {"page": 0},
        {"bounding_region": [0.5, 0.1, 0.2, 0.3]},
        {"bounding_region": [0.1, 0.1, float("inf"), 0.3]},
        {"field_name": "free text"},
    ],
)
def test_evidence_validation(evidence: Evidence, changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Evidence.model_validate({**evidence.model_dump(), **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"version": ""},
        {"index_version": "version with spaces"},
        {"rule_pack_version": ""},
        {"effective_to": "2026-01-01"},
        {"effective_to": "2025-01-01"},
        {"jurisdiction": "US"},
    ],
)
def test_policy_metadata(policy: Policy, changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Policy.model_validate({**policy.model_dump(), **changes})


def test_duplicate_policy_artifacts(policy: Policy) -> None:
    with pytest.raises(ValidationError):
        Policy.model_validate({**policy.model_dump(), "endorsements": [policy.wording]})


@pytest.mark.parametrize(
    "changes",
    [
        {"policy_version": "fixture-v2"},
        {"document_id": "NS-DOC-00000099"},
        {"artifact_sha256": "e" * 64},
        {"policy_id": "NS-POL-00000099"},
    ],
)
def test_exact_policy_citation(assessment: Assessment, changes: dict[str, object]) -> None:
    citation = {**assessment.citations[0].model_dump(), **changes}
    with pytest.raises(ValidationError):
        Assessment.model_validate({**assessment.model_dump(), "citations": [citation]})


def test_assessment_references(assessment: Assessment) -> None:
    with pytest.raises(ValidationError):
        Assessment.model_validate({**assessment.model_dump(), "evidence_ids": []})
    with pytest.raises(ValidationError):
        Assessment.model_validate(
            {**assessment.model_dump(), "evidence_ids": assessment.evidence_ids * 2}
        )
    with pytest.raises(ValidationError):
        Assessment.model_validate(
            {
                **assessment.model_dump(),
                "rule_results": [
                    {
                        "rule_id": "fixture",
                        "outcome": "eligible",
                        "evidence_ids": ["NS-EVD-00000099"],
                    }
                ],
            }
        )


@pytest.mark.parametrize(
    "changes",
    [
        {"claim_id": "NS-CLM-00000099"},
        {"document_id": "NS-DOC-00000099"},
        {"artifact_sha256": "e" * 64},
        {"page": 3},
    ],
)
def test_case_provenance(case: Case, evidence: Evidence, changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        Case.model_validate(
            {**case.model_dump(), "evidence": [{**evidence.model_dump(), **changes}]}
        )


def test_case_rejects_unscanned_and_duplicate_documents(case: Case) -> None:
    for scan_status in ("quarantined", "rejected"):
        with pytest.raises(ValidationError):
            Case.model_validate(
                {
                    **case.model_dump(),
                    "documents": [{**case.documents[0].model_dump(), "scan_status": scan_status}],
                }
            )
    with pytest.raises(ValidationError):
        Case.model_validate({**case.model_dump(), "documents": case.documents * 2})
    with pytest.raises(ValidationError):
        Case.model_validate({**case.model_dump(), "evidence": case.evidence * 2})


def test_required_evidence_is_explicit_not_a_coverage_rule(case: Case) -> None:
    validate_required_evidence(case, frozenset({DocumentKind.CLAIM_FORM}))
    with pytest.raises(ValueError, match="required evidence"):
        validate_required_evidence(case, frozenset({DocumentKind.REPAIR_ESTIMATE}))
    no_extraction = Case.model_validate({**case.model_dump(), "evidence": []})
    with pytest.raises(ValueError, match="required evidence"):
        validate_required_evidence(no_extraction, frozenset({DocumentKind.CLAIM_FORM}))


def test_nested_instances_are_revalidated(case: Case) -> None:
    forged = case.claim.model_copy(update={"claim_id": "invalid"})
    with pytest.raises(ValidationError):
        Case.model_validate({**case.model_dump(), "claim": forged})


def test_assessment_cannot_appear_before_review(case: Case, assessment: Assessment) -> None:
    with pytest.raises(ValidationError):
        Case.model_validate({**case.model_dump(), "assessment": assessment})


def test_policy_dates_are_metadata_not_coverage_decisions(policy: Policy, now: datetime) -> None:
    # No loss-date eligibility rule or financial calculation is executed by these contracts.
    assert policy.effective_from < now.date() < policy.effective_to
