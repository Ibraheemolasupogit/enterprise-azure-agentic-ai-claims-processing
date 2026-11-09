"""Reproducible synthetic human actions over one genuinely executed M12 advisory."""

import argparse
import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid5

from claims_ai.agent_tools.contracts import ToolGrant
from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.contracts import (
    AssignmentRequest,
    DecisionReason,
    InvalidationRequest,
    Principal,
    PrincipalKind,
    QueueEntry,
    ReviewAction,
    ReviewBinding,
    ReviewCode,
    ReviewDecision,
    ReviewError,
    ReviewSession,
    ReviewState,
)
from claims_ai.human_review.service import ReviewQueue
from claims_ai.models import DocumentKind, ReviewerRole
from claims_ai.workflow.__main__ import demo_grant, demo_request
from claims_ai.workflow.contracts import Checkpoint, WorkflowRequest
from claims_ai.workflow.engine import WorkflowRunner

NAMESPACE = UUID("15151515-1515-4515-8515-151515151515")
NOW = datetime(2027, 2, 2, tzinfo=UTC)


def demo_sessions() -> dict[str, ReviewSession]:
    return {
        name: ReviewSession(Principal(principal_id=uuid5(NAMESPACE, name), kind=kind, role=role))
        for name, kind, role in (
            ("host", PrincipalKind.HOST, None),
            ("reviewer", PrincipalKind.HUMAN, ReviewerRole.REVIEWER),
            ("supervisor", PrincipalKind.HUMAN, ReviewerRole.SUPERVISOR),
            ("outsider", PrincipalKind.HUMAN, ReviewerRole.REVIEWER),
            ("agent", PrincipalKind.AGENT, None),
            ("mcp", PrincipalKind.MCP, None),
            ("model", PrincipalKind.MODEL, None),
        )
    }


def demo_decision(entry: QueueEntry, action: ReviewAction, name: str) -> ReviewDecision:
    reasons = {
        ReviewAction.APPROVE: DecisionReason.SUPPORTED,
        ReviewAction.REJECT: DecisionReason.UNSUPPORTED,
        ReviewAction.REQUEST_EVIDENCE: DecisionReason.EVIDENCE,
        ReviewAction.ESCALATE: DecisionReason.SUPERVISOR,
    }
    return ReviewDecision(
        action_id=uuid5(NAMESPACE, name),
        entry_id=entry.entry_id,
        expected_review_revision=entry.review_revision,
        expected=entry.binding,
        action=action,
        reason=reasons[action],
        rationale="Synthetic human reviewed source-linked advisory; no insurance outcome.",
        evidence=(entry.evidence[0],),
        requested_evidence=(DocumentKind.REPAIR_ESTIMATE,)
        if action == ReviewAction.REQUEST_EVIDENCE
        else (),
        occurred_at=NOW + timedelta(seconds=10),
    )


async def demo_queue(
    request: WorkflowRequest,
    grant: ToolGrant,
    checkpoint: Checkpoint,
    sessions: dict[str, ReviewSession],
) -> tuple[ReviewQueue, QueueEntry]:
    queue = ReviewQueue(tuple(sessions.values()), clock=lambda: NOW + timedelta(hours=1))
    entry = await queue.enqueue(sessions["host"], request, grant, checkpoint, occurred_at=NOW)
    for index, name in enumerate(("reviewer", "supervisor"), start=1):
        queue.assign(
            sessions["host"],
            AssignmentRequest(
                request_id=uuid5(NAMESPACE, name + "/assignment"),
                entry_id=entry.entry_id,
                claim_id=entry.binding.claim_id,
                expected_review_revision=entry.review_revision,
                assignee_id=sessions[name].principal.principal_id,
                occurred_at=NOW + timedelta(seconds=index),
                rationale="Synthetic case-specific assignment by trusted host.",
            ),
        )
        entry = queue.details.get(sessions[name], entry.entry_id).entry
    return queue, entry


