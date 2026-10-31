"""Pinned offline evaluation; the engine receives inputs/faults, never relevance or expectations."""

import asyncio
import platform
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path
from typing import Protocol

from claims_ai.dataset.schema import GroundTruth
from claims_ai.dataset.validation import check_reproduction
from claims_ai.knowledge.contracts import (
    IngestionRequest,
    KnowledgeIndex,
    RetrievalRequest,
    fingerprint,
)
from claims_ai.knowledge.ingestion import ingest
from claims_ai.knowledge.retrieval import retrieve, retrieve_from
from claims_ai.models import Case
from claims_ai.retrieval_eval.contracts import Fault, GoldenQuery
from claims_ai.retrieval_eval.dataset import Context, context_for, load_gold
from claims_ai.retrieval_eval.scoring import score, summarize


class EvaluationEngine(Protocol):
    async def run(
        self, case: Case, request: RetrievalRequest, index: KnowledgeIndex, *, fault: Fault
    ) -> object: ...


class FaultSource:
    """SIMULATED unavailable dependency, not a provider implementation or real outage."""

    def __init__(self, fault: Fault) -> None:
        self.fault = fault

    async def load(self, index_sha256: str) -> KnowledgeIndex | None:
        if self.fault == Fault.OUTAGE:
            raise OSError("simulated offline store outage")
        return None


class LexicalEngine:
    async def run(
        self, case: Case, request: RetrievalRequest, index: KnowledgeIndex, *, fault: Fault
    ) -> object:
        if fault in {Fault.OUTAGE, Fault.MISSING_INDEX}:
            return await retrieve_from(FaultSource(fault), case, request)
        return retrieve(case, request, index)


def prepare(
    root: Path, truth: GroundTruth, gold: GoldenQuery
) -> tuple[Context, KnowledgeIndex, RetrievalRequest]:
    context = context_for(root, truth, gold)
    index = ingest(
        IngestionRequest(case=context.case, policies=context.policies, documents=context.documents)
    )
    if gold.fault == Fault.SOURCE_TAMPER:
        payload = index.model_dump(mode="json")
        payload["entries"][0]["sources"][0]["source"]["title"] = "Manipulated synthetic source"
        payload["index_sha256"] = fingerprint(
            {k: v for k, v in payload.items() if k != "index_sha256"}
        )
        index = KnowledgeIndex.model_validate(payload)
    request = RetrievalRequest.model_validate(
        {
            **gold.request.model_dump(exclude={"k"}),
            "limit": gold.request.k,
            "index_sha256": "0" * 64 if gold.fault == Fault.WRONG_SNAPSHOT else index.index_sha256,
        }
    )
    return context, index, request


def code_hash(folder: Path) -> str:
    return sha256(
        b"".join(p.name.encode() + b"\x00" + p.read_bytes() for p in sorted(folder.glob("*.py")))
    ).hexdigest()


async def evaluate(
    root: Path, gold_path: Path, *, engine: EvaluationEngine | None = None
) -> dict[str, object]:
    truth = check_reproduction(root)
    dataset = load_gold(gold_path, root, truth)
    active_engine = engine or LexicalEngine()
    rows = []
    for gold in dataset.queries:
        context, index, request = prepare(root, truth, gold)
        raw = None
        technical_error = False
        try:
            raw = await asyncio.wait_for(
                active_engine.run(context.case, request, index, fault=gold.fault), timeout=2.0
            )
        except Exception:
            technical_error = True
        rows.append(score(gold, context, request, raw, technical_error=technical_error))
    evaluations = tuple(rows)
    return {
        "report_version": "retrieval-eval-v1",
        "evaluation_mode": "OFFLINE_LEXICAL",
        "dataset_version": dataset.dataset_version,
        "label_status": dataset.label_status,
        "split": dataset.split,
        "contains_untrusted_synthetic_text": True,
        "technical_faults": "SIMULATED offline store exceptions/missing index",
        "gold_sha256": sha256(gold_path.read_bytes()).hexdigest(),
        "gold_manifest_sha256": sha256(
            (gold_path.parent / "manifest.json").read_bytes()
        ).hexdigest(),
        "corpus_manifest_sha256": dataset.corpus_manifest_sha256,
        "evaluator_sha256": code_hash(Path(__file__).parent),
        "retriever_sha256": code_hash(Path(__file__).parents[1] / "knowledge"),
        "engine": type(active_engine).__name__,
        "python_version": platform.python_version(),
        "pydantic_version": version("pydantic"),
        "overall": summarize(evaluations),
        "by_cohort": {
            c: summarize(tuple(r for r in evaluations if r.cohort == c))
            for c in sorted({r.cohort for r in evaluations})
        },
        "by_scenario": {
            s: summarize(tuple(r for r in evaluations if r.scenario == s))
            for s in sorted({r.scenario for r in evaluations})
        },
        "queries": [r.model_dump(mode="json") for r in evaluations],
    }
