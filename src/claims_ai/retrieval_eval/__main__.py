"""Offline lexical evaluation CLI; writes new artifacts only, never gold/corpus inputs."""

import argparse
import asyncio
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.retrieval_eval.runner import evaluate


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline lexical evaluation; no semantic/hybrid RAG"
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/synthetic/motor/v1"))
    parser.add_argument(
        "--gold", type=Path, default=Path("data/evaluation/policy-retrieval/v1/queries.json")
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if any(
            args.output.resolve().is_relative_to(p.resolve())
            for p in (args.corpus, args.gold.parent)
        ):
            raise ValueError("output cannot modify evaluation inputs")
        report = asyncio.run(evaluate(args.corpus, args.gold))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(json_bytes(report))
    except (OSError, ValueError, StopIteration, IndexError, KeyError) as error:
        parser.exit(
            1, f"Offline lexical evaluation failed ({type(error).__name__}); raw inputs omitted.\n"
        )
    print(
        "OFFLINE_LEXICAL report written; authored labels are not independently adjudicated truth."
    )


if __name__ == "__main__":
    main()
