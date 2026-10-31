"""Pinned fictional parameters; no insurer approval, arbitrary expressions or prompt rules."""

from hashlib import sha256
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.evidence.normalization import normalize
from claims_ai.rules.contracts import RuleSpecification, SpecificationManifest, Terms


def digest(value: object) -> str:
    return sha256(json_bytes(value)).hexdigest()


def pence(value: str) -> int:
    canonical = normalize("estimate_amount", value)
    whole, fraction = canonical.split(".")
    return int(whole) * 100 + int(fraction)


def money(value: int) -> str:
    return f"{value // 100}.{value % 100:02d}"


def clause_texts(terms: Terms) -> dict[str, str]:
    return {
        "C01": "Provisional scope: private motor damage; reviewed category must be motor_damage.",
        "C02": "Provisional checklist: validated claim form, repair estimate and damage image.",
        "X01": "Provisional exclusion: reviewed cause gradual_wear_only, with no impact.",
        "C03": f"Provisional excess GBP {money(terms.excess_pence)}: subtract once, floor at zero.",
        "C04": (
            f"Provisional net cap GBP {money(terms.limit_pence)} "
            "applies after excess; illustration only."
        ),
        "R01": "Human approval always; adverse, ambiguous or high-risk findings need supervisor.",
        "V01": (
            f"Provisional version {terms.policy_version}; status unapproved; no binding outcome."
        ),
    }


def load_specification(root: Path) -> RuleSpecification:
    path = root / "specification.json"
    if path.stat().st_size > 131072:
        raise ValueError("rule specification exceeds offline input budget")
    manifest = SpecificationManifest.model_validate_json((root / "manifest.json").read_bytes())
    content = path.read_bytes()
    if sha256(content).hexdigest() != manifest.specification_sha256:
        raise ValueError("rule specification fingerprint mismatch")
    spec = RuleSpecification.model_validate_json(content)
    if json_bytes(spec.model_dump(mode="json")) != content:
        raise ValueError("rule specification must use canonical versioned serialization")
    return spec
