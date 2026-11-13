"""Deterministic offline coordinator; no independent review verifier is configured."""

import json
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

from claims_ai.quality_ops.candidate import verify_candidate
from claims_ai.quality_ops.contracts import Cohort, ReferenceLabels
from claims_ai.quality_ops.development_inputs import inputs
from claims_ai.quality_ops.development_labels import references
from claims_ai.quality_ops.operational_contracts import (
    FIELDS,
    CaseResult,
    DevelopmentInput,
    DevelopmentPrediction,
)
from claims_ai.quality_ops.prediction_access import bounded_bytes

CANDIDATE_PIN = "42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b"


class ScoringNotAuthorised(ValueError):
    pass


def require_independent_scoring(review_record: object = None) -> None:
    # A supplied APPROVED flag, signature string, hash or path is not a configured
    # independent identity/approval verifier. There is intentionally no bypass.
    del review_record
    raise ScoringNotAuthorised("independent_review_verifier_unconfigured")


def pending_cases(root: Path) -> tuple[CaseResult, ...]:
    verify_candidate(root, expected_manifest_sha256=CANDIDATE_PIN)
    # Trusted coordinator may inspect labels only for roster/cohort metadata. No
    # candidate predictor runs; no reference data crosses the prediction boundary.
    labels = ReferenceLabels.model_validate_json(
        bounded_bytes(root / "references/labels.json", 1048576)
    )
    return tuple(
        CaseResult(
            case_id=row.case_id,
            cohort=row.cohort,
            classification="PENDING_REVIEW",
            verdict="NOT_TESTED",
            correct_fields=None,
            eligible_fields=5,
            missing_predictions=0,
            failures=("pending_review",),
            reason="Independent labels and release gates are unapproved",
        )
        for row in labels.labels
    )


def predict_development(values: tuple[DevelopmentInput, ...]) -> tuple[DevelopmentPrediction, ...]:
    import claims_ai

    package = str(Path(claims_ai.__file__).resolve().parent.parent)
    payload = json.dumps({"inputs": [v.model_dump(mode="json") for v in values]})
    if not 1 <= len(values) <= 16 or len(payload) > 65536:
        raise ValueError("development input capacity")
    code = (
        "import sys;sys.path.insert(0,sys.argv[1]);"
        "from claims_ai.quality_ops.prediction_worker import main;main()"
    )
    with tempfile.TemporaryDirectory(prefix="m22-predict-") as directory:
        response = subprocess.run(
            [sys.executable, "-I", "-B", "-c", code, package],
            input=payload,
            text=True,
            capture_output=True,
            timeout=15,
            cwd=directory,
        )
    if response.returncode or len(response.stdout) > 65536:
        raise ValueError("development prediction unavailable; details omitted")
    raw = json.loads(response.stdout)
    if not isinstance(raw, list) or len(raw) > 16:
        raise ValueError("prediction protocol")
    parsed = tuple(DevelopmentPrediction.model_validate(v) for v in raw)
    if len({v.case_id for v in parsed}) != len(parsed) or not {v.case_id for v in parsed} <= {
        v.case_id for v in values
    }:
        raise ValueError("prediction identity mismatch")
    return parsed


def evaluate_development(
    predictions: tuple[DevelopmentPrediction, ...] | None = None, *, harness_error: bool = False
) -> tuple[CaseResult, ...]:
    if predictions is None and not harness_error:
        try:
            predictions = predict_development(inputs())
        except Exception:
            harness_error = True
    predicted = {p.case_id: p for p in predictions or ()}
    if len(predicted) != len(predictions or ()) or not set(predicted) <= {
        r.case_id for r in references()
    }:
        raise ValueError("development prediction roster mismatch")
    rows = []
    for reference in references():
        prediction = predicted.get(reference.case_id)
        correct = (
            sum(prediction.fields[f] == reference.fields[f] for f in FIELDS) if prediction else 0
        )
        rows.append(
            CaseResult(
                case_id=reference.case_id,
                cohort=reference.cohort,
                classification="SIMULATED_DEVELOPMENT",
                verdict="NOT_TESTED" if harness_error else "PASS" if correct == 5 else "FAIL",
                correct_fields=None if harness_error else correct,
                eligible_fields=5,
                missing_predictions=5 if prediction is None else 0,
                failures=("harness_error",)
                if harness_error
                else ()
                if correct == 5
                else ("missing_prediction" if prediction is None else "quality_mismatch",),
                reason="Development harness did not execute" if harness_error else None,
            )
        )
    return tuple(rows)


def summarize(rows: tuple[CaseResult, ...]) -> dict[str, object]:
    result: dict[str, object] = {}
    for cohort in Cohort:
        selected = [r for r in rows if r.cohort == cohort]
        scored = [r for r in selected if r.correct_fields is not None]
        denominator = sum(r.eligible_fields for r in scored)
        numerator = sum(r.correct_fields or 0 for r in scored)
        result[cohort.value] = {
            "cases": len(selected),
            "counts": dict(Counter(r.verdict for r in selected)),
            "numerator": numerator if scored else None,
            "denominator": denominator,
            "rate": numerator / denominator if denominator else None,
            "missing_predictions": sum(r.missing_predictions for r in selected),
            "unscored_cases": sum(r.verdict == "NOT_TESTED" for r in selected),
        }
    return result
