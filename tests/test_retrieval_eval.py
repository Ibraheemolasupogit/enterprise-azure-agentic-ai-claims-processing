"""Metric math, independent labels, adversarial responses and reproducible offline evaluation."""

import asyncio
import json
import subprocess
import sys
from hashlib import sha256
from math import log2
from pathlib import Path

import pytest
from pydantic import ValidationError

from claims_ai.dataset.generator import json_bytes
from claims_ai.dataset.schema import GroundTruth
from claims_ai.knowledge import ingestion, retrieval
from claims_ai.knowledge.contracts import (
    KnowledgeIndex,
    Reason,
    RetrievalRequest,
)
from claims_ai.models import Case
from claims_ai.retrieval_eval.contracts import Cohort, Fault, GoldenDataset, GoldenManifest
from claims_ai.retrieval_eval.dataset import load_gold, source_chunk
from claims_ai.retrieval_eval.runner import LexicalEngine, evaluate, prepare
from claims_ai.retrieval_eval.scoring import ranking_metrics, score, summarize

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "data/synthetic/motor/v1"
GOLD = ROOT / "data/evaluation/policy-retrieval/v1/queries.json"


@pytest.fixture(scope="module")
def truth() -> GroundTruth:
    return GroundTruth.model_validate_json((CORPUS / "ground_truth.json").read_bytes())


@pytest.fixture(scope="module")
def gold(truth: GroundTruth) -> GoldenDataset:
    return load_gold(GOLD, CORPUS, truth)


def test_ranking_math_with_graded_relevance_and_original_ranks() -> None:
    result = ranking_metrics(("irrelevant", "b", "a"), {"a": 3, "b": 1}, 3)
    assert result is not None
    assert result.precision_at_k == pytest.approx(2 / 3)
    assert result.recall_at_k == 1 and result.mrr_at_k == 0.5
    assert result.ndcg_at_k == pytest.approx((1 / log2(3) + 7 / log2(4)) / (7 + 1 / log2(3)))


@pytest.mark.parametrize(
    ("retrieved", "k", "precision", "recall", "mrr"),
    [
        ((), 3, 0.0, 0.0, 0.0),
        (("a",), 3, 1 / 3, 0.5, 1.0),
        (("a", "a", "b"), 3, 2 / 3, 1.0, 1.0),
        ((None, "a", "b"), 1, 0.0, 0.0, 0.0),
        ((None, "a", "b"), 2, 0.5, 0.5, 0.5),
    ],
)
def test_empty_short_duplicate_and_truncated_rankings(
    retrieved: tuple[str | None, ...],
    k: int,
    precision: float,
    recall: float,
    mrr: float,
) -> None:
    result = ranking_metrics(retrieved, {"a": 1, "b": 1}, k)
    assert result is not None
    assert result.precision_at_k == precision and result.recall_at_k == recall
    assert result.mrr_at_k == mrr and 0 <= result.ndcg_at_k <= 1


def test_empty_relevance_is_not_perfect_ranking() -> None:
    assert ranking_metrics((), {}, 3) is None
    assert ranking_metrics(("anything",), {}, 3) is None
    for k, grades in [(0, {"a": 1}), (3, {"a": 0}), (3, {"a": 4})]:
        with pytest.raises(ValueError):
            ranking_metrics((), grades, k)


