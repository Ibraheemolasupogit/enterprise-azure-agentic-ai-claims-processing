"""Offline integration, stage safety, bounded failures and checkpoint recovery."""

import asyncio
import json
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from claims_ai.agent_tools.contracts import PolicyData, ToolGrant
from claims_ai.agent_tools.execution import Mode
from claims_ai.agent_tools.tools import LocalReadServices
from claims_ai.agents.contracts import AssessmentInput
from claims_ai.models import Case, CaseState
from claims_ai.rules.contracts import EvidenceInput
from claims_ai.rules.specification import digest
from claims_ai.workflow.__main__ import demo_grant, demo_request, injected_document
from claims_ai.workflow.contracts import (
    STAGES,
    Checkpoint,
    Code,
    Snapshot,
    Stage,
    State,
    Step,
    WorkflowLimits,
    WorkflowRequest,
)
from claims_ai.workflow.engine import WorkflowRunner
from claims_ai.workflow.stages import Context, LocalStages, changed

ROOT = Path(__file__).resolve().parents[1]
SPEC_ROOT = ROOT / "data/rules/motor/v1"


@pytest.fixture(scope="module")
def request_value() -> WorkflowRequest:
    return demo_request(SPEC_ROOT, "valid-v1", "workflow-test")


class ObservedStages(LocalStages):
    def __init__(self, *, failing: Stage | None = None, once: bool = False) -> None:
        super().__init__()
        self.calls: list[Stage] = []
        self.failing, self.once = failing, once

    async def run(self, stage: Stage, context: Context, snapshot: Snapshot) -> Step:
        self.calls.append(stage)
        if stage == self.failing and (not self.once or self.calls.count(stage) == 1):
            raise OSError("SYNTHETIC_PRIVATE_BACKEND_TRACE")
        return await super().run(stage, context, snapshot)


def modified(value: WorkflowRequest, **changes: object) -> WorkflowRequest:
    return WorkflowRequest.model_validate(
        {
            **value.model_dump(exclude={"evidence_inputs"}),
            "evidence_inputs": value.evidence_inputs,
            **changes,
        }
    )


@pytest.fixture(scope="module")
def complete(request_value: WorkflowRequest) -> Checkpoint:
    return asyncio.run(WorkflowRunner().run(request_value, demo_grant(request_value)))


def rehash(raw: dict[str, Any]) -> Checkpoint:
    """Adversary can recompute unsigned hashes; provenance replay must still reject edits."""
    previous = raw["execution_key"]
    before = raw["initial"]
    for record in raw["records"]:
        record["previous_sha256"] = previous
        record["input_sha256"] = digest(before)
        record["output_sha256"] = digest(record["step"]["snapshot"])
        record["record_sha256"] = digest({k: v for k, v in record.items() if k != "record_sha256"})
        previous, before = record["record_sha256"], record["step"]["snapshot"]
    return Checkpoint.model_validate(raw)


