"""New authored SIMULATED snapshots; no imported M4 claim or real scan/reviewer assertions."""

from datetime import UTC, datetime
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from claims_ai.benchmark.contracts import (
    ExtractedField,
    ExtractionResponse,
    Provider,
    ProviderIdentity,
    SourceReference,
)
from claims_ai.dataset.generator import WARNING
from claims_ai.dataset.render import render_document
from claims_ai.dataset.schema import SourceDocument
from claims_ai.evidence.contracts import Disposition, ProcessingRequest
from claims_ai.evidence.normalization import FIELDS, OPTIONAL
from claims_ai.evidence.processing import admit_evidence, process_extraction
from claims_ai.knowledge.contracts import IngestionRequest, PolicyDocument
from claims_ai.knowledge.ingestion import SCHEDULE_NOTES, WORDING_NOTE, ingest
from claims_ai.models import (
    Case,
    CaseState,
    Claim,
    DocumentKind,
    DocumentMetadata,
    Policy,
    PolicyArtifact,
    ReviewerRole,
    RiskFlag,
    ScanStatus,
)
from claims_ai.rules.contracts import (
    EvaluationRequest,
    EvidenceInput,
    FixtureScenario,
    FixtureSuite,
    ReviewedFacts,
    RuleSpecification,
    SpecificationManifest,
)
from claims_ai.rules.specification import clause_texts, digest, money, pence


def load_scenarios(root: Path) -> FixtureSuite:
    manifest = SpecificationManifest.model_validate_json((root / "manifest.json").read_bytes())
    content = (root / "scenarios.json").read_bytes()
    if len(content) > 131072 or sha256(content).hexdigest() != manifest.scenarios_sha256:
        raise ValueError("rule fixture fingerprint/size mismatch")
    return FixtureSuite.model_validate_json(content)


