"""Explicit syntactic normalization, not M5 scoring or coverage/financial rules."""

import re
import unicodedata
from datetime import UTC, date, datetime

from pydantic import TypeAdapter

from claims_ai.models import ClaimId, DocumentId, PolicyId, Text, Version

# Required extraction fields, not contractual evidence/coverage requirements.
FIELDS: dict[str, tuple[str, ...]] = {
    "claim_form": (
        "policy_id",
        "loss_at",
        "vehicle_reference",
        "claimed_amount",
        "currency",
        "narrative",
    ),
    "repair_estimate": (
        "vehicle_reference",
        "loss_at",
        "estimate_amount",
        "currency",
        "estimate_issued_at",
        "repairer_reference",
    ),
    "policy_schedule": (
        "policy_id",
        "policy_version",
        "effective_from",
        "effective_to",
        "vehicle_reference",
    ),
    "policy_wording": ("policy_version", "product", "jurisdiction"),
    "damage_photo": ("damage_location",),
}
OPTIONAL = {
    "claim_form": ("submitted_policy_version", "claimant_reference", "claim_id", "document_id")
}
SHARED = {"policy_id", "vehicle_reference", "loss_at", "claimed_amount", "currency", "narrative"}
IDENTIFIERS: dict[str, TypeAdapter[str]] = {
    "claim_id": TypeAdapter(ClaimId),
    "policy_id": TypeAdapter(PolicyId),
    "document_id": TypeAdapter(DocumentId),
}


def normalize(name: str, value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    if any(ord(char) < 32 and char not in "\t\n\r" for char in value):
        raise ValueError("unsupported control character")
    # Unicode compatibility expansion must still fit the existing domain text contract.
    value = TypeAdapter(Text).validate_python(" ".join(value.split()))
    if name in {"claim_id", "policy_id", "document_id"}:
        return IDENTIFIERS[name].validate_python(value)
    if name in {"claimed_amount", "estimate_amount"}:
        if not re.fullmatch(r"\+?(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)(?:\.[0-9]+)?", value):
            raise ValueError("money requires a nonnegative decimal string")
        whole, _, fraction = value.lstrip("+").replace(",", "").partition(".")
        if len(whole) > 12 or len(fraction.rstrip("0")) > 2:
            raise ValueError("money exceeds representation precision/size")
        return (whole.lstrip("0") or "0") + "." + fraction[:2].ljust(2, "0")
    if name in {"loss_at", "estimate_issued_at"}:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError("timestamp requires timezone")
        return timestamp.astimezone(UTC).isoformat().replace("+00:00", "Z")
    if name in {"effective_from", "effective_to"}:
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
            raise ValueError("date requires ISO calendar form")
        return date.fromisoformat(value).isoformat()
    if name == "currency" and value != "GBP":
        raise ValueError("initial claim currency is GBP")
    if name == "product" and value != "motor_damage":
        raise ValueError("initial product is motor_damage")
    if name == "jurisdiction" and value != "GB":
        raise ValueError("initial jurisdiction is GB")
    if name == "damage_location":
        value = value.lower().replace(" ", "_")
    if name in {
        "vehicle_reference",
        "repairer_reference",
        "claimant_reference",
        "policy_version",
        "submitted_policy_version",
        "damage_location",
    }:
        return TypeAdapter(Version).validate_python(value)
    return value