def test_stage_order_and_actual_m11_framework_execution(
    request_value: WorkflowRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    def no_network(*args: object, **kwargs: object) -> None:
        raise AssertionError("network is outside M12")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    before = request_value.model_dump_json()
    services = ObservedStages()
    result = asyncio.run(
        WorkflowRunner(services=services).run(request_value, demo_grant(request_value))
    )
    assert services.calls == list(STAGES)
    assert [record.stage for record in result.records] == list(STAGES)
    assert result.state == State.REVIEW and result.next_stage is None
    agent = result.snapshot.agent_result
    assert agent is not None and agent.framework_executed and agent.model_calls == 4
    assert len(agent.receipts) == 3 and all(r.status == "ok" for r in agent.receipts)
    assert result.snapshot.case.state == CaseState.ASSESSING
    assert result.snapshot.case.assessment is None and result.snapshot.case.decision is None
    assert result.snapshot.review_task is not None
    assert result.snapshot.review_task.human_approval_required
    assert result.final_outcome is None and not result.settlement_authorized
    assert all(record.correlation_id == result.correlation_id for record in result.records)
    assert request_value.model_dump_json() == before


def test_existing_lifecycle_and_admission_records_form_one_exact_chain(
    complete: Checkpoint,
) -> None:
    snapshot = complete.snapshot
    transitions = snapshot.transitions
    assert [event.current.state for event in transitions] == [
        CaseState.VALIDATING,
        CaseState.EXTRACTING,
        CaseState.ASSESSING,
    ]
    case = transitions[1].current
    for admission in snapshot.admissions:
        assert admission.previous == case
        case = admission.current
    assert transitions[2].previous == case and transitions[2].current == snapshot.case
    assert snapshot.history is not None
    assert len(snapshot.history.records) == len(snapshot.case.evidence)
    with pytest.raises(ValidationError):
        complete.state = State.READY  # type: ignore[misc]


def test_duplicate_and_concurrent_execution_does_not_repeat_the_agent(
    request_value: WorkflowRequest,
) -> None:
    services = ObservedStages()
    runner = WorkflowRunner(services=services)

    async def run() -> None:
        results = await asyncio.gather(
            *(runner.run(request_value, demo_grant(request_value)) for _ in range(3))
        )
        assert results[0] == results[1] == results[2]
        assert services.calls == list(STAGES)

    asyncio.run(run())


@pytest.mark.parametrize(
    "stage", [Stage.INTAKE, Stage.EVIDENCE, Stage.POLICY, Stage.RULES, Stage.AGENT]
)
def test_partial_checkpoint_roundtrip_matches_uninterrupted_processing(
    request_value: WorkflowRequest, complete: Checkpoint, stage: Stage
) -> None:
    partial = asyncio.run(
        WorkflowRunner().run(request_value, demo_grant(request_value), stop_after=stage)
    )
    assert partial.state == State.PAUSED
    loaded = Checkpoint.model_validate_json(partial.model_dump_json())
    services = ObservedStages()
    resumed = asyncio.run(
        WorkflowRunner(services=services).run(
            request_value, demo_grant(request_value), checkpoint=loaded
        )
    )
    assert resumed == complete
    assert services.calls == list(STAGES[STAGES.index(stage) + 1 :])


def test_failed_attempt_is_resumable_without_resetting_retry_history(
    request_value: WorkflowRequest,
) -> None:
    services = ObservedStages(failing=Stage.POLICY, once=True)
    first = asyncio.run(
        WorkflowRunner(services=services).run(
            request_value, demo_grant(request_value), pause_on_retry=True
        )
    )
    assert first.state == State.PAUSED and first.next_stage == Stage.POLICY
    assert first.records[-1].attempt == 1 and first.records[-1].step.code == Code.DEPENDENCY
    later_services = ObservedStages()
    resumed = asyncio.run(
        WorkflowRunner(services=later_services).run(
            request_value,
            demo_grant(request_value),
            checkpoint=Checkpoint.model_validate_json(first.model_dump_json()),
        )
    )
    assert resumed.state == State.REVIEW
    assert [r.attempt for r in resumed.records if r.stage == Stage.POLICY] == [1, 2]
    assert later_services.calls == list(STAGES[2:])
    assert resumed.records[: len(first.records)] == first.records


@pytest.mark.parametrize("stage", [Stage.EVIDENCE, Stage.POLICY, Stage.AGENT])
def test_exhausted_retries_are_terminal_and_do_not_reset_on_replay(
    request_value: WorkflowRequest, stage: Stage, caplog: pytest.LogCaptureFixture
) -> None:
    services = ObservedStages(failing=stage)
    runner = WorkflowRunner(services=services)
    result = asyncio.run(runner.run(request_value, demo_grant(request_value)))
    assert result.state == State.FAILED and result.next_stage is None
    assert result.snapshot.review_task is not None
    assert result.snapshot.review_task.required_reviewer == "supervisor"
    assert services.calls.count(stage) == 2
    calls = tuple(services.calls)
    assert asyncio.run(runner.run(request_value, demo_grant(request_value))) == result
    assert tuple(services.calls) == calls
    assert "SYNTHETIC_PRIVATE_BACKEND_TRACE" not in result.model_dump_json() + caplog.text


@pytest.mark.parametrize("fault", ["claim", "snapshot", "permissions"])
def test_authorization_precedes_checkpoint_replay_and_service_reads(
    request_value: WorkflowRequest,
    complete: Checkpoint,
    fault: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = demo_grant(request_value).model_dump()
    changes: dict[str, dict[str, object]] = {
        "claim": {"claim_id": "NS-CLM-00000000"},
        "snapshot": {"case_sha256": "0" * 64},
        "permissions": {"permissions": ()},
    }
    raw.update(changes[fault])
    grant = ToolGrant.model_validate(raw)

    async def forbidden(*args: object, **kwargs: object) -> Step:
        raise AssertionError("unauthorized replay must not read services")

    monkeypatch.setattr(LocalStages, "run", forbidden)
    result = asyncio.run(WorkflowRunner().run(request_value, grant, checkpoint=complete))
    assert result.state == State.REJECTED and result.records[0].step.code == Code.DENIED
    assert result.snapshot.agent_result is None and len(result.records) == 1


@pytest.mark.parametrize(
    "fixture,expected",
    [
        ("missing-estimate", State.EVIDENCE),
        ("contradictory-loss", State.QUARANTINED),
        ("quarantined-documents", State.QUARANTINED),
        ("unverified-extraction", State.QUARANTINED),
        ("conflicting-amounts", State.ABSTAINED),
        ("simulation-not-authorized", State.REJECTED),
    ],
)
def test_missing_conflicting_or_untrusted_evidence_never_reaches_agent(
    fixture: str, expected: State
) -> None:
    value = demo_request(SPEC_ROOT, fixture, fixture)
    services = ObservedStages()
    result = asyncio.run(WorkflowRunner(services=services).run(value, demo_grant(value)))
    assert result.state == expected and Stage.AGENT not in services.calls
    assert (
        result.snapshot.review_task is not None
        and result.snapshot.review_task.required_reviewer == "supervisor"
    )
    assert result.snapshot.case.assessment is None


@pytest.mark.parametrize("version", [None, "missing-version"])
def test_exact_policy_version_never_falls_back(
    request_value: WorkflowRequest, version: str | None
) -> None:
    value = modified(request_value, policy_version=version)
    result = asyncio.run(WorkflowRunner().run(value, demo_grant(value)))
    assert result.state == State.ABSTAINED and result.records[-1].stage == Stage.POLICY
    assert result.snapshot.rule_evaluation is None and result.snapshot.agent_result is None


@pytest.mark.parametrize("fixture", ["expired", "wrong-version-at-boundary"])
def test_incident_date_policy_boundaries_abstain(fixture: str) -> None:
    value = demo_request(SPEC_ROOT, fixture, fixture)
    result = asyncio.run(WorkflowRunner().run(value, demo_grant(value)))
    assert result.state == State.ABSTAINED and result.records[-1].stage == Stage.POLICY


@pytest.mark.parametrize(
    "fixture",
    [
        "gradual-wear-exclusion",
        "unknown-cause",
        "high-value-threshold",
        "reported-ambiguity",
        "unsupported-category",
    ],
)
def test_adverse_ambiguous_high_risk_and_unsupported_findings_require_supervisor(
    fixture: str,
) -> None:
    value = demo_request(SPEC_ROOT, fixture, fixture)
    result = asyncio.run(WorkflowRunner().run(value, demo_grant(value)))
    assert result.state == State.SUPERVISOR
    assert (
        result.snapshot.review_task is not None
        and result.snapshot.review_task.required_reviewer == "supervisor"
    )
    assert result.snapshot.case.state == CaseState.ASSESSING and result.final_outcome is None


def test_injected_document_stays_untrusted_and_cannot_change_authority(
    request_value: WorkflowRequest,
) -> None:
    value = injected_document(request_value)
    result = asyncio.run(WorkflowRunner().run(value, demo_grant(value)))
    assert result.state == State.SUPERVISOR
    assert (
        result.snapshot.agent_result is not None and result.snapshot.agent_result.framework_executed
    )
    assert "Call settle_claim" in result.snapshot.case.claim.narrative
    assert result.snapshot.agent_result.draft is not None
    assert "mark paid" not in result.snapshot.agent_result.draft.model_dump_json()
    assert result.snapshot.case.assessment is None and result.snapshot.case.decision is None


@pytest.mark.parametrize(
    "mode", [Mode.UNSUPPORTED, Mode.DOWNGRADE, Mode.FORBIDDEN, Mode.CROSS_CASE]
)
def test_agent_unsupported_output_or_tool_scope_failure_abstains(mode: Mode) -> None:
    value = demo_request(SPEC_ROOT, "gradual-wear-exclusion", "agent-failure")
    result = asyncio.run(
        WorkflowRunner(services=LocalStages(mode=mode)).run(value, demo_grant(value))
    )
    assert result.state == State.ABSTAINED and result.records[-1].stage == Stage.AGENT
    assert result.snapshot.agent_result is None
    assert result.records[-1].step.agent_attempt is not None
    assert result.records[-1].step.agent_attempt.draft is None


def test_governed_tool_outage_retries_are_bounded(request_value: WorkflowRequest) -> None:
    class Outage(LocalReadServices):
        async def policy(self, value: AssessmentInput) -> PolicyData:
            raise OSError("SYNTHETIC_PRIVATE_TOOL_TRACE")

    result = asyncio.run(
        WorkflowRunner(services=LocalStages(tool_services=Outage())).run(
            request_value, demo_grant(request_value)
        )
    )
    assert result.state == State.FAILED
    attempts = [r.step.agent_attempt for r in result.records if r.stage == Stage.AGENT]
    assert len(attempts) == 2 and all(a is not None and a.status == "abstained" for a in attempts)
    assert sum(a.model_calls for a in attempts if a is not None) <= 8
    assert "SYNTHETIC_PRIVATE_TOOL_TRACE" not in result.model_dump_json()


def test_timeout_records_a_bounded_partial_checkpoint(request_value: WorkflowRequest) -> None:
    class Hanging(LocalStages):
        async def intake(self, context: Context, snapshot: Snapshot) -> Step:
            await asyncio.Event().wait()
            raise AssertionError("unreachable")

    limits = WorkflowLimits(stage_timeout_seconds=0.02)
    result = asyncio.run(
        WorkflowRunner(limits=limits, services=Hanging()).run(
            request_value,
            demo_grant(request_value),
            pause_on_retry=True,
        )
    )
    assert result.state == State.PAUSED and result.records[-1].step.code == Code.TIMEOUT
    assert result.records[-1].stage == Stage.INTAKE and result.records[-1].attempt == 1
    assert result.snapshot == result.initial


def test_fake_stage_cannot_skip_evidence_or_invent_a_case_transition(
    request_value: WorkflowRequest,
) -> None:
    class Skipping(LocalStages):
        async def evidence(self, context: Context, snapshot: Snapshot) -> Step:
            case = Case.model_validate({**snapshot.case.model_dump(), "state": CaseState.ASSESSING})
            return Step(snapshot=changed(snapshot, case=case))

    result = asyncio.run(
        WorkflowRunner(services=Skipping()).run(request_value, demo_grant(request_value))
    )
    assert result.state == State.FAILED and result.records[-1].step.code == Code.INVALID
    assert result.snapshot.case.state == CaseState.EXTRACTING and not result.snapshot.case.evidence


@pytest.mark.parametrize("tamper", ["citation", "transition", "agent_conclusion"])
def test_rehashed_checkpoint_tampering_cannot_bypass_canonical_replay(
    request_value: WorkflowRequest, complete: Checkpoint, tamper: str
) -> None:
    raw = complete.model_dump(mode="json")
    if tamper == "citation":
        raw["records"][2]["step"]["snapshot"]["retrieval_response"]["hits"][0]["chunk"]["clause"][
            "citation"
        ]["policy_version"] = "forged-version"
    elif tamper == "transition":
        raw["records"][0]["step"]["snapshot"]["transitions"] = []
    else:
        raw["records"][4]["step"]["snapshot"]["agent_result"]["draft"]["findings"][0][
            "explanation"
        ] = "Claim approved for payment."
        raw["records"][4]["step"]["agent_attempt"]["draft"]["findings"][0]["explanation"] = (
            "Claim approved for payment."
        )
    forged = rehash(raw)
    with pytest.raises(ValueError, match="stage output|unsupported finding"):
        asyncio.run(
            WorkflowRunner().run(request_value, demo_grant(request_value), checkpoint=forged)
        )


@pytest.mark.parametrize("tamper", ["order", "attempt", "hash", "state"])
def test_checkpoint_structure_rejects_unsafe_history(complete: Checkpoint, tamper: str) -> None:
    raw = complete.model_dump(mode="json")
    if tamper == "order":
        raw["records"][0]["stage"] = "agent"
    elif tamper == "attempt":
        raw["records"][0]["attempt"] = 2
    elif tamper == "state":
        raw["state"] = "ready"
    else:
        raw["records"][0]["record_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        rehash(raw) if tamper != "hash" else Checkpoint.model_validate(raw)


def test_checkpoint_binds_actual_bytes_case_caller_and_configuration(
    request_value: WorkflowRequest, complete: Checkpoint
) -> None:
    first = request_value.evidence_inputs[0]
    processing = type(first.request).model_validate(
        {
            **first.request.model_dump(exclude={"case"}),
            "case": first.request.case,
            "content": first.request.content + b"tampered",
        }
    )
    changed_input = EvidenceInput(request=processing, response=first.response)
    altered = modified(
        request_value, evidence_inputs=(changed_input, *request_value.evidence_inputs[1:])
    )
    for value, grant, limits in [
        (altered, demo_grant(altered), WorkflowLimits()),
        (
            request_value,
            ToolGrant.model_validate(
                {
                    **demo_grant(request_value).model_dump(),
                    "principal_id": "00000000-0000-0000-0000-000000000001",
                }
            ),
            WorkflowLimits(),
        ),
        (request_value, demo_grant(request_value), WorkflowLimits(max_attempts=1)),
    ]:
        with pytest.raises(ValueError, match="different inputs"):
            asyncio.run(WorkflowRunner(limits=limits).run(value, grant, checkpoint=complete))
    result = asyncio.run(WorkflowRunner().run(altered, demo_grant(altered)))
    assert result.state == State.QUARANTINED


def test_workflow_contracts_forbid_outcomes_and_retry_expansion(complete: Checkpoint) -> None:
    for key, unsafe in [
        ("final_outcome", "approved"),
        ("settlement_authorized", True),
        ("human_approval_required", False),
        ("max_attempts", 10),
    ]:
        with pytest.raises(ValueError):
            Checkpoint.model_validate({**complete.model_dump(), key: unsafe})


def test_cancellation_consumes_an_attempt_and_keeps_the_last_verified_snapshot(
    request_value: WorkflowRequest,
) -> None:
    async def run() -> None:
        entered = asyncio.Event()

        class Hanging(LocalStages):
            async def policy(self, context: Context, snapshot: Snapshot) -> Step:
                entered.set()
                await asyncio.Event().wait()
                raise AssertionError("unreachable")

        runner = WorkflowRunner(services=Hanging())
        task = asyncio.create_task(runner.run(request_value, demo_grant(request_value)))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        runner.services = ObservedStages()
        result = await runner.run(request_value, demo_grant(request_value))
        policy_records = [r for r in result.records if r.stage == Stage.POLICY]
        assert result.state == State.REVIEW and len(policy_records) == 2
        assert policy_records[0].step.code == Code.CANCELLED
        assert policy_records[1].attempt == 2

    asyncio.run(run())


def test_run_deadline_and_single_attempt_budget_are_explicit(
    request_value: WorkflowRequest,
) -> None:
    services = ObservedStages()
    limits = WorkflowLimits(run_timeout_seconds=0.000001, max_attempts=1)
    result = asyncio.run(
        WorkflowRunner(limits=limits, services=services).run(
            request_value,
            demo_grant(request_value),
        )
    )
    assert result.state == State.FAILED and len(result.records) == 1
    assert result.records[0].step.code == Code.TIMEOUT and not services.calls


def test_missing_extraction_and_duplicate_submissions_never_advance(
    request_value: WorkflowRequest,
) -> None:
    duplicate = modified(
        request_value,
        evidence_inputs=(*request_value.evidence_inputs, request_value.evidence_inputs[0]),
    )
    result = asyncio.run(WorkflowRunner().run(duplicate, demo_grant(duplicate)))
    assert result.state == State.REJECTED and len(result.records) == 1
    missing = modified(request_value, evidence_inputs=request_value.evidence_inputs[:-1])
    result = asyncio.run(WorkflowRunner().run(missing, demo_grant(missing)))
    assert result.state == State.EVIDENCE and result.records[-1].stage == Stage.EVIDENCE


def test_stale_reviewer_assertions_are_not_rebound_by_runtime(
    request_value: WorkflowRequest,
) -> None:
    from claims_ai.rules.contracts import ReviewedFacts

    stale = tuple(
        ReviewedFacts.model_validate({**f.model_dump(), "case_sha256": "0" * 64})
        for f in request_value.reviewed_facts
    )
    value = modified(request_value, reviewed_facts=stale)
    result = asyncio.run(WorkflowRunner().run(value, demo_grant(value)))
    assert result.state == State.SUPERVISOR
    assert value.reviewed_facts == stale
    assert result.snapshot.rule_evaluation is not None
    assert all(f.calculation is None for f in result.snapshot.rule_evaluation.findings)


def test_checkpoint_capacity_fails_without_publishing_oversized_state(
    request_value: WorkflowRequest,
) -> None:
    runner = WorkflowRunner(limits=WorkflowLimits(max_checkpoint_bytes=65536))
    with pytest.raises(ValueError, match="capacity"):
        asyncio.run(runner.run(request_value, demo_grant(request_value)))


def test_cli_reproduction_and_data_protection_from_other_cwd(tmp_path: Path) -> None:
    import claims_ai

    assert claims_ai.__file__ is not None
    package_root = Path(claims_ai.__file__).resolve().parents[1]
    bootstrap = (
        "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));"
        "runpy.run_module('claims_ai.workflow',run_name='__main__')"
    )
    command = [
        sys.executable,
        "-I",
        "-c",
        bootstrap,
        str(package_root),
        "--spec-root",
        str(SPEC_ROOT),
    ]
    outputs = [tmp_path / "a.json", tmp_path / "b.json"]
    for output in outputs:
        subprocess.run(
            [*command, "--output", str(output)], check=True, capture_output=True, cwd=tmp_path
        )
    assert outputs[0].read_bytes() == outputs[1].read_bytes()
    report = json.loads(outputs[0].read_bytes())
    assert (
        report["live_model_calls"]
        == report["autonomous_outcomes"]
        == report["operational_assessments"]
        == 0
    )
    assert report["framework_version"] == "1.23.0" and report["model_execution"] == "SIMULATED"
    assert [row["checkpoint"]["state"] for row in report["cases"]] == [
        State.REVIEW,
        State.EVIDENCE,
        State.FAILED,
        State.SUPERVISOR,
        State.SUPERVISOR,
        State.SUPERVISOR,
        State.REVIEW,
    ]
    for target in (
        outputs[0],
        SPEC_ROOT / "m12-must-not-write.json",
        ROOT / "data/synthetic/motor/v1/m12-must-not-write.json",
    ):
        assert (
            subprocess.run(
                [*command, "--output", str(target)], cwd=tmp_path, capture_output=True
            ).returncode
            != 0
        )
        if target not in outputs:
            assert not target.exists()
