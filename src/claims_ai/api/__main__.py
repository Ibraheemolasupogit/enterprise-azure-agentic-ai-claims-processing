"""Reproducible TestClient API/OpenAPI evidence, without a socket or live cloud dependency."""

import argparse
from hashlib import sha256
from pathlib import Path
from typing import Any
from uuid import UUID, uuid5

import httpx2
from fastapi.openapi.models import OpenAPI
from fastapi.testclient import TestClient

from claims_ai.api.fixtures import demo_application
from claims_ai.dataset.generator import json_bytes
from claims_ai.human_review.__main__ import demo_decision
from claims_ai.human_review.contracts import QueueEntry, ReviewAction

NAMESPACE = UUID("16161616-1616-4616-8616-161616161616")


def offline_report(root: Path) -> tuple[dict[str, object], dict[str, Any]]:
    fixture = demo_application(root, fixtures=("valid-v1", "valid-v2"))
    cases: list[dict[str, object]] = []

    def headers(actor: str, name: str, **extra: str) -> dict[str, str]:
        return {
            "Authorization": "Bearer " + fixture.tokens[actor],
            "X-Correlation-ID": str(uuid5(NAMESPACE, name)),
            **extra,
        }

    def record(name: str, response: httpx2.Response, expected: int) -> dict[str, Any]:
        if response.status_code != expected:
            raise ValueError("unexpected offline API status")
        body: dict[str, Any] = response.json()
        cases.append(
            {
                "scenario": name,
                "status_code": response.status_code,
                "body": body,
                "etag": response.headers.get("etag"),
            }
        )
        return body

    with TestClient(
        fixture.app, base_url="http://127.0.0.1:8766", client=("127.0.0.1", 50000)
    ) as client:
        record(
            "local-readiness", client.get("/health/ready", headers=headers("host", "ready")), 200
        )
        bundle = fixture.bundles[0]
        claim_id = bundle.request.intake.claim.claim_id
        intake = {
            "bundle_id": bundle.bundle_id,
            "claim": bundle.request.intake.claim.model_dump(mode="json"),
        }
        intake_headers = headers(
            "host",
            "intake",
            **{
                "Idempotency-Key": str(uuid5(NAMESPACE, "intake")),
                "If-None-Match": "*",
            },
        )
        first = record(
            "intake", client.post("/api/v1/claims", headers=intake_headers, json=intake), 201
        )
        if (
            record(
                "duplicate-intake",
                client.post("/api/v1/claims", headers=intake_headers, json=intake),
                201,
            )
            != first
        ):
            raise ValueError("intake replay changed its receipt")
        process_body = {
            "expected_case_revision": first["case_revision"],
            "expected_case_sha256": first["case_sha256"],
        }
        process_headers = headers(
            "host",
            "process",
            **{
                "Idempotency-Key": str(uuid5(NAMESPACE, "process")),
                "If-Match": '"1"',
            },
        )
        process_path = f"/api/v1/claims/{claim_id}/process"
        processed = record(
            "processing", client.post(process_path, headers=process_headers, json=process_body), 200
        )
        if (
            record(
                "duplicate-processing",
                client.post(process_path, headers=process_headers, json=process_body),
                200,
            )
            != processed
        ):
            raise ValueError("processing replay changed its receipt")
        entry_id = processed["review_entry_id"]
        record(
            "review-queue",
            client.get("/api/v1/reviews?limit=1", headers=headers("reviewer", "queue")),
            200,
        )
        detail = record(
            "review-detail",
            client.get(f"/api/v1/reviews/{entry_id}", headers=headers("reviewer", "detail")),
            200,
        )
        record(
            "advisory",
            client.get(
                f"/api/v1/claims/{claim_id}/advisory", headers=headers("reviewer", "advisory")
            ),
            200,
        )
        entry = QueueEntry.model_validate(detail["entry"])
        decision = demo_decision(entry, ReviewAction.APPROVE, "m16-approval")
        action_headers = headers(
            "reviewer",
            "action",
            **{
                "Idempotency-Key": str(decision.action_id),
                "If-Match": f'"{entry.review_revision}"',
            },
        )
        action_path = f"/api/v1/reviews/{entry_id}/actions"
        approved = record(
            "recommendation-approval",
            client.post(action_path, headers=action_headers, json=decision.model_dump(mode="json")),
            200,
        )
        if (
            record(
                "duplicate-review-action",
                client.post(
                    action_path, headers=action_headers, json=decision.model_dump(mode="json")
                ),
                200,
            )
            != approved
        ):
            raise ValueError("review replay changed its receipt")
        record(
            "unauthorized-review",
            client.get(f"/api/v1/reviews/{entry_id}", headers=headers("outsider", "outsider")),
            404,
        )
        record("nonhuman-denied", client.get("/api/v1/reviews", headers=headers("mcp", "mcp")), 403)
        stale_headers = {**process_headers, "Idempotency-Key": str(uuid5(NAMESPACE, "stale"))}
        record(
            "stale-processing",
            client.post(process_path, headers=stale_headers, json=process_body),
            412,
        )
        final = record(
            "processing-status",
            client.get(f"/api/v1/claims/{claim_id}/status", headers=headers("host", "status")),
            200,
        )
        if (
            final["final_outcome"] is not None
            or final["settlement_authorized"]
            or not final["human_approval_required"]
        ):
            raise ValueError("API acquired insurance-outcome authority")
        specification = client.get("/openapi.json").json()
        OpenAPI.model_validate(specification)
    report: dict[str, object] = {
        "report_version": "offline-claims-api-v1",
        "execution_surface": "FASTAPI_TESTCLIENT_ASGI_NOT_TCP",
        "identity_mode": "EPHEMERAL_HOST_CAPABILITY_NOT_ENTRA",
        "azure_operations": 0,
        "live_model_calls": 0,
        "autonomous_outcomes": 0,
        "insurance_outcome_authority": False,
        "upstream_model_execution": "SIMULATED_EXISTING_M12_WORKFLOW",
        "storage": "BOUNDED_SINGLE_PROCESS_MEMORY_NOT_DURABLE",
        "openapi_sha256": sha256(json_bytes(specification)).hexdigest(),
        "processor_sha256": sha256(
            b"".join(
                p.name.encode() + b"\0" + p.read_bytes()
                for p in sorted(Path(__file__).parent.glob("*.py"))
            )
        ).hexdigest(),
        "cases": cases,
    }
    return report, specification


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline synthetic FastAPI protocol evidence")
    parser.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--openapi-output", type=Path, required=True)
    args = parser.parse_args()
    try:
        root = args.spec_root.resolve()
        paths = (args.output.resolve(), args.openapi_output.resolve())
        protected = [root, Path("data").resolve(), *(p for p in root.parents if p.name == "data")]
        if paths[0] == paths[1] or any(
            p.exists() or any(p.is_relative_to(r) for r in protected) for p in paths
        ):
            raise ValueError("outputs must be new files outside reference data")
        report, specification = offline_report(root)
        for path, value in zip(paths, (report, specification), strict=True):
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as stream:
                stream.write(json_bytes(value))
    except Exception as error:
        parser.exit(
            1, f"Offline API verification failed ({type(error).__name__}); raw payload omitted.\n"
        )
    print(
        "Genuine offline FastAPI/OpenAPI evidence recorded; synthetic identity; "
        "no cloud/outcome authority."
    )


if __name__ == "__main__":
    main()
