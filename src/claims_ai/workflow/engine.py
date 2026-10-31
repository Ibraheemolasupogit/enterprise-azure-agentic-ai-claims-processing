"""Single-process orchestration, bounded retries and validated caller-held checkpoint replay."""

import asyncio
import platform
import time
from hashlib import sha256
from importlib.metadata import version
from pathlib import Path

from claims_ai.agent_tools.contracts import ALLOWLIST, ToolGrant
from claims_ai.dataset.generator import json_bytes
from claims_ai.rules.specification import digest
from claims_ai.workflow.contracts import (
    Checkpoint,
    Code,
    Snapshot,
    Stage,
    StageRecord,
    State,
    Step,
    WorkflowLimits,
    WorkflowRequest,
)
from claims_ai.workflow.stages import (
    Context,
    LocalStages,
    agent_step,
    blocked,
    changed,
    review_task,
)


def code_fingerprint() -> str:
    root = Path(__file__).resolve().parents[1]
    return sha256(
        b"".join(
            str(p.relative_to(root)).encode() + b"\x00" + p.read_bytes()
            for p in sorted(root.rglob("*.py"))
        )
    ).hexdigest()


def execution_key(request: WorkflowRequest, grant: ToolGrant, limits: WorkflowLimits) -> str:
    contents = [b.request.content for b in request.evidence_inputs]
    if sum(map(len, contents)) > 8388608:
        raise ValueError("offline workflow input capacity exceeded")
    # ProcessingRequest excludes content from model dumps; hash actual bytes explicitly.
    return digest(
        {
            "version": "offline-claims-v1",
            "code": code_fingerprint(),
            "python": platform.python_version(),
            "pydantic": version("pydantic"),
            "framework": version("agent-framework-core"),
            "request": request.model_dump(mode="json"),
            "content_sha256": [sha256(content).hexdigest() for content in contents],
            "grant": grant.model_dump(mode="json"),
            "limits": limits.model_dump(mode="json"),
        }
    )


def authorized(request: WorkflowRequest, grant: ToolGrant) -> bool:
    return (
        grant.claim_id == request.intake.claim.claim_id
        and grant.case_sha256 == digest(request.intake.model_dump(mode="json"))
        and set(grant.permissions) == set(ALLOWLIST)
    )


async def verify_step(stage: Stage, context: Context, before: Snapshot, step: Step) -> None:
    step = Step.model_validate(step)
    if step.outcome == "retryable":
        expected_snapshot = before
        if step.state == State.FAILED:
            if step.code is None:
                raise ValueError("failed retry needs a reason")
            expected_snapshot = changed(before, review_task=review_task(context, before, step.code))
        if step.snapshot != expected_snapshot:
            raise ValueError("technical failures cannot advance processing data")
        if step.agent_attempt is not None:
            if stage != Stage.AGENT:
                raise ValueError("only agent stages carry SDK attempt records")
            expected = agent_step(context, before, step.agent_attempt)
            if expected.outcome != step.outcome or expected.code != step.code:
                raise ValueError("invalid agent failure record")
        return
    if step.outcome == "blocked" and step.code == Code.INVALID:
        expected = blocked(context, before, Code.INVALID, State.FAILED)
    elif step.outcome == "blocked" and step.code == Code.DENIED:
        if stage != Stage.INTAKE or authorized(context.request, context.grant):
            raise ValueError("invalid denial checkpoint")
        expected = blocked(context, before, Code.DENIED, State.REJECTED)
    elif stage == Stage.AGENT:
        if step.agent_attempt is None:
            raise ValueError("agent stage must retain its typed attempt result")
        expected = agent_step(context, before, step.agent_attempt)
    else:
        # Pure replay independently rejects forged stage outputs, even after rehashing.
        expected = await LocalStages().run(stage, context, before)
    if step != expected:
        raise ValueError("stage output does not match verified prerequisites")


async def restore(request: WorkflowRequest, context: Context, checkpoint: Checkpoint) -> Checkpoint:
    if not authorized(request, context.grant):
        raise ValueError("checkpoint replay requires case authorization")
    checkpoint = Checkpoint.model_validate(checkpoint)
    if len(json_bytes(checkpoint.model_dump(mode="json"))) > context.limits.max_checkpoint_bytes:
        raise ValueError("checkpoint capacity exceeded")
    if (
        checkpoint.execution_key != context.execution_key
        or checkpoint.correlation_id != context.grant.correlation_id
        or checkpoint.max_attempts != context.limits.max_attempts
        or checkpoint.initial != Snapshot(case=request.intake)
    ):
        raise ValueError("checkpoint belongs to different inputs, code, configuration or caller")
    before = checkpoint.initial
    for record in checkpoint.records:
        await verify_step(record.stage, context, before, record.step)
        before = record.step.snapshot
    return checkpoint


