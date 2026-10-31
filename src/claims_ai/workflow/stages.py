"""Compose implemented local services; lifecycle and insurance logic remain in their owners."""

from dataclasses import dataclass
from uuid import UUID, uuid5

from claims_ai.agent_tools.contracts import Code as ToolCode
from claims_ai.agent_tools.contracts import GovernedResult, ToolGrant
from claims_ai.agent_tools.execution import Mode, assess
from claims_ai.agent_tools.tools import ReadServices
from claims_ai.agents.assessment import validate_draft
from claims_ai.agents.contracts import AssessmentInput, Limits
from claims_ai.agents.prepare import prepare_packet
from claims_ai.benchmark.contracts import Provider
from claims_ai.evidence.contracts import Disposition, EvidenceHistory
from claims_ai.evidence.processing import admit_evidence, process_extraction
from claims_ai.knowledge.contracts import IngestionRequest, PolicyDocument, RetrievalRequest
from claims_ai.knowledge.contracts import Reason as RetrievalReason
from claims_ai.knowledge.ingestion import ingest
from claims_ai.knowledge.retrieval import retrieve
from claims_ai.lifecycle import TransitionActor, TransitionRequest, transition_case
from claims_ai.models import Case, CaseState, DocumentKind, ReviewerRole, validate_required_evidence
from claims_ai.rules.contracts import EvaluationRequest, FindingStatus, RuleId
from claims_ai.rules.engine import evaluate
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import (
    Code,
    ReviewTask,
    Snapshot,
    Stage,
    State,
    Step,
    WorkflowLimits,
    WorkflowRequest,
)


@dataclass(frozen=True)
class Context:
    request: WorkflowRequest
    grant: ToolGrant
    execution_key: str
    limits: WorkflowLimits


def changed(snapshot: Snapshot, **values: object) -> Snapshot:
    return Snapshot.model_validate({**snapshot.model_dump(), **values})


def advance(snapshot: Snapshot, target: CaseState, context: Context) -> Snapshot:
    event = transition_case(
        snapshot.case,
        TransitionRequest(
            target=target,
            expected_revision=snapshot.case.revision,
            actor=TransitionActor(principal_id=context.grant.principal_id),
            audit_event_id=uuid5(
                UUID(hex=context.execution_key[:32]), f"{target}/{snapshot.case.revision}"
            ),
            occurred_at=context.request.requested_at,
            reason="Offline deterministic workflow stage; no claim outcome.",
        ),
    )
    return changed(snapshot, case=event.current, transitions=(*snapshot.transitions, event))


def review_task(
    context: Context,
    snapshot: Snapshot,
    reason: Code | str,
    role: ReviewerRole = ReviewerRole.SUPERVISOR,
) -> ReviewTask:
    return ReviewTask.model_validate(
        {
            "claim_id": snapshot.case.claim.claim_id,
            "case_sha256": digest(snapshot.case.model_dump(mode="json")),
            "correlation_id": context.grant.correlation_id,
            "required_reviewer": role,
            "reason": reason,
        }
    )


def blocked(context: Context, snapshot: Snapshot, code: Code, state: State) -> Step:
    return Step(
        snapshot=changed(snapshot, review_task=review_task(context, snapshot, code)),
        outcome="blocked",
        code=code,
        state=state,
    )


def evaluation_request(context: Context, snapshot: Snapshot) -> EvaluationRequest:
    request = context.request
    return EvaluationRequest(
        case=snapshot.case,
        policy_id=snapshot.case.claim.policy_id,
        policy_version=request.policy_version,
        index=snapshot.index,
        specification_sha256=digest(request.specification.model_dump(mode="json")),
        evidence_inputs=request.evidence_inputs,
        reviewed_facts=request.reviewed_facts,
        risk_flags=request.risk_flags,
        allow_simulated_evidence=request.allow_simulated_evidence,
    )


