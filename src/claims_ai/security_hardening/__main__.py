"""Reproducible offline M21 evidence, never activates a deployment profile."""

import argparse
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.rules.__main__ import protected_output
from claims_ai.security_hardening.evaluation import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(description="M21 simulated offline identity/security evidence")
    parser.add_argument("--fixture-root", type=Path, default=Path("data/security/identity/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.fixture_root.resolve(strict=True)
        destination = protected_output(args.output, root)
        report = evaluate(root)
        content = json_bytes(report)
        if len(content) > 1048576 or report["counts"] != {"PASS": 25, "FAIL": 0, "NOT_TESTED": 0}:
            raise ValueError("evaluation incomplete or failed")
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination = protected_output(destination, root)
        with destination.open("xb") as stream:
            stream.write(content)
    except Exception:
        parser.exit(3, "Offline M21 evidence unavailable; details redacted.\n")
    print("M21 offline supplement: 25 PASS / 0 FAIL / 0 NOT_TESTED; no live identity integration.")


if __name__ == "__main__":
    main()
