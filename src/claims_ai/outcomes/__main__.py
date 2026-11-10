"""New-path-only offline M20 evidence; no serving, cloud or external delivery mode."""

import argparse
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.outcomes.evidence import offline_report
from claims_ai.rules.__main__ import protected_output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline synthetic durable outcome/recovery evidence"
    )
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        path = protected_output(args.output, args.spec_root)
        report = offline_report(args.spec_root.resolve())
        content = json_bytes(report)
        if len(content) > 1048576:
            raise ValueError("report limit")
        if protected_output(args.output, args.spec_root) != path:
            raise ValueError("output changed")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(content)
    except Exception as error:
        parser.exit(
            1,
            "Offline outcome verification failed ("
            + type(error).__name__
            + "); raw state omitted.\n",
        )
    print(
        "Synthetic durable outcomes and real subprocess recovery verified; "
        "no insurance or settlement authority."
    )


if __name__ == "__main__":
    main()
