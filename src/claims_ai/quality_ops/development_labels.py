"""Explicit hand-authored SIMULATED development references; never imported by predictor."""

from claims_ai.quality_ops.contracts import Cohort
from claims_ai.quality_ops.operational_contracts import DevelopmentReference


def references() -> tuple[DevelopmentReference, ...]:
    return tuple(
        DevelopmentReference(
            case_id=f"DEV-{i:03}",
            cohort=cohort,
            fields={
                "policy_id": f"NS-POL-DD00000{i}",
                "loss_date": f"2031-02-0{i}",
                "vehicle_reference": f"SYNTH-DEV-{i}",
                "estimate_pence": str(i * 1000),
                "currency": None if i == 3 else "GBP",
            },
        )
        for i, cohort in enumerate(Cohort, 1)
    )