def assessment_input(context: Context, snapshot: Snapshot) -> AssessmentInput:
    if snapshot.rule_evaluation is None:
        raise ValueError("validated deterministic findings required")
    return AssessmentInput(
        rule_request=evaluation_request(context, snapshot),
        specification=context.request.specification,
        rule_evaluation=snapshot.rule_evaluation,
        retrieval_request=snapshot.retrieval_request,
        retrieval_response=snapshot.retrieval_response,
        untrusted_note=context.request.untrusted_note,
    )


def agent_step(context: Context, snapshot: Snapshot, result: GovernedResult) -> Step:
    if result.correlation_id != context.grant.correlation_id:
        raise ValueError("agent correlation mismatch")
    if result.status == "abstained":
        if result.reason in {ToolCode.UNAVAILABLE, ToolCode.TIMEOUT}:
            return Step(
                snapshot=snapshot,
                outcome="retryable",
                code=Code.DEPENDENCY if result.reason == ToolCode.UNAVAILABLE else Code.TIMEOUT,
                agent_attempt=result,
            )
        return Step.model_validate(
            {
                **blocked(context, snapshot, Code.AGENT, State.ABSTAINED).model_dump(),
                "agent_attempt": result,
            }
        )
    packet = prepare_packet(assessment_input(context, snapshot), Limits())
    if result.draft is None or not result.framework_executed or result.model_calls != 4:
        raise ValueError("complete governed agent execution required")
    from claims_ai.agent_tools.contracts import ALLOWLIST

    if tuple(r.tool for r in result.receipts) != ALLOWLIST or any(
        r.status != "ok" for r in result.receipts
    ):
        raise ValueError("complete successful tool receipts required")
    validate_draft(result.draft, packet)
    return Step(snapshot=changed(snapshot, agent_result=result), agent_attempt=result)