async def offline_report(root: Path) -> dict[str, object]:
    request = demo_request(root, "valid-v1", "m15-advisory")
    grant = demo_grant(request)
    checkpoint = await WorkflowRunner().run(request, grant)
    sessions = demo_sessions()
    cases = []
    for name in (
        "approve",
        "reject",
        "escalate",
        "request-evidence",
        "stale-evidence",
        "unauthorized",
    ):
        queue, entry = await demo_queue(request, grant, checkpoint, sessions)
        error_code = None
        if name == "stale-evidence":
            decision = demo_decision(entry, ReviewAction.APPROVE, name)
            queue.invalidate(
                sessions["host"],
                InvalidationRequest(
                    request_id=uuid5(NAMESPACE, "changed-evidence"),
                    entry_id=entry.entry_id,
                    expected_review_revision=entry.review_revision,
                    replacement=ReviewBinding.model_validate(
                        {**entry.binding.model_dump(), "evidence_sha256": "f" * 64}
                    ),
                    occurred_at=NOW + timedelta(seconds=5),
                    rationale="Host reports replacement evidence; reprocessing is required.",
                ),
            )
            try:
                queue.decide(sessions["reviewer"], decision)
            except ReviewError as error:
                error_code = error.code
            if error_code != ReviewCode.STALE:
                raise ValueError("stale evidence did not reject review")
        elif name == "unauthorized":
            try:
                queue.details.get(sessions["outsider"], entry.entry_id)
            except ReviewError as error:
                error_code = error.code
            if error_code != ReviewCode.DENIED:
                raise ValueError("unassigned caller obtained review access")
        else:
            action = {
                "approve": ReviewAction.APPROVE,
                "reject": ReviewAction.REJECT,
                "escalate": ReviewAction.ESCALATE,
                "request-evidence": ReviewAction.REQUEST_EVIDENCE,
            }[name]
            decision = demo_decision(entry, action, name)
            event = queue.decide(sessions["reviewer"], decision)
            if queue.decide(sessions["reviewer"], decision) != event:
                raise ValueError("duplicate review action did not return its immutable receipt")
            if name == "escalate":
                entry = queue.details.get(sessions["supervisor"], entry.entry_id).entry
                queue.decide(
                    sessions["supervisor"], demo_decision(entry, ReviewAction.APPROVE, "supervised")
                )
        detail = queue.details.get(sessions["reviewer"], entry.entry_id)
        if detail.current_case.decision is not None or detail.current_case.assessment is not None:
            raise ValueError("advisory review acquired insurance outcome authority")
        expected_state = {
            "approve": ReviewState.APPROVED,
            "reject": ReviewState.REJECTED,
            "escalate": ReviewState.APPROVED,
            "request-evidence": ReviewState.EVIDENCE,
            "stale-evidence": ReviewState.STALE,
            "unauthorized": ReviewState.REVIEW,
        }[name]
        if detail.entry.state != expected_state:
            raise ValueError("unexpected offline review state")
        cases.append(
            {
                "scenario": name,
                "error_code": error_code,
                "detail": detail.model_dump(mode="json"),
            }
        )
    return {
        "report_version": "offline-human-review-v1",
        "identity_and_clock": "HOST_ASSERTED_SYNTHETIC_NOT_AUTHENTICATION",
        "storage": "BOUNDED_SINGLE_PROCESS_MEMORY_NOT_DURABLE",
        "upstream_model_execution": "SIMULATED_M12_ADVISORY_PREPARATION",
        "review_model_calls": 0,
        "live_model_calls": 0,
        "autonomous_outcomes": 0,
        "azure_operations": 0,
        "insurance_outcome_authority": False,
        "human_approval_required": True,
        "processor_sha256": sha256(
            b"".join(
                p.name.encode() + b"\0" + p.read_bytes()
                for p in sorted(Path(__file__).parent.glob("*.py"))
            )
        ).hexdigest(),
        "cases": cases,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic human recommendation review only")
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root, output = args.spec_root.resolve(), args.output.resolve()
        protected = [root, Path("data").resolve(), *(p for p in root.parents if p.name == "data")]
        if any(output.is_relative_to(path) for path in protected) or output.exists():
            raise ValueError("output cannot replace evidence or a previous report")
        report = asyncio.run(offline_report(root))
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(json_bytes(report))
    except Exception as error:
        parser.exit(1, f"Offline review failed ({type(error).__name__}); raw payload omitted.\n")
    print("Synthetic human recommendation review recorded; no insurance outcome or cloud call.")


if __name__ == "__main__":
    main()
