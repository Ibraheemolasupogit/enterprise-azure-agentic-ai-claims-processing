"""Exclusive candidate construction/integrity checks; no evaluation or approval command."""

import argparse
import json
from hashlib import sha256
from pathlib import Path

from claims_ai.quality_ops.cases import generate_inputs
from claims_ai.quality_ops.contracts import (
    COHORT_COUNTS,
    GatePlan,
    InputManifest,
    ReferenceLabels,
    ReviewTemplate,
    ReviewTemplates,
)
from claims_ai.quality_ops.prediction_access import bounded_bytes, load_prediction_inputs
from claims_ai.quality_ops.references import GUIDE, gate_plan, propose_labels
from claims_ai.rules.specification import digest

BASELINE = "9c3cc78a16764411005893371a80ac9f291b354e"
FILES = frozenset(
    {
        "inputs/cases.json",
        "inputs/manifest.json",
        "references/labels.json",
        "references/guide.md",
        "reviews/templates.json",
        "gates.json",
    }
)


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def authoring_hash() -> str:
    root = Path(__file__).parent
    return sha256(
        b"".join(p.name.encode() + b"\0" + p.read_bytes() for p in sorted(root.glob("*.py")))
    ).hexdigest()


def candidate_bytes() -> dict[str, bytes]:
    inputs = generate_inputs()
    labels = propose_labels(inputs)
    gates = json_bytes(gate_plan().model_dump(mode="json"))
    inputs_raw = json_bytes(inputs.model_dump(mode="json"))
    reviews = ReviewTemplates(
        reviews=tuple(
            ReviewTemplate(
                case_id=r.case_id,
                input_sha256=r.input_sha256,
                reference_sha256=digest(r.model_dump(mode="json")),
                gates_sha256=sha256(gates).hexdigest(),
            )
            for r in labels.labels
        )
    )
    files = {
        "inputs/cases.json": inputs_raw,
        "inputs/manifest.json": json_bytes(
            InputManifest(sha256=sha256(inputs_raw).hexdigest()).model_dump(mode="json")
        ),
        "references/labels.json": json_bytes(labels.model_dump(mode="json")),
        "references/guide.md": GUIDE.encode(),
        "reviews/templates.json": json_bytes(reviews.model_dump(mode="json")),
        "gates.json": gates,
    }
    inventory = json_bytes(
        {
            "format": "m22-file-inventory-v1",
            "files": {
                name: {"sha256": sha256(content).hexdigest(), "bytes": len(content)}
                for name, content in sorted(files.items())
            },
        }
    )
    files["inventory.json"] = inventory
    files["candidate-manifest.json"] = json_bytes(
        {
            "format": "m22-candidate-v1",
            "stage": "A",
            "baseline_revision": BASELINE,
            "case_count": 60,
            "cohorts": {c.value: n for c, n in COHORT_COUNTS.items()},
            "case_ids": [r.case_id for r in labels.labels],
            "authoring_sha256": authoring_hash(),
            "inventory_sha256": sha256(inventory).hexdigest(),
            "review_status": "PENDING_REVIEW",
            "reviewer_identity": None,
            "approval": None,
            "holdout_status": "CANDIDATE_NOT_SEALED_AUTHOR_VISIBLE",
            "gates_status": "FROZEN_PROPOSAL_PENDING_APPROVAL",
            "scored_evaluation_allowed": False,
            "prediction_manifest_sha256": sha256(files["inputs/manifest.json"]).hexdigest(),
            "gates_sha256": sha256(gates).hexdigest(),
            "native_text_only": True,
            "live_predictions": "NOT_TESTED",
        }
    )
    return files