class LocalStages:
    """No external I/O; injected subclasses are trusted offline fault simulations only."""

    def __init__(
        self, *, mode: Mode = Mode.NORMAL, tool_services: ReadServices | None = None
    ) -> None:
        self.mode, self.tool_services = mode, tool_services

    async def run(self, stage: Stage, context: Context, snapshot: Snapshot) -> Step:
        return await {
            Stage.INTAKE: self.intake,
            Stage.EVIDENCE: self.evidence,
            Stage.POLICY: self.policy,
            Stage.RULES: self.rules,
            Stage.AGENT: self.agent,
            Stage.ROUTING: self.routing,
        }[stage](context, snapshot)

    async def intake(self, context: Context, snapshot: Snapshot) -> Step:
        request, case = context.request, Case.model_validate(snapshot.case)
        if (
            case.state != CaseState.RECEIVED
            or case.revision != 1
            or case.evidence
            or case.policy is not None
            or not request.allow_simulated_evidence
        ):
            return blocked(context, snapshot, Code.INTAKE, State.REJECTED)
        ids = [b.request.document_id for b in request.evidence_inputs]
        if len(ids) != len(set(ids)):
            return blocked(context, snapshot, Code.INTAKE, State.REJECTED)
        for bundle in request.evidence_inputs:
            original, provider = bundle.request, bundle.response.provider
            if (
                original.case.claim != case.claim
                or original.case.documents != case.documents
                or provider.provider != Provider.FIXTURE
                or provider.execution_mode != "SIMULATED"
            ):
                return blocked(context, snapshot, Code.INTAKE, State.REJECTED)
        snapshot = advance(snapshot, CaseState.VALIDATING, context)
        return Step(snapshot=advance(snapshot, CaseState.EXTRACTING, context))

    async def evidence(self, context: Context, snapshot: Snapshot) -> Step:
        request = context.request
        history = EvidenceHistory(claim_id=snapshot.case.claim.claim_id)
        if {b.request.document_id for b in request.evidence_inputs} != {
            d.document_id for d in snapshot.case.documents
        }:
            snapshot = advance(snapshot, CaseState.AWAITING_EVIDENCE, context)
            return blocked(context, snapshot, Code.MISSING, State.EVIDENCE)
        for bundle in request.evidence_inputs:
            result = process_extraction(bundle.request, bundle.response, history)
            history = result.history
            snapshot = changed(snapshot, history=history)
            if result.disposition != Disposition.ACCEPTED:
                snapshot = advance(snapshot, CaseState.QUARANTINED, context)
                return blocked(context, snapshot, Code.UNTRUSTED, State.QUARANTINED)
            admission = admit_evidence(
                snapshot.case, result, allow_simulated=request.allow_simulated_evidence
            )
            snapshot = changed(
                snapshot, case=admission.current, admissions=(*snapshot.admissions, admission)
            )
        try:
            validate_required_evidence(
                snapshot.case,
                frozenset(DocumentKind(kind) for kind in request.specification.required_kinds),
            )
        except ValueError:
            snapshot = advance(snapshot, CaseState.AWAITING_EVIDENCE, context)
            return blocked(context, snapshot, Code.MISSING, State.EVIDENCE)
        return Step(snapshot=advance(snapshot, CaseState.ASSESSING, context))

    async def policy(self, context: Context, snapshot: Snapshot) -> Step:
        documents = {d.document_id: d for d in snapshot.case.documents}
        sources = []
        for bundle in context.request.evidence_inputs:
            document = documents[bundle.request.document_id]
            if document.kind in {DocumentKind.POLICY_SCHEDULE, DocumentKind.POLICY_WORDING}:
                if bundle.request.fixture_source is None:
                    return blocked(context, snapshot, Code.POLICY, State.ABSTAINED)
                sources.append(
                    PolicyDocument(
                        document=document,
                        source=bundle.request.fixture_source,
                        content=bundle.request.content,
                    )
                )
        index = ingest(
            IngestionRequest(
                case=snapshot.case, policies=context.request.policies, documents=tuple(sources)
            )
        )
        query = RetrievalRequest(
            claim_id=snapshot.case.claim.claim_id,
            policy_id=snapshot.case.claim.policy_id,
            policy_version=context.request.policy_version,
            incident_date=snapshot.case.claim.loss_at.date(),
            index_sha256=index.index_sha256,
            query="provisional human",
            limit=10,
        )
        response = retrieve(snapshot.case, query, index)
        snapshot = changed(
            snapshot, index=index, retrieval_request=query, retrieval_response=response
        )
        if response.status != "retrieved":
            if response.reason == RetrievalReason.OUTAGE:
                raise OSError("offline retrieval unavailable")
            return blocked(context, snapshot, Code.POLICY, State.ABSTAINED)
        return Step(snapshot=snapshot)

    async def rules(self, context: Context, snapshot: Snapshot) -> Step:
        evaluation = evaluate(evaluation_request(context, snapshot), context.request.specification)
        snapshot = changed(snapshot, rule_evaluation=evaluation)
        if any(
            f.status != FindingStatus.PASS
            for f in evaluation.findings
            if f.rule_id in {RuleId.BINDING, RuleId.EVIDENCE}
        ):
            return blocked(context, snapshot, Code.RULES, State.ABSTAINED)
        return Step(snapshot=snapshot)

    async def agent(self, context: Context, snapshot: Snapshot) -> Step:
        value = assessment_input(context, snapshot)
        # Delegate only after verified same-case transitions/admissions; model cannot rebind.
        grant = ToolGrant.model_validate(
            {
                **context.grant.model_dump(),
                "case_sha256": digest(snapshot.case.model_dump(mode="json")),
            }
        )
        result = await assess(
            value, grant, limits=context.limits.tools, mode=self.mode, services=self.tool_services
        )
        return agent_step(context, snapshot, result)

    async def routing(self, context: Context, snapshot: Snapshot) -> Step:
        result = snapshot.agent_result
        if result is None or result.draft is None:
            raise ValueError("validated advisory draft required before routing")
        agent_step(context, changed(snapshot, agent_result=None), result)
        task = review_task(context, snapshot, "advisory_ready", result.required_reviewer)
        return Step(
            snapshot=changed(snapshot, review_task=task),
            state=State.SUPERVISOR
            if result.required_reviewer == ReviewerRole.SUPERVISOR
            else State.REVIEW,
        )
