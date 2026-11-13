"""Versioned candidate, review and future measurement shapes; no quality scoring."""

from datetime import date
from enum import StrEnum
from hashlib import sha256
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from claims_ai.models import ClaimId, Contract, PolicyId, Sha256, Text

CaseId = Annotated[str, StringConstraints(strict=True, pattern=r"^M22-[A-F0-9]{12}$")]
Count = Annotated[int, Field(strict=True, ge=0, le=1000000)]
Fraction = Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)]


class Cohort(StrEnum):
    DAMAGE = "ordinary_damage"
    EXCLUSION = "exclusions_and_dates"
    EVIDENCE = "evidence_problems"
    POLICY = "policy_boundaries"
    SECURITY = "security"
    RECOVERY = "recovery"


COHORT_COUNTS: dict[Cohort, int] = dict(zip(Cohort, (15, 10, 10, 10, 10, 5), strict=True))


class Asset(Contract):
    """Actual native-text bytes are UTF-8(content); these are not OCR/image fixtures."""

    asset_id: Annotated[str, StringConstraints(pattern=r"^M22-[A-F0-9]{12}-[A-Z]+$")]
    media_type: Literal["text/plain"] = "text/plain"
    content: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=16000)]
    content_sha256: Sha256

    @model_validator(mode="after")
    def content_binding(self) -> Self:
        if sha256(self.content.encode("utf-8")).hexdigest() != self.content_sha256:
            raise ValueError("asset hash mismatch")
        return self


class PredictionCase(Contract):
    """Only runner-visible inputs. Cohorts, labels and reviewer fields are excluded."""

    format: Literal["m22-prediction-input-v1"] = "m22-prediction-input-v1"
    case_id: CaseId
    claim_id: ClaimId
    policy_id: PolicyId
    requested_policy_version: Literal["v1", "v2", "unknown"] | None
    loss_date: date
    requested_operation: Literal["prepare_advisory", "human_decide", "publish", "recover"]
    actor_profile: Literal["reviewer", "supervisor", "host"]
    fault: Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,63}$")]
    assets: Annotated[tuple[Asset, ...], Field(min_length=1, max_length=4)]

    @model_validator(mode="after")
    def unique_assets(self) -> Self:
        if len({a.asset_id for a in self.assets}) != len(self.assets) or any(
            not a.asset_id.startswith(self.case_id + "-") for a in self.assets
        ):
            raise ValueError("asset ownership mismatch")
        return self


class PredictionInputs(Contract):
    format: Literal["m22-prediction-inputs-v1"] = "m22-prediction-inputs-v1"
    cases: Annotated[tuple[PredictionCase, ...], Field(min_length=60, max_length=60)]

    @model_validator(mode="after")
    def distinct_inputs(self) -> Self:
        if (
            len({c.case_id for c in self.cases}) != 60
            or len({c.claim_id for c in self.cases}) != 60
        ):
            raise ValueError("candidate identities must be unique")
        return self


class InputManifest(Contract):
    format: Literal["m22-input-manifest-v1"] = "m22-input-manifest-v1"
    file: Literal["cases.json"] = "cases.json"
    sha256: Sha256
    case_count: Literal[60] = 60
    maximum_bytes: Literal[1048576] = 1048576


class PredictionRecord(Contract):
    """Future prediction shape only; predicted routes/findings never authorize a service action."""

    format: Literal["m22-prediction-record-v1"] = "m22-prediction-record-v1"
    case_id: CaseId
    input_sha256: Sha256
    execution: Literal["RUNTIME", "SIMULATED"]
    critical_fields: dict[
        Literal["policy_id", "loss_date", "vehicle_reference", "estimate_pence", "currency"],
        str | None,
    ]
    returned_clause_ids: Annotated[tuple[str, ...], Field(max_length=10)]
    proposed_findings: Annotated[tuple[str, ...], Field(max_length=16)]
    proposed_route: Literal["reviewer", "supervisor", "deny", "recover_without_authority"]

    @model_validator(mode="after")
    def explicit_unknowns_not_missing_fields(self) -> Self:
        if len(self.critical_fields) != 5:
            raise ValueError("missing critical prediction; do not substitute an unknown value")
        return self


