"""Authored attack intent, independently observed facts and explicit evidence limits."""

from enum import StrEnum
from typing import Annotated, Literal, Self

from pydantic import Field, StringConstraints, model_validator

from claims_ai.models import Contract, Sha256, Text
from claims_ai.rules.specification import digest

Identifier = Annotated[str, StringConstraints(strict=True, pattern=r"^[A-Z][A-Z0-9-]{3,47}$")]
FactName = Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,47}$")]
Scalar = str | bool | int | None


class Target(StrEnum):
    CONTENT = "content"
    AGENT = "agent"
    TOOLS = "tools"
    MCP = "mcp"
    APPLICATION = "application"
    IDENTITY = "identity"
    REVIEW = "review"
    PRODUCTION = "production"


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_TESTED = "NOT_TESTED"


class Criterion(Contract):
    fact: FactName
    expected: Scalar


class AttackCase(Contract):
    case_id: Identifier
    target: Target
    attack: Annotated[str, StringConstraints(strict=True, pattern=r"^[a-z][a-z0-9_]{0,47}$")]
    payload: Text
    entry_point: Text
    trust_boundary: Text
    expected_behavior: Text
    control: Text
    residual_risk: Text
    owasp_2025: Annotated[tuple[str, ...], Field(max_length=4)]
    atlas_5_6: Annotated[tuple[str, ...], Field(max_length=3)] = ()
    criteria: Annotated[tuple[Criterion, ...], Field(min_length=1, max_length=8)]

    @model_validator(mode="after")
    def unique_criteria(self) -> Self:
        if len({c.fact for c in self.criteria}) != len(self.criteria):
            raise ValueError("criteria must address distinct observed facts")
        return self


class Catalog(Contract):
    catalog_version: Literal["claims-adversarial-v1"] = "claims-adversarial-v1"
    label_status: Literal["authored_security_expectations_not_independently_adjudicated"] = (
        "authored_security_expectations_not_independently_adjudicated"
    )
    cases: Annotated[tuple[AttackCase, ...], Field(min_length=1, max_length=96)]

    @model_validator(mode="after")
    def unique_cases(self) -> Self:
        if len({c.case_id for c in self.cases}) != len(self.cases):
            raise ValueError("attack IDs must be unique")
        return self


class CatalogManifest(Contract):
    catalog_version: Literal["claims-adversarial-v1"] = "claims-adversarial-v1"
    scenarios_sha256: Sha256


class Observation(Contract):
    execution: Literal[
        "RUNTIME", "SIMULATED_MODEL_RUNTIME_GUARDS", "HOST_INJECTED_RUNTIME_GUARDS", "NOT_EXECUTED"
    ]
    facts: Annotated[dict[FactName, Scalar], Field(max_length=24)]
    evidence_note: Text
    unavailable_reason: Text | None = None
    harness_error: bool = False

    @model_validator(mode="after")
    def explicit_execution(self) -> Self:
        if (self.execution == "NOT_EXECUTED") != (self.unavailable_reason is not None):
            raise ValueError("missing execution must be explicit and explained")
        if self.harness_error and self.unavailable_reason is None:
            raise ValueError("a harness failure cannot be runtime protection evidence")
        return self


def misses(case: AttackCase, observed: Observation) -> tuple[str, ...]:
    return tuple(
        criterion.fact
        for criterion in case.criteria
        if criterion.fact not in observed.facts
        or type(observed.facts[criterion.fact]) is not type(criterion.expected)
        or observed.facts[criterion.fact] != criterion.expected
    )


class CaseResult(Contract):
    case: AttackCase
    verdict: Verdict
    observed: Observation
    unmet_criteria: tuple[FactName, ...]
    attempt_sha256: Sha256
    evidence_sha256: Sha256

    @model_validator(mode="after")
    def evidence_binding(self) -> Self:
        if self.attempt_sha256 != digest(self.case.model_dump(mode="json")):
            raise ValueError("attack evidence does not bind the authored attempt")
        expected = digest(self.model_dump(mode="json", exclude={"evidence_sha256"}))
        if self.evidence_sha256 != expected:
            raise ValueError("attack evidence fingerprint mismatch")
        if (self.verdict == Verdict.NOT_TESTED) != (self.observed.unavailable_reason is not None):
            raise ValueError("untested cases must explain absent evidence")
        if self.verdict == Verdict.PASS and (self.unmet_criteria or self.observed.harness_error):
            raise ValueError("an incomplete or failed observation cannot pass")
        actual_misses = (
            () if self.observed.unavailable_reason is not None else misses(self.case, self.observed)
        )
        actual_verdict = (
            Verdict.NOT_TESTED
            if self.observed.unavailable_reason is not None
            else Verdict.FAIL
            if actual_misses
            else Verdict.PASS
        )
        if self.verdict != actual_verdict or self.unmet_criteria != actual_misses:
            raise ValueError("evidence classification must match actual criteria")
        return self


def score(case: AttackCase, observed: Observation) -> CaseResult:
    unmet: tuple[str, ...]
    if observed.unavailable_reason is not None:
        verdict, unmet = Verdict.NOT_TESTED, ()
    else:
        unmet = misses(case, observed)
        verdict = Verdict.FAIL if unmet else Verdict.PASS
    values = {
        "schema_version": "1.0",
        "synthetic": True,
        "case": case.model_dump(mode="json"),
        "verdict": verdict.value,
        "observed": observed.model_dump(mode="json"),
        "unmet_criteria": unmet,
        "attempt_sha256": digest(case.model_dump(mode="json")),
    }
    return CaseResult.model_validate({**values, "evidence_sha256": digest(values)})
