"""python -m claims_ai.dataset {generate,check} --output/--root PATH."""

import argparse
from pathlib import Path

from claims_ai.dataset.generator import DEFAULT_SEED
from claims_ai.dataset.validation import check_reproduction, write_corpus


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline synthetic motor corpus; no coverage decisions"
    )
    commands = parser.add_subparsers(dest="command", required=True)
    generate = commands.add_parser(
        "generate", help="create a new corpus directory; never overwrite"
    )
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--seed", type=int, default=DEFAULT_SEED)
    check = commands.add_parser(
        "check", help="validate bytes, labels and exact seeded regeneration"
    )
    check.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    try:
        truth = (
            write_corpus(args.output, args.seed)
            if args.command == "generate"
            else check_reproduction(args.root)
        )
    except (OSError, ValueError) as error:
        parser.exit(1, f"Corpus validation/generation failed ({type(error).__name__}).\n")
    print(
        f"Validated {len(truth.samples)} synthetic scenarios; "
        f"seed={truth.seed}; coverage unapproved."
    )


if __name__ == "__main__":
    main()
