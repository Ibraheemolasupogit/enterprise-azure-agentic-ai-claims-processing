"""Reproducible offline fixture benchmark CLI; no vendor/live options."""

import argparse
import asyncio
from pathlib import Path

from claims_ai.benchmark.adapters import FixtureAdapter
from claims_ai.benchmark.runner import run_benchmark, write_report
from claims_ai.dataset.validation import check_reproduction


def main() -> None:
    parser = argparse.ArgumentParser(description="SIMULATED extraction harness, not model accuracy")
    parser.add_argument("--corpus", type=Path, default=Path("data/synthetic/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--pdf-only", action="store_true", help="fixture capability restriction only"
    )
    args = parser.parse_args()
    try:
        if args.output.resolve().is_relative_to(args.corpus.resolve()):
            raise ValueError("result output must not modify the corpus")
        truth = check_reproduction(args.corpus)
        report = asyncio.run(
            run_benchmark(args.corpus, FixtureAdapter(truth, pdf_only=args.pdf_only))
        )
        write_report(report, args.output)
    except (OSError, ValueError) as error:
        parser.exit(
            1, f"Offline benchmark failed ({type(error).__name__}); no raw payload logged.\n"
        )
    print(
        f"SIMULATED harness: {len(report.documents)} documents, "
        f"{report.unique_label_count} unique labels."
    )
    print("Fixture echoes known truth; this is not a provider accuracy/performance result.")


if __name__ == "__main__":
    main()
