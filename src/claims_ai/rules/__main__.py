"""Reproducible provisional rule findings on new synthetic, explicitly simulated fixtures."""

import argparse
import platform
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.rules.contracts import RuleEvaluation
from claims_ai.rules.engine import evaluate
from claims_ai.rules.fixtures import build_fixture, load_scenarios
from claims_ai.rules.specification import load_specification


def protected_output(
    output: Path, spec_root: Path, additional_roots: tuple[Path, ...] = ()
) -> Path:
    """Bind exclusions to host-selected input paths, never a working-directory data guess.

    A conventional data tree is derived from the explicit specification path.
    Hosts with separate/nonstandard reference trees must supply their absolute roots.
    Both lexical and resolved ancestry matter when the specification uses a symlink.
    """
    canonical_spec = spec_root.resolve(strict=True)
    roots = {canonical_spec}
    for path in (spec_root.absolute(), canonical_spec):
        roots.update(
            parent.resolve(strict=True) for parent in path.parents if parent.name == "data"
        )
    for root in additional_roots:
        if not root.is_absolute():
            raise ValueError("protected data roots must be explicit absolute paths")
        roots.add(root.resolve(strict=True))
    if any(not root.is_dir() for root in roots):
        raise ValueError("protected inputs must be existing directories")
    canonical_output = output.resolve()
    if (
        output.exists()
        or output.is_symlink()
        or any(
            canonical_output.is_relative_to(root) or root.is_relative_to(canonical_output)
            for root in roots
        )
    ):
        raise ValueError("output cannot overlap protected data or existing evidence")
    return canonical_output


def offline_report(root: Path) -> dict[str, object]:
    spec = load_specification(root)
    suite = load_scenarios(root)
    evaluations: list[RuleEvaluation] = []
    for scenario in suite.scenarios:
        request = build_fixture(spec, scenario)
        result = evaluate(request, spec)
        if result != evaluate(request, spec):
            raise ValueError("rule replay is not deterministic")
        evaluations.append(result)
    code_hash = sha256(
        b"".join(
            p.name.encode() + b"\x00" + p.read_bytes()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        )
    ).hexdigest()
    package = Path(__file__).parents[1]
    dependencies = [
        package / "models.py",
        *(
            p
            for folder in ("benchmark", "dataset", "evidence", "knowledge")
            for p in (package / folder).glob("*.py")
        ),
    ]
    dependency_hash = sha256(
        b"".join(
            str(p.relative_to(package)).encode() + b"\x00" + p.read_bytes()
            for p in sorted(dependencies)
        )
    ).hexdigest()
    return {
        "report_version": "provisional-rules-run-v1",
        "evaluation_mode": "OFFLINE_PROVISIONAL",
        "fixture_execution_mode": "SIMULATED",
        "scan_and_reviewer_assertions": "synthetic_test_assertions_only",
        "specification_status": "provisional_unapproved",
        "final_outcomes_created": 0,
        "settlements_authorized": 0,
        "m4_cases_modified": False,
        "specification_sha256": sha256((root / "specification.json").read_bytes()).hexdigest(),
        "scenarios_sha256": sha256((root / "scenarios.json").read_bytes()).hexdigest(),
        "manifest_sha256": sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "processor_sha256": code_hash,
        "foundation_sha256": dependency_hash,
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "fixtures": [
            {"fixture_id": s.fixture_id, "evaluation": r.model_dump(mode="json")}
            for s, r in zip(suite.scenarios, evaluations, strict=True)
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline provisional rules: findings, never claim decisions"
    )
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument(
        "--protected-data-root",
        type=Path,
        action="append",
        default=[],
        help="additional trusted absolute reference-data root; repeat for separate trees",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        protected = tuple(args.protected_data_root)
        output = protected_output(args.output, args.spec_root, protected)
        report = offline_report(args.spec_root)
        if protected_output(args.output, args.spec_root, protected) != output:
            raise ValueError("output binding changed during evaluation")
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(json_bytes(report))
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(
            1, f"Provisional rule evaluation failed ({type(error).__name__}); raw inputs omitted.\n"
        )
    print(
        "OFFLINE_PROVISIONAL findings written; SIMULATED inputs, "
        "human review required, no settlements."
    )


if __name__ == "__main__":
    main()
