"""Versioned dataset annotations, kept separate from operational domain evidence."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, StrictInt, model_validator

from claims_ai.models import (
    Case,
    CaseState,
    Contract,
    DocumentId,
    DocumentKind,
    Evidence,
    Policy,
    PositiveInt,
    ReviewerRole,
    RiskFlag,
    ScanStatus,
    Sha256,
    Text,
    Version,
)

Seed = Annotated[StrictInt, Field(ge=0, le=2**32 - 1)]


class Scenario(StrEnum):
    STRAIGHTFORWARD = "straightforward_front_damage"
    SECOND_VERSION = "straightforward_side_damage_v2"
    MISSING_ESTIMATE = "missing_repair_estimate"
    MISSING_PHOTO = "missing_damage_image"
    CONFLICT = "conflicting_loss_dates"
    EXPIRED = "expired_policy_metadata"
    WRONG_VERSION = "wrong_submitted_policy_version"
    HIGH_VALUE = "high_value_manual_risk_label"
    EXCLUSION = "draft_exclusion_candidate"
    DUPLICATE = "duplicate_submission"
    INJECTION = "malicious_document_instructions"
    BOUNDARY = "exact_policy_version_boundary"


class SourceDocument(Contract):
    document_id: DocumentId
    title: Text
    lines: Annotated[tuple[Text, ...], Field(min_length=1, max_length=38)]
    rendering: Literal["pdf-text", "png-schematic"]

    @model_validator(mode="after")
    def safe_layout(self) -> Self:
        for text in (self.title, *self.lines):
            if not text.isascii() or any(ord(char) < 32 for char in text) or len(text) > 94:
                raise ValueError("fixture text must be printable ASCII within layout limits")
        return self


class FieldTruth(Contract):
    expected: Evidence
    source_line: PositiveInt
    location_kind: Literal["pdf_line", "image_caption"]


class PolicySelectionTruth(Contract):
    submitted_version: Version
    expected_version: Version | None
    basis: Literal["fixture_interval", "outside_fixture_intervals", "conflicting_source_dates"]
    approval_status: Literal["unapproved_fixture_metadata_only"] = (
        "unapproved_fixture_metadata_only"
    )


class ReviewTruth(Contract):
    expected_role: ReviewerRole
    expected_action: Literal[
        "handler_triage", "request_evidence", "supervisor_triage", "duplicate_triage"
    ]
    risk_flags: tuple[RiskFlag, ...] = ()
    human_outcome_required: Literal[True] = True
    automatic_outcome_allowed: Literal[False] = False
    coverage_outcome: Literal[None] = None
    label_basis: Literal["authored_scenario_not_executed_workflow"] = (
        "authored_scenario_not_executed_workflow"
    )

    @model_validator(mode="after")
    def escalation(self) -> Self:
        if self.risk_flags and self.expected_role != ReviewerRole.SUPERVISOR:
            raise ValueError("flagged dataset review requires supervisor labeling")
        if self.expected_action in {"supervisor_triage", "duplicate_triage"}:
            if self.expected_role != ReviewerRole.SUPERVISOR:
                raise ValueError("supervisor action must have supervisor role")
        return self


class SampleTruth(Contract):
    scenario_id: Version
    scenario: Scenario
    submission_id: Version
    duplicate_of: Version | None = None
    input_case: Case
    policies: Annotated[tuple[Policy, ...], Field(min_length=1)]
    extraction_fields: Annotated[tuple[FieldTruth, ...], Field(min_length=1)]
    fixture_required_kinds: tuple[DocumentKind, ...]
    expected_missing_kinds: tuple[DocumentKind, ...]
    completeness_basis: Literal["presence_only_unapproved_exercise_checklist"] = (
        "presence_only_unapproved_exercise_checklist"
    )
    policy_selection: PolicySelectionTruth
    review: ReviewTruth
    coverage_hypothesis: Text
    hypothesis_status: Literal["requires_fictional_policy_approval"] = (
        "requires_fictional_policy_approval"
    )

    @model_validator(mode="after")
    def references(self) -> Self:
        case = self.input_case
        if (
            case.state != CaseState.RECEIVED
            or case.revision != 1
            or case.policy is not None
            or case.evidence
            or case.assessment is not None
            or case.decision is not None
        ):
            raise ValueError(
                "corpus stores intake and separate annotations, not processed outcomes"
            )
        docs = {doc.document_id: doc for doc in case.documents}
        if any(doc.scan_status != ScanStatus.QUARANTINED for doc in case.documents):
            raise ValueError("generated documents have not passed a real scanner")
        available = {doc.kind for doc in case.documents}
        missing = set(self.fixture_required_kinds) - available
        if missing != set(self.expected_missing_kinds):
            raise ValueError("completeness annotation disagrees with supplied documents")
        evidence_ids = [field.expected.evidence_id for field in self.extraction_fields]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("extraction labels must have unique evidence IDs")
        for field in self.extraction_fields:
            value = field.expected
            doc = docs.get(value.document_id)
            if (
                doc is None
                or value.claim_id != case.claim.claim_id
                or value.artifact_sha256 != doc.sha256
                or value.page != 1
                or value.extraction_method != "generator-ground-truth"
                or value.confidence is not None
            ):
                raise ValueError("ground-truth field must have matching authored provenance")
        versions = [policy.version for policy in self.policies]
        if len(versions) != len(set(versions)):
            raise ValueError("policy versions must be unique within a sample")
        for policy in self.policies:
            if policy.policy_id != case.claim.policy_id:
                raise ValueError("policy register must match claim policy ID")
            if (
                policy.rule_pack_version != "unapproved-no-rules"
                or policy.index_version != "fixture-not-indexed"
            ):
                raise ValueError(
                    "dataset policies must not claim approved rules or an active index"
                )
            if (
                docs.get(policy.schedule.document_id) is None
                or docs.get(policy.wording.document_id) is None
            ):
                raise ValueError("policy schedule/wording references must exist")
            if (
                docs[policy.schedule.document_id].kind != DocumentKind.POLICY_SCHEDULE
                or docs[policy.wording.document_id].kind != DocumentKind.POLICY_WORDING
            ):
                raise ValueError("policy artifacts must have the correct document kinds")
            for artifact in policy.artifacts:
                doc = docs.get(artifact.document_id)
                if doc is None or doc.sha256 != artifact.sha256:
                    raise ValueError("policy artifact is absent or has a mismatched hash")
        selection = self.policy_selection
        if selection.submitted_version not in versions:
            raise ValueError("submitted policy version is not in the fixture register")
        matches = [
            p.version
            for p in self.policies
            if p.effective_from <= case.claim.loss_at.date() < p.effective_to
        ]
        if selection.basis == "fixture_interval" and matches != [selection.expected_version]:
            raise ValueError("selected fixture version disagrees with date metadata")
        if selection.basis == "outside_fixture_intervals" and (
            matches or selection.expected_version
        ):
            raise ValueError("outside-interval label conflicts with date metadata")
        if selection.basis == "conflicting_source_dates" and selection.expected_version is not None:
            raise ValueError("conflicting dates must not be assigned a single expected version")
        return self


class GroundTruth(Contract):
    dataset_version: Literal["motor-v1"] = "motor-v1"
    generator_version: Literal["1.0"] = "1.0"
    seed: Seed
    provenance: Literal["generated_from_code_no_real_people_or_external_inputs"] = (
        "generated_from_code_no_real_people_or_external_inputs"
    )
    split: Literal["development_not_held_out"] = "development_not_held_out"
    samples: tuple[SampleTruth, ...]

    @model_validator(mode="after")
    def inventory(self) -> Self:
        if len(self.samples) != len(Scenario) or {s.scenario for s in self.samples} != set(
            Scenario
        ):
            raise ValueError("corpus requires every distinct scenario exactly once")
        by_id = {sample.scenario_id: sample for sample in self.samples}
        if len(by_id) != len(self.samples) or len({s.submission_id for s in self.samples}) != len(
            by_id
        ):
            raise ValueError("scenario and submission identifiers must be unique")
        cases: set[str] = set()
        document_owners: dict[str, tuple[str, str]] = {}
        evidence_owners: dict[str, tuple[str, str]] = {}
        for sample in self.samples:
            for doc in sample.input_case.documents:
                owner = (doc.claim_id, doc.sha256)
                if document_owners.setdefault(doc.document_id, owner) != owner:
                    raise ValueError("document identity reused for different case/content")
            for field in sample.extraction_fields:
                evidence = field.expected
                owner = (evidence.claim_id, evidence.document_id)
                if evidence_owners.setdefault(evidence.evidence_id, owner) != owner:
                    raise ValueError("evidence identity reused across source documents")
            if sample.duplicate_of:
                original = by_id.get(sample.duplicate_of)
                if (
                    sample.scenario != Scenario.DUPLICATE
                    or original is None
                    or original.duplicate_of
                    or sample.input_case != original.input_case
                    or sample.extraction_fields != original.extraction_fields
                    or sample.policies != original.policies
                ):
                    raise ValueError("duplicate must reference the identical original case payload")
            else:
                if (
                    sample.scenario == Scenario.DUPLICATE
                    or sample.input_case.claim.claim_id in cases
                ):
                    raise ValueError(
                        "repeated claim identity requires explicit duplicate annotation"
                    )
                cases.add(sample.input_case.claim.claim_id)
        return self


class FileRecord(Contract):
    path: Text
    sha256: Sha256
    byte_size: PositiveInt

    @model_validator(mode="after")
    def relative_path(self) -> Self:
        if (
            self.path.startswith("/")
            or "\\" in self.path
            or any(part in {"", ".", ".."} for part in self.path.split("/"))
        ):
            raise ValueError("manifest paths must be safe relative paths")
        return self


class CorpusManifest(Contract):
    dataset_version: Literal["motor-v1"] = "motor-v1"
    seed: Seed
    generator_sha256: Sha256
    files: tuple[FileRecord, ...]

    @model_validator(mode="after")
    def unique_paths(self) -> Self:
        paths = [record.path for record in self.files]
        if len(paths) != len(set(paths)) or "manifest.json" in paths:
            raise ValueError("manifest must list unique payload paths without self-reference")
        return self