def append(
    checkpoint: Checkpoint, context: Context, stage: Stage, attempt: int, step: Step
) -> Checkpoint:
    if step.outcome == "retryable":
        exhausted = attempt == context.limits.max_attempts
        snapshot = step.snapshot
        if exhausted:
            if step.code is None:
                raise ValueError("failed retry needs a reason")
            snapshot = changed(snapshot, review_task=review_task(context, snapshot, step.code))
        step = Step.model_validate(
            {
                **step.model_dump(),
                "snapshot": snapshot,
                "state": State.FAILED if exhausted else State.PAUSED,
            }
        )
    payload = {
        "schema_version": "1.0",
        "synthetic": True,
        "sequence": len(checkpoint.records) + 1,
        "stage": stage.value,
        "attempt": attempt,
        "correlation_id": str(context.grant.correlation_id),
        "input_sha256": digest(checkpoint.snapshot.model_dump(mode="json")),
        "output_sha256": digest(step.snapshot.model_dump(mode="json")),
        "previous_sha256": checkpoint.records[-1].record_sha256
        if checkpoint.records
        else checkpoint.execution_key,
        "step": step.model_dump(mode="json"),
    }
    record = StageRecord.model_validate({**payload, "record_sha256": digest(payload)})
    return Checkpoint.model_validate(
        {
            **checkpoint.model_dump(),
            "records": (*checkpoint.records, record),
            "state": step.state,
        }
    )


class WorkflowRunner:
    """Bounded in-memory journal; repeated same-key calls reuse verified checkpoints.

    This is not durable storage, distributed locking, authentication or exactly-once delivery.
    A new runner can resume a caller-retained checkpoint after revalidating deterministic data.
    """

    def __init__(
        self, *, limits: WorkflowLimits | None = None, services: LocalStages | None = None
    ) -> None:
        self.limits = WorkflowLimits.model_validate(limits or WorkflowLimits())
        self.services = services or LocalStages()
        self._journal: dict[str, Checkpoint] = {}
        self._lock = asyncio.Lock()

    async def run(
        self,
        request: WorkflowRequest,
        grant: ToolGrant,
        *,
        checkpoint: Checkpoint | None = None,
        stop_after: Stage | None = None,
        pause_on_retry: bool = False,
    ) -> Checkpoint:
        async with self._lock:
            started_run = time.monotonic()
            request, grant = (
                WorkflowRequest.model_validate(request),
                ToolGrant.model_validate(grant),
            )
            key = execution_key(request, grant, self.limits)
            context = Context(request, grant, key, self.limits)
            if not authorized(request, grant):
                initial = Checkpoint(
                    execution_key=key,
                    correlation_id=grant.correlation_id,
                    max_attempts=self.limits.max_attempts,
                    initial=Snapshot(case=request.intake),
                )
                return append(
                    initial,
                    context,
                    Stage.INTAKE,
                    1,
                    blocked(context, initial.snapshot, Code.DENIED, State.REJECTED),
                )
            existing = self._journal.get(key)
            if existing is None and len(self._journal) >= 32:
                raise ValueError("offline journal capacity exceeded")
            if checkpoint is not None:
                checkpoint = await restore(request, context, checkpoint)
                if existing and existing.records[: len(checkpoint.records)] != checkpoint.records:
                    raise ValueError("checkpoint conflicts with the current journal")
            current = (
                existing
                or checkpoint
                or Checkpoint(
                    execution_key=key,
                    correlation_id=grant.correlation_id,
                    max_attempts=self.limits.max_attempts,
                    initial=Snapshot(case=request.intake),
                )
            )
            if existing is not None:
                await restore(request, context, existing)
            deadline = started_run + self.limits.run_timeout_seconds
            while current.next_stage is not None:
                stage = current.next_stage
                last = current.records[-1] if current.records else None
                attempt = last.attempt + 1 if last and last.stage == stage else 1
                before = current.snapshot
                cancelled = False
                try:
                    if not authorized(request, grant):
                        step = blocked(context, before, Code.DENIED, State.REJECTED)
                    else:
                        remaining = min(
                            deadline - time.monotonic(), self.limits.stage_timeout_seconds
                        )
                        if remaining <= 0:
                            raise TimeoutError("workflow deadline")
                        started = time.monotonic()
                        async with asyncio.timeout(remaining):
                            step = await self.services.run(stage, context, before)
                            await verify_step(stage, context, before, step)
                        if time.monotonic() - started >= remaining:
                            raise TimeoutError("cooperative stage deadline")
                except asyncio.CancelledError:
                    cancelled = True
                    step = Step(snapshot=before, outcome="retryable", code=Code.CANCELLED)
                except TimeoutError:
                    step = Step(snapshot=before, outcome="retryable", code=Code.TIMEOUT)
                except OSError:
                    step = Step(snapshot=before, outcome="retryable", code=Code.DEPENDENCY)
                except Exception:
                    step = blocked(context, before, Code.INVALID, State.FAILED)
                updated = append(current, context, stage, attempt, step)
                if (
                    len(json_bytes(updated.model_dump(mode="json")))
                    > self.limits.max_checkpoint_bytes
                ):
                    raise ValueError("checkpoint capacity exceeded; previous checkpoint retained")
                self._journal[key] = current = updated
                if cancelled:
                    raise asyncio.CancelledError
                if stop_after == stage or (pause_on_retry and step.outcome == "retryable"):
                    break
            return current
