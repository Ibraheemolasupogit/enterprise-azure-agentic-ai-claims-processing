"""Bounded local acceptance probes using production verification and fresh child processes."""

import json
import subprocess
import sys
from pathlib import Path
from typing import Literal

from claims_ai.security_hardening.contracts import Anchor, Grant


def child_probe(
    path: Path,
    *,
    credential: str,
    public_pem: bytes,
    policy: dict[str, object],
    integrity_key: bytes,
    grant: Grant,
    anchor: Anchor,
    now: int,
    actor: Literal["reviewer", "supervisor"] = "reviewer",
) -> dict[str, object]:
    """Private stdin carries synthetic credential/context, never argv, env, files or reports."""
    import claims_ai

    package_parent = str(Path(claims_ai.__file__).resolve().parent.parent)
    code = (
        "import sys; sys.path.insert(0,sys.argv[1]); "
        "from claims_ai.security_hardening.worker import main; main()"
    )
    value = {
        "database": str(path),
        "credential": credential,
        "public_key": public_pem.decode(),
        "policy": policy,
        "integrity_key": integrity_key.hex(),
        "grant": grant.model_dump(mode="json"),
        "anchor": anchor.model_dump(mode="json"),
        "now": now,
        "actor": actor,
        "case_ids": grant.case_ids,
    }
    result = subprocess.run(
        [sys.executable, "-I", "-B", "-c", code, package_parent],
        input=json.dumps(value),
        capture_output=True,
        text=True,
        cwd=path.parent,
        timeout=20,
    )
    if result.returncode != 0 or len(result.stdout) > 4096:
        raise ValueError("offline restart probe unavailable; details redacted")
    response = json.loads(result.stdout)
    if (
        not isinstance(response, dict)
        or set(response) != {"allowed", "signature_valid", "context_sha256"}
        or type(response["allowed"]) is not bool
        or type(response["signature_valid"]) is not bool
    ):
        raise ValueError("offline restart probe invalid")
    return response