class FieldExpectation(Contract):
    field: Literal["policy_id", "loss_date", "vehicle_reference", "estimate_pence", "currency"]
    proposed_value: str | None
    source_asset_id: str | None
    source_quote: Text | None

    @model_validator(mode="after")
    def source_or_absence(self) -> Self:
        if (self.proposed_value is None) != (self.source_quote is None) or (
            self.source_quote is None
        ) != (self.source_asset_id is None):
            raise ValueError("reference value requires a source or explicit absence")
        return self


class ReferenceLabel(Contract):
    format: Literal["m22-reference-proposal-v1"] = "m22-reference-proposal-v1"
    case_id: CaseId
    input_sha256: Sha256
    cohort: Cohort
    scenario: str
    tags: Annotated[tuple[str, ...], Field(min_length=1, max_length=8)]
    review_status: Literal["PENDING_REVIEW"] = "PENDING_REVIEW"
    disposition_hypothesis: Literal[
        "covered_candidate", "excluded_candidate", "undetermined", "not_applicable"
    ]
    proposed_route: Literal["reviewer", "supervisor", "deny", "recover_without_authority"]
    fields: Annotated[tuple[FieldExpectation, ...], Field(min_length=5, max_length=5)]
    relevant_clause_ids: tuple[str, ...]
    proposed_rule_findings: tuple[str, ...]
    illustrative_excess_pence: int | None
    illustrative_net_pence: int | None
    expected_control: Text
    rationale: Text
    prohibited_actions: tuple[str, ...]
    actual_insurance_authority: Literal[False] = False

    @model_validator(mode="after")
    def exact_fields(self) -> Self:
        if len({f.field for f in self.fields}) != 5:
            raise ValueError("duplicate reference fields")
        return self


class ReferenceLabels(Contract):
    format: Literal["m22-reference-labels-v1"] = "m22-reference-labels-v1"
    label_status: Literal["AUTHOR_PROPOSALS_NOT_INDEPENDENTLY_REVIEWED"] = (
        "AUTHOR_PROPOSALS_NOT_INDEPENDENTLY_REVIEWED"
    )
    labels: Annotated[tuple[ReferenceLabel, ...], Field(min_length=60, max_length=60)]

    @model_validator(mode="after")
    def exact_cohorts(self) -> Self:
        if len({r.case_id for r in self.labels}) != 60 or any(
            sum(r.cohort == cohort for r in self.labels) != count
            for cohort, count in COHORT_COUNTS.items()
        ):
            raise ValueError("invalid candidate cohort inventory")
        return self


class ReviewTemplate(Contract):
    """Not an approval DTO. Real review is a separate, externally attested future record."""

    case_id: CaseId
    input_sha256: Sha256
    reference_sha256: Sha256
    gates_sha256: Sha256
    status: Literal["PENDING_REVIEW"] = "PENDING_REVIEW"
    reviewer_identity: None = None
    reviewed_at: None = None
    independence_attestation: None = None
    approval: None = None
    signature: None = None
    source_checks: tuple[str, ...] = (
        "critical fields and source quotes",
        "policy intervals and clause relevance",
        "integer-pence illustrations and uncertainty",
        "routing, prohibited actions and fault expectations",
        "independence, prior exposure and leakage disclosure",
    )


class ReviewTemplates(Contract):
    format: Literal["m22-review-templates-v1"] = "m22-review-templates-v1"
    reviews: Annotated[tuple[ReviewTemplate, ...], Field(min_length=60, max_length=60)]


class MetricDefinition(Contract):
    metric_id: str
    numerator: Text
    denominator: Text
    aggregation: Literal["micro", "macro_query", "count", "coverage", "p95"]
    comparator: Literal["gte", "eq", "lt"]
    threshold: Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
    applicability: Literal["offline_control", "independent_quality", "live_or_human_study"]
    unavailable_classification: Literal["NOT_TESTED"] = "NOT_TESTED"


