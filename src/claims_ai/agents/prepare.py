"""Deterministic host validation; resolution, rules and authority never become agent tools."""

from claims_ai.agents.contracts import AssessmentInput, Limits, Reason, ReviewPacket
from claims_ai.dataset.generator import json_bytes
from claims_ai.knowledge.retrieval import retrieve
from claims_ai.rules.contracts import FindingStatus, RuleId
from claims_ai.rules.engine import evaluate
from claims_ai.rules.specification import digest


class InputBlocked(ValueError):
    def __init__(self, reason: Reason) -> None:
        self.reason = reason
        super().__init__(reason.value)


def prepare_packet(value: AssessmentInput, limits: Limits) -> ReviewPacket:
    value = AssessmentInput.model_validate(value)
    if value.task != "explain_findings":
        raise InputBlocked(Reason.UNSUPPORTED)
    checked = evaluate(value.rule_request, value.specification)
    if checked != value.rule_evaluation:
        raise InputBlocked(Reason.INPUT)
    if any(
        f.status != FindingStatus.PASS
        for f in checked.findings
        if f.rule_id in {RuleId.BINDING, RuleId.EVIDENCE}
    ):
        raise InputBlocked(Reason.EVIDENCE)
    query, response = value.retrieval_request, value.retrieval_response
    index = value.rule_request.index
    if query is None or response is None or index is None or response.status != "retrieved":
        raise InputBlocked(Reason.RETRIEVAL)
    if response != retrieve(value.rule_request.case, query, index):
        raise InputBlocked(Reason.CITATIONS)
    selected = value.rule_request.policy_version
    if query.policy_version != selected:
        raise InputBlocked(Reason.CITATIONS)
    required = {c for f in checked.findings for c in f.citations}
    supplied = {h.chunk.clause.citation for h in response.hits}
    if not required or not required <= supplied:
        raise InputBlocked(Reason.CITATIONS)
    payload = {
        "schema_version": "1.0",
        "synthetic": True,
        "claim_id": checked.claim_id,
        "case_sha256": checked.case_sha256,
        "rule_execution_key": checked.execution_key,
        "policy_status": "provisional_unapproved",
        "content_trust": "untrusted_document_and_retrieved_data",
        "required_reviewer": checked.required_reviewer.value,
        "findings": [f.model_dump(mode="json") for f in checked.findings],
        "evidence": [e.model_dump(mode="json") for e in value.rule_request.case.evidence],
        "clauses": [h.chunk.model_dump(mode="json") for h in response.hits],
    }
    packet = ReviewPacket.model_validate({**payload, "packet_sha256": digest(payload)})
    if len(json_bytes(packet.model_dump(mode="json"))) > limits.max_packet_bytes:
        raise InputBlocked(Reason.BUDGET)
    return packet
