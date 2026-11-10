"""Explicit host authoring of supplied synthetic assessments, never M9 promotion."""

from base64 import b64encode
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid5

from claims_ai.api.auth import ApiAccess, SyntheticAuthenticator
from claims_ai.api.contracts import ApiScope
from claims_ai.human_review.__main__ import demo_sessions
from claims_ai.human_review.contracts import PrincipalKind
from claims_ai.human_review.validation import verify_advisory
from claims_ai.models import (
    Assessment,
    AssessmentOutcome,
    Case,
    DecisionAction,
    ReviewerDecision,
    RiskFlag,
)
from claims_ai.outcomes.authority import Authority
from claims_ai.outcomes.contracts import (
    Action,
    ApprovedInput,
    Binding,
    Command,
    RecoveryBundle,
    StoredCase,
)
from claims_ai.outcomes.store import OutcomeStore
from claims_ai.rules.specification import digest
from claims_ai.workflow.__main__ import demo_grant, demo_request
from claims_ai.workflow.contracts import WorkflowLimits, WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner, code_fingerprint

NS = UUID("20202020-2020-4020-8020-202020202020")
NOW = datetime(2027, 3, 1, tzinfo=UTC)


async def approved_fixture(
    root: Path,
    *,
    name: str,
    approved_outcome: AssessmentOutcome,
    fixture: str = "valid-v1",
    risks: tuple[RiskFlag, ...] = (),
    parent: Binding | None = None,
    request: WorkflowRequest | None = None,
) -> ApprovedInput:
    request = request or demo_request(root, fixture, "m20-" + name)
    grant = demo_grant(request)
    checkpoint = await WorkflowRunner().run(request, grant)
    limits = WorkflowLimits()
    verified = await verify_advisory(request, grant, checkpoint, limits)
    snapshot = verified.snapshot
    assert snapshot.index is not None and snapshot.retrieval_response is not None
    policy = next(
        e.policy for e in snapshot.index.entries if e.policy.version == request.policy_version
    )
    revision = snapshot.case.revision if parent is None else parent.case_revision + 3
    case = Case.model_validate(
        {**snapshot.case.model_dump(), "policy": policy, "revision": revision}
    )
    # approved_outcome is supplied explicitly by the synthetic policy owner. No
    # code maps provisional findings, advisory dispositions or illustrations to it.
    assessment = Assessment(
        assessment_id="NS-ASM-" + digest(name)[:8].upper(),
        claim_id=case.claim.claim_id,
        case_revision=case.revision,
        policy=policy,
        input_sha256=digest(case.model_dump(mode="json")),
        producer_version="host-approved-synthetic-v1",
        evidence_ids=tuple(e.evidence_id for e in case.evidence),
        citations=tuple(h.chunk.clause.citation for h in snapshot.retrieval_response.hits),
        outcome=approved_outcome,
        risk_flags=risks,
        rationale="Explicit supplied synthetic test assessment; not a computed insurance result.",
    )
    return ApprovedInput(
        approval_id=uuid5(NS, name),
        approved_by=uuid5(NS, "synthetic-policy-owner"),
        rationale="Explicit host approval of this exact supplied synthetic assessment and source.",
        case=case,
        assessment=assessment,
        parent=parent,
        bundle=RecoveryBundle(
            request=request,
            contents=tuple(b64encode(b.request.content).decode() for b in request.evidence_inputs),
            grant=grant,
            checkpoint=checkpoint,
            limits=limits,
            runtime_sha256=code_fingerprint(),
        ),
    )


@dataclass
class DemoHost:
    authority: Authority
    authenticator: SyntheticAuthenticator
    tokens: dict[str, str]


def demo_host(approved: tuple[ApprovedInput, ...]) -> DemoHost:
    sessions = demo_sessions()
    auth = SyntheticAuthenticator()
    claims = tuple(sorted({a.case.claim.claim_id for a in approved}))
    tokens = {
        name: auth.issue(
            ApiAccess(
                ApiScope(principal=session.principal, claim_ids=claims),
                session if session.principal.kind == PrincipalKind.HUMAN else None,
            )
        )
        for name, session in sessions.items()
    }
    authority = Authority(
        auth,
        sessions["host"].principal,
        tuple(s for s in sessions.values() if s.principal.kind == PrincipalKind.HUMAN),
        approved,
    )
    return DemoHost(authority, auth, tokens)


def command(
    action: Action,
    name: str,
    approval: ApprovedInput,
    state: StoredCase | None = None,
    *,
    actor: str = "reviewer",
    decision_action: DecisionAction = DecisionAction.APPROVE,
    outcome: AssessmentOutcome | None = AssessmentOutcome.ELIGIBLE,
) -> Command:
    sessions = demo_sessions()
    fields: dict[str, object] = {}
    if action in {Action.REGISTER, Action.PUBLISH, Action.REVALIDATE}:
        fields["approval_id"] = approval.approval_id
    elif action == Action.ASSIGN:
        fields["assignee_id"] = sessions[actor].principal.principal_id
    elif action == Action.DECIDE:
        assert state is not None and state.case.assessment is not None
        role = sessions[actor].principal.role
        assert role is not None
        fields["decision"] = ReviewerDecision(
            claim_id=state.case.claim.claim_id,
            assessment_id=state.case.assessment.assessment_id,
            expected_case_revision=state.case.revision,
            reviewer_id=sessions[actor].principal.principal_id,
            role=role,
            action=decision_action,
            outcome=outcome,
            reason="Explicit synthetic human action; no actual insurance or settlement authority.",
            evidence_ids=state.case.assessment.evidence_ids,
            decided_at=NOW,
        )
    return Command.model_validate(
        dict(
            request_id=uuid5(NS, name),
            correlation_id=uuid5(NS, "m20-demo"),
            claim_id=approval.case.claim.claim_id,
            action=action,
            occurred_at=NOW,
            rationale=(
                "Explicit synthetic human action; no actual insurance or settlement authority."
            ),
            expected=state.binding if state else None,
            **fields,
        )
    )


def prepared_store(
    path: Path, approval: ApprovedInput, host: DemoHost | None = None
) -> tuple[OutcomeStore, DemoHost, StoredCase]:
    host = host or demo_host((approval,))
    store = OutcomeStore(path, host.authority, create=True, clock=lambda: NOW + timedelta(days=1))
    state = None
    for action, name, actor in (
        (Action.REGISTER, "register", "host"),
        (Action.PUBLISH, "publish", "host"),
        (Action.ASSIGN, "assign-reviewer", "reviewer"),
        (Action.ASSIGN, "assign-supervisor", "supervisor"),
    ):
        event = store.execute(
            host.tokens["host"],
            command(action, name, approval, state, actor=actor),
            permit=host.authority.permit,
        )
        state = event.after
    assert state is not None
    return store, host, state