class GatePlan(Contract):
    format: Literal["m22-gates-v1"] = "m22-gates-v1"
    status: Literal["FROZEN_PROPOSAL_PENDING_APPROVAL"] = "FROZEN_PROPOSAL_PENDING_APPROVAL"
    scored_evaluation_allowed: Literal[False] = False
    metrics: Annotated[tuple[MetricDefinition, ...], Field(min_length=12, max_length=12)]
    zero_denominator: Literal["null_and_NOT_TESTED"] = "null_and_NOT_TESTED"
    missing_prediction: Literal["error_within_eligible_denominator"] = (
        "error_within_eligible_denominator"
    )
    unavailable_coverage: Literal["separate_count_no_full_scope_PASS"] = (
        "separate_count_no_full_scope_PASS"
    )
    harness_error: Literal["NOT_TESTED_and_incomplete_run"] = "NOT_TESTED_and_incomplete_run"
    safety_failure: Literal["FAIL_not_waived_by_aggregate"] = "FAIL_not_waived_by_aggregate"
    deterministic_repeats: Literal["two_source_one_wheel"] = "two_source_one_wheel"
    probabilistic_repeats: Literal[3] = 3
    canonical_exclusions: tuple[str, ...] = (
        "trace_id",
        "span_id",
        "wall_clock_timestamp",
        "measured_duration",
    )

    @model_validator(mode="after")
    def unique_metrics(self) -> Self:
        if len({m.metric_id for m in self.metrics}) != len(self.metrics):
            raise ValueError("duplicate metric definition")
        return self


class FailureClass(StrEnum):
    QUALITY = "quality_mismatch"
    SAFETY = "safety_violation"
    DEPENDENCY = "dependency_failure"
    MISSING = "missing_prediction"
    HARNESS = "harness_error"
    UNAVAILABLE = "unavailable_capability"
    PENDING = "pending_review"
    INAPPLICABLE = "not_applicable"


class Measurement(Contract):
    """Ratio/count evidence; macro recall retains a record per query, never pooled recall.

    Scalar timing/study observations remain a Stage B contract extension, not a rate.
    Stage A produces no Measurements and this DTO does not authenticate review claims.
    """

    format: Literal["m22-measurement-v1"] = "m22-measurement-v1"
    metric_id: str
    cohort: Cohort
    case_id: CaseId | None = None
    execution: Literal["RUNTIME", "SIMULATED", "NOT_EXECUTED"]
    capability_available: Annotated[bool, Field(strict=True)] = False
    review_status: Literal["PENDING_REVIEW", "APPROVED", "REJECTED"]
    verdict: Literal["PASS", "FAIL", "NOT_TESTED"]
    numerator: Count
    denominator: Count
    missing_predictions: Count = 0
    rate: Fraction | None
    failures: tuple[FailureClass, ...] = ()
    unavailable_reason: Text | None = None

    @model_validator(mode="after")
    def consistent_measurement(self) -> Self:
        if self.numerator > self.denominator or self.missing_predictions > self.denominator:
            raise ValueError("invalid measurement denominator")
        if self.rate != (self.numerator / self.denominator if self.denominator else None):
            raise ValueError("invalid measurement rate")
        blocked = (
            self.review_status != "APPROVED"
            or not self.capability_available
            or not self.denominator
            or self.execution == "NOT_EXECUTED"
            or FailureClass.HARNESS in self.failures
            or FailureClass.UNAVAILABLE in self.failures
            or FailureClass.INAPPLICABLE in self.failures
        )
        observed_safety_failure = (
            FailureClass.SAFETY in self.failures
            and self.execution != "NOT_EXECUTED"
            and self.capability_available
        )
        if observed_safety_failure and self.verdict != "FAIL":
            raise ValueError("observed safety failures cannot be waived by pending review")
        if blocked and not observed_safety_failure and self.verdict != "NOT_TESTED":
            raise ValueError("unavailable or unreviewed measurement cannot be scored")
        if (self.verdict == "NOT_TESTED") != (self.unavailable_reason is not None):
            raise ValueError("NOT_TESTED needs an explicit reason")
        if self.verdict == "PASS" and self.failures:
            raise ValueError("failed observation cannot pass")
        if self.verdict == "FAIL" and not self.failures:
            raise ValueError("failed measurement needs a failure classification")
        return self


