"""Compose existing case/evidence/policy types without promoting findings to outcomes."""

from datetime import date
from enum import StrEnum
from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import AwareDatetime, Field, model_validator

from claims_ai.benchmark.contracts import ExtractionResponse
from claims_ai.evidence.contracts import ProcessingRequest
from claims_ai.knowledge.contracts import KnowledgeIndex
from claims_ai.models import (
    Case,
    ClaimId,
    Contract,
    EvidenceId,
    PolicyArtifact,
    PolicyCitation,
    PolicyId,
    ReviewerRole,
    RiskFlag,
    Sha256,
    Text,
    Version,
)

Pence = Annotated[int, Field(strict=True, ge=0, le=99_999_999_999_999)]


class FindingStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INDETERMINATE = "INDETERMINATE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleId(StrEnum):
    BINDING = "PR01"
    EVIDENCE = "PR02"
    CATEGORY = "PR03"
    EXCLUSION = "PR04"
    ILLUSTRATION = "PR05"
    REVIEW = "PR06"


class Terms(Contract):
    policy_version: Version
    effective_from: date
    effective_to: date
    excess_pence: Pence
    limit_pence: Annotated[int, Field(strict=True, gt=0, le=99_999_999_999_999)]
    high_value_pence: Annotated[int, Field(strict=True, gt=0, le=99_999_999_999_999)]

    @model_validator(mode="after")
    def valid_interval(self) -> Self:
        if self.effective_from >= self.effective_to:
            raise ValueError("terms need an increasing effective interval")
        return self


class RuleDefinition(Contract):
    rule_id: RuleId
    clauses: Annotated[tuple[Version, ...], Field(min_length=1)]
    definition: Text


class RuleSpecification(Contract):
    specification_id: Literal["northstar-motor-provisional"] = "northstar-motor-provisional"
    version: Literal["0.1.0"] = "0.1.0"
    engine_version: Literal["motor-rules-v1"] = "motor-rules-v1"
    status: Literal["provisional_unapproved"] = "provisional_unapproved"
    operational_use_allowed: Literal[False] = False
    currency: Literal["GBP"] = "GBP"
    supported_category: Literal["motor_damage"] = "motor_damage"
    exclusion: Literal["reviewed_gradual_wear_only"] = "reviewed_gradual_wear_only"
    amount_basis: Literal["matching_claim_and_repair_estimate"] = (
        "matching_claim_and_repair_estimate"
    )
    formula: Literal["min(max(estimate_pence - excess_pence, 0), limit_pence)"] = (
        "min(max(estimate_pence - excess_pence, 0), limit_pence)"
    )
    required_kinds: tuple[Literal["claim_form", "repair_estimate", "damage_photo"], ...]
    terms: Annotated[tuple[Terms, ...], Field(min_length=1, max_length=8)]
    rules: tuple[RuleDefinition, ...]

    @model_validator(mode="after")
    def complete_specification(self) -> Self:
        if (
            set(self.required_kinds) != {"claim_form", "repair_estimate", "damage_photo"}
            or len(self.required_kinds) != 3
        ):
            raise ValueError("this engine requires the explicit three-document checklist")
        expected = {
            RuleId.BINDING: ("V01",),
            RuleId.EVIDENCE: ("C02",),
            RuleId.CATEGORY: ("C01",),
            RuleId.EXCLUSION: ("X01",),
            RuleId.ILLUSTRATION: ("C03", "C04"),
            RuleId.REVIEW: ("R01",),
        }
        if len(self.rules) != 6 or {r.rule_id: r.clauses for r in self.rules} != expected:
            raise ValueError("all six supported rule IDs and exact clause mappings are required")
        for position, first in enumerate(self.terms):
            for second in self.terms[position + 1 :]:
                if first.policy_version == second.policy_version or max(
                    first.effective_from, second.effective_from
                ) < min(first.effective_to, second.effective_to):
                    raise ValueError(
                        "rule terms must have unique versions and nonoverlapping dates"
                    )
        return self


class SpecificationManifest(Contract):
    version: Literal["0.1.0"] = "0.1.0"
    specification_sha256: Sha256
    scenarios_sha256: Sha256


class FixtureScenario(Contract):
    fixture_id: Version
    policy_version: Version
    incident_at: AwareDatetime
    amount: Text
    category: Literal["motor_damage", "other", "unknown"] = "motor_damage"
    cause: Literal["impact", "gradual_wear_only", "unknown"] = "impact"
    fault: Literal[
        "none",
        "missing_estimate",
        "contradictory_estimate",
        "quarantined",
        "unverified",
        "no_facts",
        "ambiguous",
        "amount_conflict",
        "simulation_disabled",
    ] = "none"


class FixtureSuite(Contract):
    version: Literal["motor-rules-fixtures-v1"] = "motor-rules-fixtures-v1"
    provenance: Literal["new_authored_synthetic_fixtures_not_m4"] = (
        "new_authored_synthetic_fixtures_not_m4"
    )
    scenarios: Annotated[tuple[FixtureScenario, ...], Field(min_length=1, max_length=64)]

    @model_validator(mode="after")
    def unique_ids(self) -> Self:
        if len({s.fixture_id for s in self.scenarios}) != len(self.scenarios):
            raise ValueError("synthetic rule fixture IDs must be unique")
        return self


