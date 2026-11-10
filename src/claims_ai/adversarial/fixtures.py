"""Bounded source-pinned authored catalog; no arbitrary code, URLs or test plugins execute."""

import json
from hashlib import sha256
from pathlib import Path

from claims_ai.adversarial.contracts import Catalog, CatalogManifest


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("ambiguous catalog JSON")
        result[key] = value
    return result


def load_catalog(root: Path) -> Catalog:
    manifest_path, path = root / "manifest.json", root / "scenarios.json"
    if manifest_path.stat().st_size > 4096 or path.stat().st_size > 131072:
        raise ValueError("adversarial fixture budget exceeded")
    manifest = CatalogManifest.model_validate_json(manifest_path.read_bytes())
    data = path.read_bytes()
    if sha256(data).hexdigest() != manifest.scenarios_sha256:
        raise ValueError("adversarial fixture fingerprint mismatch")
    value = json.loads(data, object_pairs_hook=unique_object)
    return Catalog.model_validate_json(json.dumps(value))
