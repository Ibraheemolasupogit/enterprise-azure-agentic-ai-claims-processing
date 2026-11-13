"""Fresh-process audit/replay probe. Private stdin holds host context; output is metadata only."""

import json
import os
import signal
import sys
from pathlib import Path
from uuid import UUID

from claims_ai.outcomes.contracts import ApprovedInput, Command, OutcomeError
from claims_ai.outcomes.demo import NOW, demo_host
from claims_ai.outcomes.store import OutcomeStore, decode
from claims_ai.quality_ops.operational_authority import EPOCH, bind_current
from claims_ai.quality_ops.telemetry import LocalSink, Telemetry
from claims_ai.rules.specification import digest
from claims_ai.security_hardening.contracts import Anchor, Grant
from claims_ai.security_hardening.lifecycle import Lifecycle


def main() -> None:
    try:
        raw = sys.stdin.buffer.read(12582913)
        if len(raw) > 12582912:
            raise ValueError("probe capacity")
        data = json.loads(raw)
        approval = decode(ApprovedInput, data["approval"])
        request = decode(Command, data["command"])
        if data["fault"] not in {"none", "before_commit", "after_commit"}:
            raise ValueError("unsupported probe fault")
        lifecycle = Lifecycle(
            Path(data["lifecycle"]),
            context_sha256=data["context"],
            integrity_key=bytes.fromhex(data["integrity_key"]),
            anchor=Anchor.model_validate(data["anchor"]),
            clock=lambda: EPOCH,
        )
        host = demo_host((approval,))
        bind_current(
            host, lifecycle, {n: Grant.model_validate(g) for n, g in data["grants"].items()}
        )
        sink = LocalSink()
        sink.fail = data["telemetry_fail"] is True
        telemetry = Telemetry(sink=sink)

        def fault(point: str) -> None:
            if point == data["fault"]:
                os.kill(os.getpid(), signal.SIGKILL)

        store = OutcomeStore(Path(data["database"]), host.authority, clock=lambda: NOW, fault=fault)
        allowed = True
        event_hash = None
        with telemetry.boundary("recovery", UUID(data["correlation"]), parent=data["carrier"]):
            try:
                event_hash = store.execute(host.tokens["reviewer"], request).event_sha256
            except OutcomeError as error:
                if str(error) != "access_denied":
                    raise
                allowed = False
            state = store.read(host.tokens["host"], request.claim_id)
            with store.transaction() as connection:
                _, events = store.verify(connection)
                decisions = connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]
                outbox_dead = connection.execute(
                    "SELECT COUNT(*) FROM outbox WHERE status='dead'"
                ).fetchone()[0]
                outbox_attempts = connection.execute("SELECT MAX(attempts) FROM outbox").fetchone()[
                    0
                ]
        output = {
            "allowed": allowed,
            "event_sha256": event_hash,
            "state_sha256": digest(state.model_dump(mode="json")),
            "decisions": decisions,
            "audit_events": len(events[request.claim_id]),
            "outbox_dead": outbox_dead,
            "outbox_attempts": outbox_attempts,
            "telemetry": telemetry.raw(),
        }
        telemetry.close()
        content = json.dumps(output, sort_keys=True)
        if len(content) > 65536:
            raise ValueError("probe response capacity")
        print(content)
    except Exception:
        raise SystemExit(3) from None


if __name__ == "__main__":
    main()
