"""Offline proposal processing of the M4/M5 oracle fixture; no scan or admission claims."""

import argparse
import asyncio
import platform
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from claims_ai.benchmark.adapters import FixtureAdapter
from claims_ai.benchmark.contracts import ExtractionRequest, FieldSpec
from claims_ai.benchmark.scoring import field_kind
from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.schema import SourceDocument
from claims_ai.dataset.validation import check_reproduction
from claims_ai.evidence.contracts import EvidenceHistory, ProcessingRequest
from claims_ai.evidence.processing import process_extraction


async def offline_report(root: Path) -> dict[str, object]:
    truth = check_reproduction(root)
    adapter = FixtureAdapter(truth)
    histories: dict[str, EvidenceHistory] = {}
    attempts = []
    for sample in truth.samples:
        case = sample.input_case
        for doc in case.documents:
            content = (root / doc.artifact_ref).read_bytes()
            source = SourceDocument.model_validate_json(
                (root / (doc.artifact_ref + ".source.json")).read_bytes()
            )
            specs = tuple(
                FieldSpec(name=f.expected.field_name, kind=field_kind(f.expected.field_name))
                for f in sample.extraction_fields
                if f.expected.document_id == doc.document_id
            )
            response = await adapter.extract(
                ExtractionRequest(
                    request_id=doc.document_id, document=doc, content=content, fields=specs
                )
            )
            request = ProcessingRequest(
                case=case,
                document_id=doc.document_id,
                request_id=doc.document_id,
                expected_provider=adapter.profile.identity,
                content=content,
                fixture_source=source,
            )
            result = process_extraction(request, response, histories.get(case.claim.claim_id))
            histories[case.claim.claim_id] = result.history
            attempts.append(
                {
                    "scenario_id": sample.scenario_id,
                    "document_id": doc.document_id,
                    **result.model_dump(mode="json", exclude={"history"}),
                }
            )
    code_hash = sha256(
        b"".join(
            p.name.encode() + b"\x00" + p.read_bytes()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        )
    ).hexdigest()
    return {
        "schema_version": "evidence-run-v1",
        "execution_mode": "SIMULATED",
        "contains_untrusted_synthetic_text": True,
        "case_admission_performed": False,
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "processor_sha256": code_hash,
        "manifest_sha256": sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "attempts": attempts,
        "histories": [histories[key].model_dump(mode="json") for key in sorted(histories)],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="SIMULATED evidence proposals; no scanning or admission"
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/synthetic/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.resolve().is_relative_to(args.corpus.resolve()):
            raise ValueError("output cannot modify corpus")
        report = asyncio.run(offline_report(args.corpus))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(json_bytes(report))
    except (OSError, ValueError) as error:
        parser.exit(
            1, f"Evidence processing failed ({type(error).__name__}); raw payload omitted.\n"
        )
    print(
        "SIMULATED evidence report written. "
        "Original documents remain quarantined; no case admission."
    )


if __name__ == "__main__":
    main()