def build_fixture(spec: RuleSpecification, scenario: FixtureScenario) -> EvaluationRequest:
    amount = money(pence(scenario.amount))
    claim_id = "NS-CLM-" + digest(scenario.fixture_id)[:8].upper()
    policy_id = "NS-POL-" + digest((scenario.fixture_id, "policy"))[:8].upper()
    vehicle = "SYNTHETIC-M9-VEHICLE"
    loss = scenario.incident_at.isoformat()
    documents: list[PolicyDocument] = []

    def document(
        kind: DocumentKind, key: str, title: str, lines: tuple[str, ...]
    ) -> DocumentMetadata:
        document_id = "NS-DOC-" + digest((scenario.fixture_id, key))[:8].upper()
        source = SourceDocument(
            document_id=document_id,
            title=title,
            lines=(WARNING, f"document_id: {document_id}", f"claim_id: {claim_id}", *lines),
            rendering="png-schematic" if kind == DocumentKind.DAMAGE_PHOTO else "pdf-text",
        )
        content = render_document(source)
        suffix = "png" if kind == DocumentKind.DAMAGE_PHOTO else "pdf"
        metadata = DocumentMetadata(
            document_id=document_id,
            claim_id=claim_id,
            kind=kind,
            media_type="image/png" if suffix == "png" else "application/pdf",
            artifact_ref=f"synthetic/{claim_id}/{document_id}.{suffix}",
            sha256=sha256(content).hexdigest(),
            byte_size=len(content),
            page_count=1,
            uploaded_at=datetime(2027, 2, 1, tzinfo=UTC),
            scan_status=ScanStatus.QUARANTINED
            if scenario.fault == "quarantined"
            else ScanStatus.ACCEPTED,
        )
        documents.append(PolicyDocument(document=metadata, source=source, content=content))
        return metadata

    document(
        DocumentKind.CLAIM_FORM,
        "form",
        "NORTHSTAR | M9 SYNTHETIC FORM",
        (
            f"policy_id: {policy_id}",
            f"loss_at: {loss}",
            f"vehicle_reference: {vehicle}",
            f"claimed_amount: {amount}",
            "currency: GBP",
            "narrative: Synthetic incident; classifications require explicit reviewer assertions.",
            f"submitted_policy_version: {scenario.policy_version}",
        ),
    )
    if scenario.fault != "missing_estimate":
        estimate_loss = (
            "2026-05-18T10:00:00+00:00" if scenario.fault == "contradictory_estimate" else loss
        )
        estimate = money(pence(amount) + 1) if scenario.fault == "amount_conflict" else amount
        document(
            DocumentKind.REPAIR_ESTIMATE,
            "estimate",
            "NORTHSTAR | M9 SYNTHETIC ESTIMATE",
            (
                f"vehicle_reference: {vehicle}",
                f"loss_at: {estimate_loss}",
                f"estimate_amount: {estimate}",
                "currency: GBP",
                "estimate_issued_at: 2027-02-01T00:00:00+00:00",
                "repairer_reference: SYNTHETIC-M9-REPAIRER",
            ),
        )
    document(
        DocumentKind.DAMAGE_PHOTO,
        "image",
        "M9 SYNTHETIC SCHEMATIC",
        ("damage_location: FRONT BUMPER",),
    )
    policies = []
    for terms in spec.terms:
        schedule = document(
            DocumentKind.POLICY_SCHEDULE,
            terms.policy_version + "-schedule",
            "NORTHSTAR | DRAFT MOTOR POLICY SCHEDULE",
            (
                f"policy_id: {policy_id}",
                f"policy_version: {terms.policy_version}",
                f"effective_from: {terms.effective_from}",
                f"effective_to: {terms.effective_to}",
                f"vehicle_reference: {vehicle}",
                *SCHEDULE_NOTES,
            ),
        )
        wording = document(
            DocumentKind.POLICY_WORDING,
            terms.policy_version + "-wording",
            "NORTHSTAR | DRAFT MOTOR POLICY WORDING",
            (
                f"policy_version: {terms.policy_version}",
                "product: motor_damage",
                "jurisdiction: GB",
                *(f"{clause} - {text}" for clause, text in clause_texts(terms).items()),
                WORDING_NOTE,
            ),
        )
        policies.append(
            Policy(
                policy_id=policy_id,
                version=terms.policy_version,
                effective_from=terms.effective_from,
                effective_to=terms.effective_to,
                schedule=PolicyArtifact(document_id=schedule.document_id, sha256=schedule.sha256),
                wording=PolicyArtifact(document_id=wording.document_id, sha256=wording.sha256),
                index_version="fixture-not-indexed",
                rule_pack_version="unapproved-no-rules",
            )
        )
    case = Case(
        claim=Claim(
            claim_id=claim_id,
            policy_id=policy_id,
            loss_at=scenario.incident_at,
            vehicle_reference=vehicle,
            narrative="Synthetic incident; classifications require explicit reviewer assertions.",
            claimed_amount=Decimal(amount),
            document_ids=tuple(d.document.document_id for d in documents),
        ),
        documents=tuple(d.document for d in documents),
        state=CaseState.EXTRACTING,
        revision=3,
    )
    base = case
    inputs = []
    identity = ProviderIdentity(
        provider=Provider.FIXTURE,
        model_version="m9-authored-fixture",
        adapter_version="1.0",
        execution_mode="SIMULATED",
    )
    for item in documents:
        metadata = item.document
        allowed = set(FIELDS[metadata.kind.value]) | set(OPTIONAL.get(metadata.kind.value, ()))
        fields = []
        for number, line in enumerate(item.source.lines, start=1):
            name, separator, value = line.partition(": ")
            if separator and name in allowed:
                fields.append(
                    ExtractedField(
                        name=name,
                        value=value,
                        sources=(
                            SourceReference(
                                document_id=metadata.document_id,
                                artifact_sha256=metadata.sha256,
                                page=1,
                                source_line=number
                                + (
                                    1
                                    if scenario.fault == "unverified"
                                    and metadata.kind == DocumentKind.CLAIM_FORM
                                    else 0
                                ),
                                location_kind="image_caption"
                                if metadata.kind == DocumentKind.DAMAGE_PHOTO
                                else "pdf_line",
                            ),
                        ),
                    )
                )
        response = ExtractionResponse(
            request_id=metadata.document_id,
            document_id=metadata.document_id,
            artifact_sha256=metadata.sha256,
            provider=identity,
            fields=tuple(fields),
        )
        original = ProcessingRequest(
            case=base,
            document_id=metadata.document_id,
            request_id=metadata.document_id,
            expected_provider=identity,
            content=item.content,
            fixture_source=item.source,
        )
        inputs.append(EvidenceInput(request=original, response=response))
        result = process_extraction(original, response)
        if result.disposition == Disposition.ACCEPTED:
            case = admit_evidence(case, result, allow_simulated=True).current
    case = Case.model_validate({**case.model_dump(), "state": "assessing"})
    narrative = tuple(e.evidence_id for e in case.evidence if e.field_name == "narrative")
    facts = (
        (
            ReviewedFacts(
                fact_id="synthetic-review-1",
                category=scenario.category,
                cause=scenario.cause,
                evidence_ids=narrative,
                case_sha256=digest(case.model_dump(mode="json")),
                reviewer_id=UUID("90000000-0000-0000-0000-000000000001"),
                role=ReviewerRole.REVIEWER,
            ),
        )
        if narrative and scenario.fault != "no_facts"
        else ()
    )
    return EvaluationRequest(
        case=case,
        policy_id=policy_id,
        policy_version=scenario.policy_version,
        index=ingest(
            IngestionRequest(case=case, policies=tuple(policies), documents=tuple(documents))
        ),
        specification_sha256=digest(spec.model_dump(mode="json")),
        evidence_inputs=tuple(inputs),
        reviewed_facts=facts,
        risk_flags=(RiskFlag.AMBIGUOUS,) if scenario.fault == "ambiguous" else (),
        allow_simulated_evidence=scenario.fault != "simulation_disabled",
    )
