"""Reproducible offline adversarial evidence; findings are never converted into success."""

import argparse
from pathlib import Path

from claims_ai.adversarial.runner import evaluate
from claims_ai.dataset.generator import json_bytes


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline claims adversarial evaluation; no external targets"
    )
    parser.add_argument("--fixture-root", type=Path, default=Path("data/security/adversarial/v1"))
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        output = args.output.resolve()
        roots = [args.fixture_root.resolve(), args.spec_root.resolve(), Path("data").resolve()]
        protected = [*roots, *(p for root in roots for p in root.parents if p.name == "data")]
        if output.exists() or any(output.is_relative_to(root) for root in protected):
            raise ValueError("new evidence outside reference data required")
        report = evaluate(args.fixture_root.resolve(), args.spec_root.resolve())
        content = json_bytes(report)
        if len(content) > 1048576:
            raise ValueError("evidence budget exceeded")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(content)
    except Exception as failure:
        parser.exit(
            3,
            "Adversarial evaluation unavailable ("
            + type(failure).__name__
            + "); raw input omitted.\n",
        )
    print(
        "M19 adversarial results: "
        + str(report["counts"])
        + ". Offline scope only; NOT_TESTED is not a blocked attack."
    )
    if (
        report["harness_complete"] is not True
        or report["operational_outcomes_observed"] is not False
    ):
        raise SystemExit(3)
    counts = report["counts"]
    if isinstance(counts, dict) and counts.get("FAIL", 0):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