def write_candidate(destination: Path, *, repository_root: Path) -> str:
    """Never overwrite a version or write into historical reference/output namespaces."""
    repo = repository_root.resolve(strict=True)
    output = destination.resolve()
    if (
        destination.is_symlink()
        or (
            output.is_relative_to(repo / "data")
            and not output.is_relative_to(repo / "data/evaluation/m22")
        )
        or output.is_relative_to(repo / "outputs")
    ):
        raise ValueError("historical evidence destination denied")
    files = candidate_bytes()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.mkdir(exist_ok=False)
    for name, content in sorted(files.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
        path.chmod(0o444)
    manifest_hash = sha256(files["candidate-manifest.json"]).hexdigest()
    verify_candidate(output, expected_manifest_sha256=manifest_hash)
    return manifest_hash


def verify_candidate(root: Path, *, expected_manifest_sha256: str) -> None:
    """Trusted author/reviewer verification, distinct from input-only prediction access."""
    raw = bounded_bytes(root / "candidate-manifest.json", 65536)
    if sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError("candidate manifest mismatch")
    manifest = json.loads(raw)
    if manifest["format"] != "m22-candidate-v1" or (
        manifest["review_status"] != "PENDING_REVIEW"
        or manifest["scored_evaluation_allowed"] is not False
    ):
        raise ValueError("candidate is not Stage A")
    inventory_raw = bounded_bytes(root / "inventory.json", 65536)
    if sha256(inventory_raw).hexdigest() != manifest["inventory_sha256"]:
        raise ValueError("candidate inventory mismatch")
    inventory = json.loads(inventory_raw)
    if inventory["format"] != "m22-file-inventory-v1" or set(inventory["files"]) != FILES:
        raise ValueError("candidate file inventory mismatch")
    if {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()} != (
        FILES | {"inventory.json", "candidate-manifest.json"}
    ):
        raise ValueError("unexpected candidate file")
    for name, binding in inventory["files"].items():
        content = bounded_bytes(root / name, 1048576)
        if len(content) != binding["bytes"] or sha256(content).hexdigest() != binding["sha256"]:
            raise ValueError("candidate file hash mismatch")
    inputs = load_prediction_inputs(
        root, expected_manifest_sha256=manifest["prediction_manifest_sha256"]
    )
    labels = ReferenceLabels.model_validate_json(
        bounded_bytes(root / "references/labels.json", 1048576)
    )
    reviews = ReviewTemplates.model_validate_json(
        bounded_bytes(root / "reviews/templates.json", 1048576)
    )
    gates_raw = bounded_bytes(root / "gates.json", 65536)
    GatePlan.model_validate_json(gates_raw)
    if sha256(gates_raw).hexdigest() != manifest["gates_sha256"]:
        raise ValueError("candidate gates mismatch")
    by_id = {c.case_id: c for c in inputs.cases}
    if (
        set(by_id) != {r.case_id for r in labels.labels}
        or set(by_id) != {r.case_id for r in reviews.reviews}
        or set(by_id) != set(manifest["case_ids"])
        or manifest["case_count"] != 60
        or manifest["cohorts"] != {c.value: n for c, n in COHORT_COUNTS.items()}
    ):
        raise ValueError("candidate case/review binding mismatch")
    for label, review in zip(labels.labels, reviews.reviews, strict=True):
        case = by_id[label.case_id]
        if (
            label.input_sha256 != digest(case.model_dump(mode="json"))
            or review.case_id != label.case_id
            or review.input_sha256 != label.input_sha256
            or review.reference_sha256 != digest(label.model_dump(mode="json"))
            or review.gates_sha256 != manifest["gates_sha256"]
        ):
            raise ValueError("candidate reference/review hash mismatch")
        assets = {a.asset_id: a for a in case.assets}
        for field in label.fields:
            if field.source_asset_id is not None and (
                field.source_asset_id not in assets
                or field.source_quote not in assets[field.source_asset_id].content.splitlines()
            ):
                raise ValueError("candidate reference source mismatch")


def main() -> None:
    parser = argparse.ArgumentParser(description="M22 Stage A candidate authoring; no evaluation")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repository-root", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = write_candidate(args.output, repository_root=args.repository_root)
    except Exception:
        parser.exit(3, "Candidate creation unavailable; existing evidence is never overwritten.\n")
    print(f"60 PENDING_REVIEW candidates; no scored evaluation. Manifest SHA-256: {result}")


if __name__ == "__main__":
    main()