class QueryRecallCounts(Contract):
    case_id: CaseId
    relevant: Annotated[int, Field(strict=True, ge=1, le=1000)]
    valid_unique_relevant_at_5: Annotated[int, Field(strict=True, ge=0, le=5)]

    @model_validator(mode="after")
    def valid_credit(self) -> Self:
        if self.valid_unique_relevant_at_5 > self.relevant:
            raise ValueError("recall credit exceeds relevance inventory")
        return self


class MacroRecallEvidence(Contract):
    """Arithmetic contract, not a scorer: excludes empty gold; retains each query denominator."""

    format: Literal["m22-macro-recall-v1"] = "m22-macro-recall-v1"
    queries: Annotated[tuple[QueryRecallCounts, ...], Field(max_length=60)]
    macro_recall_at_5: Fraction | None
    excluded_empty_relevance_queries: Count

    @model_validator(mode="after")
    def macro_not_pooled(self) -> Self:
        expected = (
            sum(q.valid_unique_relevant_at_5 / q.relevant for q in self.queries) / len(self.queries)
            if self.queries
            else None
        )
        if (
            len({q.case_id for q in self.queries}) != len(self.queries)
            or self.macro_recall_at_5 != expected
        ):
            raise ValueError("recall must be the mean of distinct answerable query recalls")
        return self


class ScalarMeasurement(Contract):
    """Future timing/paired-human-study shape; negative effort reduction is retained."""

    format: Literal["m22-scalar-measurement-v1"] = "m22-scalar-measurement-v1"
    metric_id: Literal["packet_p95_seconds", "handling_effort_reduction"]
    value: Annotated[float, Field(strict=True, allow_inf_nan=False)] | None
    sample_count: Count
    capability_available: Annotated[bool, Field(strict=True)] = False
    review_status: Literal["PENDING_REVIEW", "APPROVED", "REJECTED"]
    verdict: Literal["PASS", "FAIL", "NOT_TESTED"]
    unavailable_reason: Text | None

    @model_validator(mode="after")
    def available_observation(self) -> Self:
        unavailable = (
            not self.capability_available
            or not self.sample_count
            or self.review_status != "APPROVED"
        )
        if unavailable and (self.value is not None or self.verdict != "NOT_TESTED"):
            raise ValueError("unavailable study cannot supply a measured value")
        if (self.verdict == "NOT_TESTED") != (self.unavailable_reason is not None):
            raise ValueError("unavailable scalar needs an explicit reason")
        if self.verdict != "NOT_TESTED" and self.value is None:
            raise ValueError("scored scalar needs a measured value")
        if self.metric_id == "packet_p95_seconds" and self.value is not None and self.value < 0:
            raise ValueError("negative duration")
        return self


class EvaluationRunManifest(Contract):
    """Metadata contract only: no runner, prediction or approved release is supplied."""

    format: Literal["m22-run-manifest-v1"] = "m22-run-manifest-v1"
    source_revision: str
    source_tree_sha256: Sha256
    candidate_manifest_sha256: Sha256
    gates_sha256: Sha256
    review_record_sha256: Sha256
    dependency_inventory_sha256: Sha256
    evaluated_schema_version: str
    policy_version: str
    rule_version: str
    index_version: str
    prompt_sha256: Sha256 | None
    tools_sha256: Sha256
    model_version: str | None
    inference_parameters: dict[str, str | int | float | bool | None]
    evaluator_version: Literal["m22-evaluator-v1-proposed"] = "m22-evaluator-v1-proposed"
    environment: dict[str, str]
    execution: Literal["OFFLINE_RUNTIME", "SIMULATED", "LIVE_NOT_AUTHORISED"]
    repetition: Annotated[int, Field(strict=True, ge=1, le=3)]
