"""Offline validation of fixture bytes/annotations. Never follows document instructions."""

import json
from datetime import datetime
from hashlib import sha256
from pathlib import Path

from claims_ai.dataset.generator import WARNING, build_corpus
from claims_ai.dataset.render import render_document
from claims_ai.dataset.schema import CorpusManifest, GroundTruth, SourceDocument
from claims_ai.models import DocumentKind


def validate_corpus(root: Path) -> GroundTruth:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("corpus root must be a real directory")
    entries = list(root.rglob("*"))
    if any(path.is_symlink() for path in entries):
        raise ValueError("corpus cannot contain symlinks")
    manifest = CorpusManifest.model_validate_json((root / "manifest.json").read_bytes())
    expected_paths = {record.path for record in manifest.files}
    actual_paths = {path.relative_to(root).as_posix() for path in entries if path.is_file()}
    if actual_paths != expected_paths | {"manifest.json"}:
        raise ValueError("corpus contains missing or unlisted files")
    for record in manifest.files:
        payload = (root / record.path).read_bytes()
        if len(payload) != record.byte_size or sha256(payload).hexdigest() != record.sha256:
            raise ValueError("manifest byte size or SHA-256 mismatch")
    truth = GroundTruth.model_validate_json((root / "ground_truth.json").read_bytes())
    if manifest.seed != truth.seed:
        raise ValueError("manifest and annotations must have the same seed")
    if (
        json.loads((root / "ground-truth.schema.json").read_bytes())
        != GroundTruth.model_json_schema()
    ):
        raise ValueError("ground-truth schema disagrees with the current contract")
    document_paths = {
        doc.artifact_ref for sample in truth.samples for doc in sample.input_case.documents
    }
    payload_paths = document_paths | {path + ".source.json" for path in document_paths}
    if expected_paths != payload_paths | {"ground_truth.json", "ground-truth.schema.json"}:
        raise ValueError("manifest inventory must match declared document provenance")
    for sample in truth.samples:
        sources: dict[str, SourceDocument] = {}
        for doc in sample.input_case.documents:
            payload = (root / doc.artifact_ref).read_bytes()
            if sha256(payload).hexdigest() != doc.sha256 or len(payload) != doc.byte_size:
                raise ValueError("document metadata does not match artifact bytes")
            source = SourceDocument.model_validate_json(
                (root / (doc.artifact_ref + ".source.json")).read_bytes()
            )
            if (
                source.document_id != doc.document_id
                or source.lines[0] != WARNING
                or source.lines[1] != f"document_id: {doc.document_id}"
                or source.lines[2] != f"claim_id: {doc.claim_id}"
                or (source.rendering == "png-schematic") != (doc.kind == DocumentKind.DAMAGE_PHOTO)
                or render_document(source) != payload
            ):
                raise ValueError("artifact content does not match its synthetic source record")
            sources[doc.document_id] = source
            if sample.input_case.claim.loss_at > doc.uploaded_at:
                raise ValueError("loss timestamp cannot follow fixture upload timestamp")
        for field in sample.extraction_fields:
            evidence = field.expected
            source = sources[evidence.document_id]
            if (
                field.source_line > len(source.lines)
                or source.lines[field.source_line - 1]
                != f"{evidence.field_name}: {evidence.observed_value}"
                or (field.location_kind == "image_caption") != (source.rendering == "png-schematic")
            ):
                raise ValueError("extraction field does not match the stated source line/caption")
            normalized = (
                evidence.observed_value.lower().replace(" ", "_")
                if field.location_kind == "image_caption"
                else evidence.observed_value
            )
            if evidence.normalized_value != normalized:
                raise ValueError("normalized ground truth disagrees with source value")
            if evidence.field_name in {"loss_at", "estimate_issued_at"}:
                timestamp = datetime.fromisoformat(evidence.observed_value)
                if timestamp.tzinfo is None or timestamp.utcoffset() is None:
                    raise ValueError("source timestamp must have a timezone")
                doc = next(
                    d for d in sample.input_case.documents if d.document_id == evidence.document_id
                )
                if timestamp > doc.uploaded_at:
                    raise ValueError("source timestamp cannot follow fixture upload")
        form_ids = {
            doc.document_id
            for doc in sample.input_case.documents
            if doc.kind == DocumentKind.CLAIM_FORM
        }
        form_fields = {
            field.expected.field_name: field.expected.observed_value
            for field in sample.extraction_fields
            if field.expected.document_id in form_ids
        }
        claim = sample.input_case.claim
        for policy in sample.policies:
            for document_id, expected_fields in (
                (
                    policy.schedule.document_id,
                    {
                        "policy_id": policy.policy_id,
                        "policy_version": policy.version,
                        "effective_from": policy.effective_from.isoformat(),
                        "effective_to": policy.effective_to.isoformat(),
                        "vehicle_reference": claim.vehicle_reference,
                    },
                ),
                (
                    policy.wording.document_id,
                    {
                        "policy_version": policy.version,
                        "product": policy.product,
                        "jurisdiction": policy.jurisdiction,
                    },
                ),
            ):
                observed = {
                    f.expected.field_name: f.expected.observed_value
                    for f in sample.extraction_fields
                    if f.expected.document_id == document_id
                }
                if any(observed.get(name) != value for name, value in expected_fields.items()):
                    raise ValueError(
                        "policy metadata disagrees with schedule/wording source fields"
                    )
        for name, expected in {
            "policy_id": claim.policy_id,
            "loss_at": claim.loss_at.isoformat(),
            "vehicle_reference": claim.vehicle_reference,
            "claimed_amount": f"{claim.claimed_amount:.2f}",
            "currency": claim.currency,
            "narrative": claim.narrative,
            "submitted_policy_version": sample.policy_selection.submitted_version,
        }.items():
            if form_fields.get(name) != expected:
                raise ValueError("claim facts disagree with claim-form extraction labels")
    return truth


def write_corpus(root: Path, seed: int) -> GroundTruth:
    """Write a fresh directory only. Existing datasets are never overwritten or deleted."""
    files = build_corpus(seed)
    root.mkdir(parents=True, exist_ok=False)
    for relative, payload in sorted(files.items()):
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
    return validate_corpus(root)


def check_reproduction(root: Path) -> GroundTruth:
    truth = validate_corpus(root)
    expected = build_corpus(truth.seed)
    if set(expected) != {
        path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()
    }:
        raise ValueError("regenerated file inventory differs")
    if any((root / path).read_bytes() != payload for path, payload in expected.items()):
        raise ValueError("deterministic regeneration differs from the stored corpus")
    return truth