def test_gold_loading_never_calls_retriever_or_ingestion(
    truth: GroundTruth,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("gold labels cannot come from the engine")

    monkeypatch.setattr(ingestion, "ingest", forbidden)
    monkeypatch.setattr(retrieval, "retrieve", forbidden)
    monkeypatch.setattr(retrieval, "tokens", forbidden)
    loaded = load_gold(GOLD, CORPUS, truth)
    assert len(loaded.queries) == 30
    assert loaded.label_status == "authored_not_independently_adjudicated"
    assert {q.cohort for q in loaded.queries} == set(Cohort)
    assert loaded.queries[6].request.query == "automobile collision"
    assert loaded.queries[6].relevant[0].chunk.clause.citation.clause_id == "C01"


class LabelsBlindEngine:
    def __init__(self) -> None:
        self.calls = 0

    async def run(
        self, case: Case, request: RetrievalRequest, index: KnowledgeIndex, *, fault: Fault
    ) -> object:
        assert not hasattr(request, "relevant") and not hasattr(index, "expected_reason")
        self.calls += 1
        return await LexicalEngine().run(case, request, index, fault=fault)


def test_engine_does_not_receive_gold_and_reports_real_failures(gold: GoldenDataset) -> None:
    engine = LabelsBlindEngine()
    report = asyncio.run(evaluate(CORPUS, GOLD, engine=engine))
    assert engine.calls == len(gold.queries)
    assert report["evaluation_mode"] == "OFFLINE_LEXICAL"
    overall = report["overall"]
    assert isinstance(overall, dict)
    assert overall["expected_behavior"]["numerator"] == 26
    assert {f["query_id"] for f in overall["failure_examples"]} == {
        "Q-007",
        "Q-012",
        "Q-015",
        "Q-029",
    }
    assert overall["ranking_answerable_only_by_k"]["3"]["denominator_queries"] == 11


@pytest.mark.parametrize(
    "tamper",
    ["page", "line", "hash", "text", "wrong_version", "cross_policy", "binding", "duplicate"],
)
def test_invalid_hits_do_not_earn_relevance_credit(
    truth: GroundTruth,
    gold: GoldenDataset,
    tamper: str,
) -> None:
    query = gold.queries[0]
    context, index, request = prepare(CORPUS, truth, query)
    raw = retrieval.retrieve(context.case, request, index).model_dump(mode="json")
    chunk = raw["hits"][0]["chunk"]
    if tamper == "page":
        chunk["clause"]["citation"]["page"] = 2
    elif tamper == "line":
        chunk["source_line_start"] = 8
    elif tamper == "hash":
        chunk["clause"]["citation"]["artifact_sha256"] = "0" * 64
    elif tamper == "text":
        chunk["clause"]["text"] = "Unsupported statement"
    elif tamper == "wrong_version":
        raw["hits"][0]["chunk"] = source_chunk(context, "draft-v2", "C01", 7).model_dump(
            mode="json"
        )
    elif tamper == "cross_policy":
        foreign = gold.queries[4]
        other, _, _ = prepare(CORPUS, truth, foreign)
        raw["hits"][0]["chunk"] = source_chunk(other, "draft-v2", "C01", 7).model_dump(mode="json")
    elif tamper == "binding":
        raw["request_sha256"] = "0" * 64
    else:
        raw["hits"].append(raw["hits"][0])
    result = score(query, context, request, raw)
    assert result.schema_valid and not result.expected_behavior_correct
    assert result.ranking is not None
    if tamper != "duplicate":
        assert result.ranking.recall_at_k == 0
    else:
        assert result.ranking.recall_at_k == 1 and result.ranking.precision_at_k == 1 / 3
    if tamper == "cross_policy":
        assert result.hits[0].cross_policy and result.hits[0].cross_claim
    if tamper == "wrong_version":
        assert result.hits[0].citation_valid and not result.hits[0].version_and_date_correct


def test_no_answer_is_distinct_from_outage_invalid_and_schema_failure(
    truth: GroundTruth, gold: GoldenDataset
) -> None:
    query = gold.queries[10]
    context, index, request = prepare(CORPUS, truth, query)
    correct = score(query, context, request, retrieval.retrieve(context.case, request, index))
    assert correct.expected_behavior_correct and correct.ranking is None
    for reason, observed in [(Reason.OUTAGE, "technical_failure"), (Reason.QUERY, "invalid_query")]:
        result = score(query, context, request, retrieval.abstain(request, reason))
        assert not result.expected_behavior_correct and result.observed == observed
        assert result.false_positive_retrieval is False
    malformed = score(query, context, request, {"secret": "SYNTHETIC-PRIVATE-PAYLOAD"})
    assert not malformed.schema_valid and malformed.false_positive_retrieval is None
    assert "PRIVATE" not in malformed.model_dump_json()
    summary = summarize((malformed,))
    assert summary["citation_validity"] == {"numerator": 0, "denominator": 0, "rate": None}
    assert summary["false_positive_retrieval"] == {"numerator": 0, "denominator": 0, "rate": None}


def test_malformed_gold_rejected_before_engine_calls(gold: GoldenDataset, tmp_path: Path) -> None:
    changes: list[dict[str, object]] = [
        {"queries": [gold.queries[0].model_dump(), gold.queries[0].model_dump()]},
        {"queries": [{**gold.queries[0].model_dump(), "relevant": []}]},
        {
            "queries": [
                {**gold.queries[10].model_dump(), "expected_reason": "retrieval_unavailable"}
            ]
        },
        {"queries": [{**gold.queries[26].model_dump(), "fault": "none"}]},
        {"label_status": "independently_adjudicated"},
    ]
    for change in changes:
        with pytest.raises(ValidationError):
            GoldenDataset.model_validate({**gold.model_dump(), **change})
    invalid = json_bytes({**gold.model_dump(mode="json"), "queries": []})
    path = tmp_path / "queries.json"
    path.write_bytes(invalid)
    manifest = GoldenManifest(
        queries_sha256=sha256(invalid).hexdigest(),
        corpus_manifest_sha256=gold.corpus_manifest_sha256,
    )
    (tmp_path / "manifest.json").write_bytes(json_bytes(manifest.model_dump(mode="json")))
    engine = LabelsBlindEngine()
    with pytest.raises(ValueError):
        asyncio.run(evaluate(CORPUS, path, engine=engine))
    assert engine.calls == 0


def test_ambiguous_register_cannot_earn_version_credit(
    truth: GroundTruth, gold: GoldenDataset
) -> None:
    query = gold.queries[20]
    context, _, request = prepare(CORPUS, truth, query)
    chunk = source_chunk(context, "draft-v1", "C01", 7)
    payload = retrieval.abstain(request, Reason.CONFLICT).model_dump(mode="json")
    payload.update(
        status="retrieved",
        reason=None,
        hits=[
            {
                "chunk": chunk.model_dump(mode="json"),
                "matched_terms": ["damage"],
                "lexical_score": 1,
            }
        ],
    )
    result = score(query, context, request, payload)
    assert result.hits[0].citation_valid and not result.hits[0].version_and_date_correct
    assert not result.expected_behavior_correct


@pytest.mark.parametrize(
    "tamper",
    ["manifest", "chunk_id", "source_line", "policy_version", "scope", "grade", "scenario"],
)
def test_evidence_integrity_of_gold_inputs(
    truth: GroundTruth,
    gold: GoldenDataset,
    tmp_path: Path,
    tamper: str,
) -> None:
    payload = gold.model_dump(mode="json")
    q = payload["queries"][0]
    if tamper == "chunk_id":
        q["relevant"][0]["chunk"]["chunk_id"] = "0" * 64
    elif tamper == "source_line":
        q["relevant"][0]["chunk"]["source_line_start"] = 200
    elif tamper == "policy_version":
        q["request"]["policy_version"] = "draft-v2"
    elif tamper == "scope":
        q["request"]["claim_id"] = "NS-CLM-00000000"
    elif tamper == "grade":
        q["relevant"][0]["grade"] = 0
    elif tamper == "scenario":
        q["case_scenario"] = "SCN-UNKNOWN"
    path = tmp_path / "queries.json"
    content = json_bytes(payload)
    path.write_bytes(content)
    manifest = GoldenManifest(
        queries_sha256="0" * 64 if tamper == "manifest" else sha256(content).hexdigest(),
        corpus_manifest_sha256=gold.corpus_manifest_sha256,
    )
    (tmp_path / "manifest.json").write_bytes(json_bytes(manifest.model_dump(mode="json")))
    with pytest.raises(ValueError):
        load_gold(path, CORPUS, truth)


class BrokenEngine:
    async def run(
        self, case: Case, request: RetrievalRequest, index: KnowledgeIndex, *, fault: Fault
    ) -> object:
        raise OSError("SYNTHETIC-PRIVATE-backend-token")


def test_engine_errors_are_reported_not_turned_into_no_answers() -> None:
    report = asyncio.run(evaluate(CORPUS, GOLD, engine=BrokenEngine()))
    assert isinstance(report["overall"], dict)
    assert report["overall"]["observed_technical_failures"] == 30
    assert report["overall"]["expected_behavior"]["numerator"] == 0
    assert "PRIVATE" not in json.dumps(report)


def test_cli_reproduces_reports_and_protects_gold_and_corpus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYTHONPATH", str(ROOT / "src"))
    command = [
        sys.executable,
        "-m",
        "claims_ai.retrieval_eval",
        "--corpus",
        str(CORPUS),
        "--gold",
        str(GOLD),
    ]
    outputs = [tmp_path / "one.json", tmp_path / "two.json"]
    for output in outputs:
        subprocess.run([*command, "--output", str(output)], check=True, capture_output=True)
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    for target in [outputs[0], CORPUS / "must-not-write.json", GOLD.parent / "must-not-write.json"]:
        assert (
            subprocess.run([*command, "--output", str(target)], capture_output=True).returncode != 0
        )
    assert not (GOLD.parent / "must-not-write.json").exists()
    assert not (CORPUS / "must-not-write.json").exists()
