"""Hand-authored synthetic contract examples, not approved insurance policies or golden data."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from claims_ai.models import (
    Assessment,
    AssessmentOutcome,
    Case,
    CaseState,
    Claim,
    DecisionAction,
    DocumentKind,
    DocumentMetadata,
    Evidence,
    Policy,
    PolicyArtifact,
    PolicyCitation,
    ReviewerDecision,
    ReviewerRole,
    ScanStatus,
)


@pytest.fixture
def now() -> datetime:
    return datetime(2026, 1, 2, 12, tzinfo=UTC)


@pytest.fixture
def reviewer_id() -> UUID:
    return UUID("10000000-0000-0000-0000-000000000001")


@pytest.fixture
def claim(now: datetime) -> Claim:
    return Claim(
        claim_id="NS-CLM-00000001",
        policy_id="NS-POL-00000001",
        loss_at=now,
        vehicle_reference="SYNTHETIC-VEHICLE-01",
        narrative="SYNTHETIC private narrative",
        claimed_amount=Decimal("123.45"),
        document_ids=("NS-DOC-00000001",),
    )


@pytest.fixture
def document(claim: Claim, now: datetime) -> DocumentMetadata:
    return DocumentMetadata(
        document_id="NS-DOC-00000001",
        claim_id=claim.claim_id,
        kind=DocumentKind.CLAIM_FORM,
        media_type="application/pdf",
        artifact_ref=f"synthetic/{claim.claim_id}/NS-DOC-00000001.pdf",
        sha256="a" * 64,
        byte_size=1024,
        page_count=2,
        uploaded_at=now,
        scan_status=ScanStatus.ACCEPTED,  # Fixture assertion; no scanner is executed.
    )


@pytest.fixture
def evidence(document: DocumentMetadata) -> Evidence:
    return Evidence(
        evidence_id="NS-EVD-00000001",
        claim_id=document.claim_id,
        document_id=document.document_id,
        artifact_sha256=document.sha256,
        page=1,
        bounding_region=(0.1, 0.1, 0.5, 0.2),
        field_name="loss_description",
        observed_value="SYNTHETIC private OCR content",
        normalized_value="SYNTHETIC normalized content",
        extraction_method="hand-authored-fixture",
        extraction_version="1.0",
        confidence=None,
    )


@pytest.fixture
def policy(claim: Claim) -> Policy:
    return Policy(
        policy_id=claim.policy_id,
        version="fixture-v1",
        effective_from=date(2026, 1, 1),
        effective_to=date(2027, 1, 1),
        schedule=PolicyArtifact(document_id="NS-DOC-00000002", sha256="b" * 64),
        wording=PolicyArtifact(document_id="NS-DOC-00000003", sha256="c" * 64),
        index_version="fixture-index-v1",
        rule_pack_version="unapproved-fixture-v1",
    )


@pytest.fixture
def case(claim: Claim, document: DocumentMetadata, evidence: Evidence, policy: Policy) -> Case:
    return Case(claim=claim, documents=(document,), evidence=(evidence,), policy=policy)


@pytest.fixture
def assessment(case: Case, policy: Policy) -> Assessment:
    return Assessment(
        assessment_id="NS-ASM-00000001",
        claim_id=case.claim.claim_id,
        case_revision=4,
        policy=policy,
        input_sha256="d" * 64,
        producer_version="hand-authored-fixture-v1",
        evidence_ids=("NS-EVD-00000001",),
        citations=(
            PolicyCitation(
                policy_id=policy.policy_id,
                policy_version=policy.version,
                document_id=policy.wording.document_id,
                artifact_sha256=policy.wording.sha256,
                clause_id="fixture-clause-1",
                page=1,
            ),
        ),
        outcome=AssessmentOutcome.ELIGIBLE,  # Supplied test value, not a coverage calculation.
        rationale="Synthetic assessment contract example only",
    )


@pytest.fixture
def awaiting_case(case: Case, assessment: Assessment) -> Case:
    return Case.model_validate(
        {
            **case.model_dump(),
            "state": CaseState.AWAITING_REVIEW,
            "revision": 5,
            "assessment": assessment,
        }
    )


@pytest.fixture
def decision(awaiting_case: Case, reviewer_id: UUID, now: datetime) -> ReviewerDecision:
    return ReviewerDecision(
        claim_id=awaiting_case.claim.claim_id,
        assessment_id="NS-ASM-00000001",
        expected_case_revision=5,
        reviewer_id=reviewer_id,
        role=ReviewerRole.REVIEWER,
        action=DecisionAction.APPROVE,
        outcome=AssessmentOutcome.ELIGIBLE,
        reason="Synthetic human approval example",
        evidence_ids=("NS-EVD-00000001",),
        decided_at=now,
    )
