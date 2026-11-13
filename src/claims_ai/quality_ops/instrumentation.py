"""Host-composed wrappers; existing services retain grants, retries and decision authority."""

import asyncio
from uuid import UUID

from claims_ai.agent_tools.contracts import EvidenceData, PolicyData, RuleData
from claims_ai.agent_tools.tools import LocalReadServices
from claims_ai.agents.contracts import AssessmentInput
from claims_ai.quality_ops.telemetry import Telemetry
from claims_ai.workflow.contracts import Snapshot, Stage, Step
from claims_ai.workflow.stages import Context, LocalStages


class ObservedReads(LocalReadServices):
    def __init__(self, telemetry: Telemetry, correlation: UUID) -> None:
        self.telemetry, self.correlation = telemetry, correlation

    async def evidence(self, value: AssessmentInput) -> EvidenceData:
        with self.telemetry.boundary("tool.evidence", self.correlation):
            return await super().evidence(value)

    async def policy(self, value: AssessmentInput) -> PolicyData:
        with self.telemetry.boundary("tool.policy", self.correlation):
            return await super().policy(value)

    async def rules(self, value: AssessmentInput) -> RuleData:
        with self.telemetry.boundary("tool.rules", self.correlation):
            return await super().rules(value)


class ObservedStages(LocalStages):
    def __init__(self, telemetry: Telemetry, correlation: UUID, *, fault: str = "none") -> None:
        if fault not in {"none", "outage", "timeout", "retry_once"}:
            raise ValueError("unsupported bounded fault")
        super().__init__(tool_services=ObservedReads(telemetry, correlation))
        self.telemetry, self.fault = telemetry, fault
        self.policy_attempts = 0

    async def run(self, stage: Stage, context: Context, snapshot: Snapshot) -> Step:
        with self.telemetry.boundary(stage.value, context.grant.correlation_id):
            if stage == Stage.POLICY:
                self.policy_attempts += 1
                if self.fault == "timeout":
                    # An actual bounded async deadline, without weakening M12's budgets.
                    await asyncio.wait_for(asyncio.sleep(1), timeout=0.01)
                if self.fault == "outage" or (
                    self.fault == "retry_once" and self.policy_attempts == 1
                ):
                    raise OSError("synthetic dependency unavailable")
            return await super().run(stage, context, snapshot)
