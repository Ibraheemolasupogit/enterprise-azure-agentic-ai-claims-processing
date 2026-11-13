"""Offline engineering evaluation, never an approved held-out or cloud release."""

import argparse
import os
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.quality_ops.runner import evaluate
from claims_ai.rules.__main__ import protected_output


def main() -> None:
    parser = argparse.ArgumentParser(description="M22 offline engineering evaluation")
    parser.add_argument("--candidate-root", type=Path, default=Path("data/evaluation/m22/v1"))
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument("--operations-root", type=Path, default=Path("data/operations/m22/v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--telemetry-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        roots = (
            args.candidate_root.resolve(strict=True),
            args.operations_root.resolve(strict=True),
        )
        outputs = [
            protected_output(p, args.spec_root.resolve(strict=True), roots)
            for p in (args.output, args.telemetry_output)
        ]
        if outputs[0] == outputs[1] or any(p.exists() or p.is_symlink() for p in outputs):
            raise ValueError("exclusive output required")
        report, raw = evaluate(
            args.candidate_root.resolve(strict=True),
            args.spec_root.resolve(strict=True),
            args.operations_root.resolve(strict=True),
        )
        contents = [json_bytes(report), json_bytes(raw)]
        if any(len(data) > 4194304 for data in contents):
            raise ValueError("report capacity")
        # Completion report is published only after its separate telemetry evidence.
        for index in (1, 0):
            path, content = outputs[index], contents[index]
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            path = protected_output(path, args.spec_root.resolve(strict=True), roots)
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(content)
    except Exception:
        parser.exit(3, "M22 offline evidence unavailable; details redacted.\n")
    print(
        "M22 engineering "
        + str(report["engineering_status"])
        + "; 60 candidate cases NOT_TESTED/PENDING_REVIEW; cloud export disabled."
    )
    if not report["harness_complete"]:
        raise SystemExit(3)
    if report["engineering_status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
