"""Reproducible draft-policy lexical demo; no policy activation or cloud operations."""

import argparse
import platform
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.schema import SourceDocument
from claims_ai.dataset.validation import check_reproduction
from claims_ai.knowledge.contracts import (
    IngestionRequest,
    KnowledgeIndex,
    PolicyDocument,
    RetrievalRequest,
)
from claims_ai.knowledge.ingestion import ingest
from claims_ai.knowledge.retrieval import retrieve
from claims_ai.models import DocumentKind


def offline_report(root: Path) -> dict[str, object]:
    truth = check_reproduction(root)
    indexes: dict[str, KnowledgeIndex] = {}
    attempts = []
    for sample in truth.samples:
        case = sample.input_case
        if case.claim.claim_id not in indexes:
            artifact_ids = {a.document_id for p in sample.policies for a in p.artifacts}
            documents = tuple(
                PolicyDocument(
                    document=d,
                    content=(root / d.artifact_ref).read_bytes(),
                    source=SourceDocument.model_validate_json(
                        (root / (d.artifact_ref + ".source.json")).read_bytes()
                    ),
                )
                for d in case.documents
                if d.document_id in artifact_ids
            )
            indexes[case.claim.claim_id] = ingest(
                IngestionRequest(
                    case=case,
                    policies=sample.policies,
                    documents=documents,
                )
            )
        index = indexes[case.claim.claim_id]
        form = next(d for d in case.documents if d.kind == DocumentKind.CLAIM_FORM)
        source = SourceDocument.model_validate_json(
            (root / (form.artifact_ref + ".source.json")).read_bytes()
        )
        submitted = [
            line.removeprefix("submitted_policy_version: ")
            for line in source.lines
            if line.startswith("submitted_policy_version: ")
        ]
        if len(submitted) != 1:
            raise ValueError("fixture submitted-version metadata is not unique")
        for query in ("accidental damage", "gradual wear", "unlisted-term-zzzz"):
            request = RetrievalRequest(
                claim_id=case.claim.claim_id,
                policy_id=case.claim.policy_id,
                policy_version=submitted[0],
                incident_date=case.claim.loss_at.date(),
                index_sha256=index.index_sha256,
                query=query,
            )
            response = retrieve(case, request, index)
            attempts.append(
                {
                    "scenario_id": sample.scenario_id,
                    "request": request.model_dump(mode="json"),
                    "response": response.model_dump(mode="json"),
                }
            )
    code_hash = sha256(
        b"".join(
            p.name.encode() + b"\x00" + p.read_bytes()
            for p in sorted(Path(__file__).parent.glob("*.py"))
        )
    ).hexdigest()
    return {
        "schema_version": "policy-knowledge-run-v1",
        "execution_mode": "OFFLINE_SYNTHETIC",
        "method": "distinct_token_overlap_v1",
        "knowledge_status": "unapproved_fixture_only",
        "contains_untrusted_synthetic_text": True,
        "operational_policy_activation": False,
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "processor_sha256": code_hash,
        "manifest_sha256": sha256((root / "manifest.json").read_bytes()).hexdigest(),
        "indexes": [indexes[key].model_dump(mode="json") for key in sorted(indexes)],
        "attempts": attempts,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Offline draft-policy lexical lookup; no hybrid RAG"
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/synthetic/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.output.resolve().is_relative_to(args.corpus.resolve()):
            raise ValueError("output cannot modify corpus")
        report = offline_report(args.corpus)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("xb") as stream:
            stream.write(json_bytes(report))
    except (OSError, ValueError, StopIteration) as error:
        parser.exit(
            1, f"Offline policy lookup failed ({type(error).__name__}); raw text omitted.\n"
        )
    print("OFFLINE_SYNTHETIC lexical report written; draft clauses only, no coverage decisions.")


if __name__ == "__main__":
    main()
