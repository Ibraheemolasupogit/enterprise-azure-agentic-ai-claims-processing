"""Input-only loading contract for a future isolated prediction process; no predictor."""

from hashlib import sha256
from pathlib import Path

from claims_ai.quality_ops.contracts import InputManifest, PredictionInputs


def bounded_bytes(path: Path, maximum: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("candidate file unavailable")
    with path.open("rb", buffering=0) as stream:
        content = stream.read(maximum + 1)
    if len(content) > maximum:
        raise ValueError("candidate file capacity")
    return content


def load_prediction_inputs(root: Path, *, expected_manifest_sha256: str) -> PredictionInputs:
    """Host supplies an independent input-manifest pin, not an expected answer.

    Reads exactly two allowlisted input files. Label/review files are never opened.
    This is structural separation, not an OS sandbox or proof of a blind holdout.
    """
    directory = root / "inputs"
    if root.is_symlink() or directory.is_symlink():
        raise ValueError("candidate alias denied")
    raw = bounded_bytes(directory / "manifest.json", 8192)
    if sha256(raw).hexdigest() != expected_manifest_sha256:
        raise ValueError("input manifest mismatch")
    manifest = InputManifest.model_validate_json(raw)
    content = bounded_bytes(directory / manifest.file, manifest.maximum_bytes)
    if sha256(content).hexdigest() != manifest.sha256:
        raise ValueError("prediction inputs mismatch")
    return PredictionInputs.model_validate_json(content)
