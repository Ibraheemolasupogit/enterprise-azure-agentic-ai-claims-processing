"""Trusted offline subprocess test driver; never an authentication or public API."""

import argparse
import os
import signal
from hashlib import sha256
from pathlib import Path

from claims_ai.outcomes.contracts import ApprovedInput, Command
from claims_ai.outcomes.demo import NOW, demo_host
from claims_ai.outcomes.store import OutcomeStore, decode


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic M20 subprocess driver, local host only")
    parser.add_argument("--approval", type=Path, required=True)
    parser.add_argument("--approval-sha256", required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--command", type=Path, required=True)
    parser.add_argument(
        "--actor", choices=["host", "reviewer", "supervisor", "outsider"], required=True
    )
    parser.add_argument(
        "--fault",
        choices=[
            "none",
            "after_projection",
            "after_audit",
            "before_commit",
            "after_commit",
            "after_sink",
            "before_delivery_commit",
            "after_delivery_commit",
        ],
        default="none",
    )
    parser.add_argument("--dispatch", action="store_true")
    args = parser.parse_args()
    try:
        info = args.approval.stat(follow_symlinks=False)
        if (
            info.st_uid != os.geteuid()
            or info.st_mode & 0o077
            or info.st_nlink != 1
            or info.st_size > 12582912
        ):
            raise ValueError("private host approval required")
        raw = args.approval.read_bytes()
        if sha256(raw).hexdigest() != args.approval_sha256:
            raise ValueError("independent host approval mismatch")
        approval = decode(ApprovedInput, raw.decode())
        command = decode(Command, args.command.read_text())
        host = demo_host((approval,))

        def fault(point: str) -> None:
            if point == args.fault:
                os.kill(os.getpid(), signal.SIGKILL)

        store = OutcomeStore(args.database, host.authority, clock=lambda: NOW, fault=fault)
        if args.dispatch:
            from uuid import uuid5

            from claims_ai.outcomes.store import NS

            actor = host.authority.host
            event_id = uuid5(NS, f"{command.claim_id}/{actor.principal_id}/{command.request_id}")
            print(store.dispatch(host.tokens[args.actor], command.claim_id, event_id))
        else:
            result = store.execute(host.tokens[args.actor], command, permit=host.authority.permit)
            print(result.event_sha256)
    except Exception as failure:
        parser.exit(
            1, "Synthetic recovery failed (" + type(failure).__name__ + "); raw state omitted.\n"
        )


if __name__ == "__main__":
    main()