class EvidenceInput(Contract):
    request: ProcessingRequest
    response: ExtractionResponse


class ReviewedFacts(Contract):
    fact_id: Version
    category: Literal["motor_damage", "other", "unknown"]
    cause: Literal["impact", "gradual_wear_only", "unknown"]
    evidence_ids: Annotated[tuple[EvidenceId, ...], Field(min_length=1)]
    case_sha256: Sha256
    reviewer_id: UUID
    role: ReviewerRole
    basis: Literal["synthetic_human_assertion"] = "synthetic_human_assertion"


class EvaluationRequest(Contract):
    case: Case
    policy_id: PolicyId
    policy_version: Version | None
    index: KnowledgeIndex | None = None
    specification_sha256: Sha256
    evidence_inputs: Annotated[tuple[EvidenceInput, ...], Field(max_length=64)] = ()
    reviewed_facts: Annotated[tuple[ReviewedFacts, ...], Field(max_length=16)] = ()
    risk_flags: tuple[RiskFlag, ...] = ()
    allow_simulated_evidence: Annotated[bool, Field(strict=True)] = False


class EvidenceProvenance(Contract):
    evidence_id: EvidenceId
    record_sha256: Sha256
    artifact: PolicyArtifact
    page: int
    source_lines: tuple[int, ...]
    processing_key: Sha256


class Calculation(Contract):
    currency: Literal["GBP"] = "GBP"
    estimate_pence: Pence
    excess_pence: Pence
    after_excess_pence: Pence
    limit_pence: Pence
    illustration_pence: Pence
    limit_reduction_pence: Pence
    purpose: Literal["non_binding_illustration_only"] = "non_binding_illustration_only"

    @model_validator(mode="after")
    def exact_arithmetic(self) -> Self:
        remaining = max(self.estimate_pence - self.excess_pence, 0)
        illustration = min(remaining, self.limit_pence)
        if (self.after_excess_pence, self.illustration_pence, self.limit_reduction_pence) != (
            remaining,
            illustration,
            remaining - illustration,
        ):
            raise ValueError("calculation must match the specified integer-pence formula")
        return self


class RuleFinding(Contract):
    rule_id: RuleId
    rule_version: Literal["0.1.0"] = "0.1.0"
    status: FindingStatus
    specification_sha256: Sha256
    specification_pointer: str
    citations: tuple[PolicyCitation, ...]
    evidence_ids: tuple[EvidenceId, ...] = ()
    fact_ids: tuple[Version, ...] = ()
    issues: tuple[Version, ...] = ()
    explanation: Text
    calculation: Calculation | None = None

    @model_validator(mode="after")
    def calculation_authority(self) -> Self:
        if self.calculation is not None and (
            self.rule_id != RuleId.ILLUSTRATION or self.status != FindingStatus.PASS
        ):
            raise ValueError("only a passing illustration finding can contain arithmetic")
        return self


class RuleEvaluation(Contract):
    evaluation_mode: Literal["OFFLINE_PROVISIONAL"] = "OFFLINE_PROVISIONAL"
    specification_status: Literal["provisional_unapproved"] = "provisional_unapproved"
    execution_key: Sha256
    claim_id: ClaimId
    case_policy_id: PolicyId
    requested_policy_id: PolicyId
    requested_policy_version: Version | None
    case_sha256: Sha256
    specification_sha256: Sha256
    input_sha256: Sha256
    findings: tuple[RuleFinding, ...]
    evidence_provenance: tuple[EvidenceProvenance, ...]
    risk_flags: tuple[RiskFlag, ...]
    required_reviewer: ReviewerRole
    human_review_required: Literal[True] = True
    final_outcome: Literal[None] = None
    settlement_authorized: Literal[False] = False

    @model_validator(mode="after")
    def safe_review(self) -> Self:
        if len(self.findings) != 6 or {f.rule_id for f in self.findings} != set(RuleId):
            raise ValueError("one finding for each supported rule is required")
        if self.risk_flags or any(
            f.status in {FindingStatus.FAIL, FindingStatus.INDETERMINATE} for f in self.findings
        ):
            if self.required_reviewer != ReviewerRole.SUPERVISOR:
                raise ValueError(
                    "adverse, ambiguous and risk-flagged findings require a supervisor"
                )
        calculation = next(f for f in self.findings if f.rule_id == RuleId.ILLUSTRATION)
        if any(f.specification_sha256 != self.specification_sha256 for f in self.findings):
            raise ValueError("findings must pin the evaluation specification")
        if calculation.calculation is not None:
            if any(
                f.status != FindingStatus.PASS
                for f in self.findings
                if f.rule_id in {RuleId.BINDING, RuleId.EVIDENCE, RuleId.CATEGORY, RuleId.EXCLUSION}
            ):
                raise ValueError("illustrations require all prerequisite findings to pass")
            if set(self.risk_flags) & {
                RiskFlag.AMBIGUOUS,
                RiskFlag.CONFLICTING,
                RiskFlag.INJECTION_FLAGGED,
                RiskFlag.UNSUPPORTED,
            }:
                raise ValueError(
                    "uncertain/injection/unsupported findings cannot carry illustrations"
                )
        return self
