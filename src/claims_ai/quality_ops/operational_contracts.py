"""Stage B development conformance is explicitly separate from held-out quality."""

from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from claims_ai.models import Contract
from claims_ai.quality_ops.contracts import Cohort

DevId = Annotated[str, StringConstraints(strict=True, pattern=r"^DEV-[0-9]{3}$")]
FieldName = Literal["policy_id", "loss_date", "vehicle_reference", "estimate_pence", "currency"]
FIELDS: tuple[FieldName, ...] = (
    "policy_id",
    "loss_date",
    "vehicle_reference",
    "estimate_pence",
    "currency",
)


class DevelopmentInput(Contract):
    format: Literal["m22-development-input-v1"] = "m22-development-input-v1"
    case_id: DevId
    text: Annotated[str, StringConstraints(strict=True, min_length=1, max_length=2048)]


class DevelopmentPrediction(Contract):
    case_id: DevId
    fields: dict[FieldName, str | None]

    @model_validator(mode="after")
    def exact_fields(self) -> Self:
        if set(self.fields) != set(FIELDS) or any(
            v is not None and len(v) > 128 for v in self.fields.values()
        ):
            raise ValueError("invalid development prediction")
        return self


class DevelopmentReference(Contract):
    case_id: DevId
    cohort: Cohort
    label_status: Literal["SIMULATED_DEVELOPMENT_NOT_INDEPENDENT"] = (
        "SIMULATED_DEVELOPMENT_NOT_INDEPENDENT"
    )
    fields: dict[FieldName, str | None]


class CaseResult(Contract):
    case_id: str
    cohort: Cohort
    classification: Literal["PENDING_REVIEW", "SIMULATED_DEVELOPMENT"]
    verdict: Literal["PASS", "FAIL", "NOT_TESTED"]
    correct_fields: Annotated[int, Field(strict=True, ge=0, le=5)] | None
    eligible_fields: Annotated[int, Field(strict=True, ge=0, le=5)]
    missing_predictions: Annotated[int, Field(strict=True, ge=0, le=5)]
    failures: tuple[str, ...]
    reason: str | None

    @model_validator(mode="after")
    def no_unreviewed_credit(self) -> Self:
        if self.classification == "PENDING_REVIEW" and (
            self.verdict != "NOT_TESTED" or self.correct_fields is not None
        ):
            raise ValueError("unapproved independent quality cannot be scored")
        if (self.verdict == "NOT_TESTED") != (self.reason is not None):
            raise ValueError("missing unavailable reason")
        if self.correct_fields is not None and self.correct_fields > self.eligible_fields:
            raise ValueError("invalid denominator")
        return self
