"""Explicit local browser launcher and reproducible real UI/API ASGI demonstration."""

import argparse
import re
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path

from fastapi.testclient import TestClient

from claims_ai.dataset.generator import json_bytes
from claims_ai.reviewer_ui.host import demo_host

ORIGIN = "http://127.0.0.1:8767"


class FormInputs(HTMLParser):
    def __init__(self, html: str) -> None:
        super().__init__()
        self.values: dict[str, str] = {}
        self.feed(html)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "input" and values.get("name") is not None:
            self.values.setdefault(values["name"] or "", values.get("value") or "")


def enroll(client: TestClient, code: str) -> None:
    response = client.get("/login")
    if response.status_code != 200:
        raise ValueError("synthetic enrollment unavailable")
    fields = FormInputs(response.text).values
    response = client.post(
        "/login",
        data={"csrf": fields["csrf"], "code": code},
        headers={"Origin": ORIGIN},
        follow_redirects=False,
    )
    if response.status_code != 303:
        raise ValueError("synthetic enrollment failed")


def action_fields(html: str, action: str) -> dict[str, str]:
    fields = FormInputs(html).values
    return {
        "csrf": fields["csrf"],
        "ticket": fields["ticket"],
        "evidence": fields["evidence"],
        "action": action,
        "rationale": "Synthetic reviewer inspected the source-linked advisory and uncertainty.",
    }


def snapshot(html: str) -> bytes:
    sanitized = re.sub(r'(name="(?:csrf|ticket)" value=")[^"]+(\")', r"\1REDACTED\2", html)
    sanitized = sanitized.replace('<button type="submit">', '<button type="submit" disabled>')
    return sanitized.encode()


def demonstrate(root: Path) -> tuple[dict[str, object], dict[str, bytes]]:
    cases: list[dict[str, object]] = []
    captures: dict[str, bytes] = {}
    with (
        demo_host(root) as host,
        TestClient(host.app, base_url=ORIGIN, client=("127.0.0.1", 52000)) as reviewer,
        TestClient(host.app, base_url=ORIGIN, client=("127.0.0.1", 52001)) as supervisor,
    ):
        # One ASGI app has two clients here; both remain inside their lifespan throughout actions.
        def check(name: str, status: int, expected: int) -> None:
            if status != expected:
                raise ValueError("unexpected UI protocol result")
            cases.append({"scenario": name, "status": status})

        enroll(reviewer, host.codes["reviewer"])
        enroll(supervisor, host.codes["supervisor"])
        response = reviewer.get("/")
        check("assigned-reviewer-queue", response.status_code, 200)
        captures["reviewer-queue.html"] = snapshot(response.text)
        response = supervisor.get("/")
        check("assigned-supervisor-queue", response.status_code, 200)
        captures["supervisor-queue.html"] = snapshot(response.text)
        all_items = host.api.queue(host.fixture.tokens["supervisor"]).items
        first = host.api.queue(host.fixture.tokens["reviewer"]).items[0]
        by_claim = {item.claim_id: item for item in all_items}
        first_path = "/reviews/" + first.entry_id
        first_html = reviewer.get(first_path).text
        captures["case-detail.html"] = snapshot(first_html)
        check("case-detail", reviewer.get(first_path).status_code, 200)
        second_claim = host.fixture.bundles[1].request.intake.claim.claim_id
        second = by_claim[second_claim]
        check("cross-case-denied", reviewer.get("/reviews/" + second.entry_id).status_code, 404)
        old_supervisor = supervisor.get(first_path).text
        data = action_fields(first_html, "escalate_to_supervisor")
        response = reviewer.post(first_path + "/actions", data=data, headers={"Origin": ORIGIN})
        check("reviewer-escalation", response.status_code, 200)
        check(
            "exact-action-replay",
            reviewer.post(
                first_path + "/actions", data=data, headers={"Origin": ORIGIN}
            ).status_code,
            200,
        )
        stale = action_fields(old_supervisor, "approve_recommendation")
        check(
            "stale-review-revision",
            supervisor.post(
                first_path + "/actions", data=stale, headers={"Origin": ORIGIN}
            ).status_code,
            409,
        )
        denied = action_fields(reviewer.get(first_path).text, "approve_recommendation")
        check(
            "supervisor-boundary",
            reviewer.post(
                first_path + "/actions", data=denied, headers={"Origin": ORIGIN}
            ).status_code,
            403,
        )
        approval = action_fields(supervisor.get(first_path).text, "approve_recommendation")
        check(
            "supervisor-recommendation-approval",
            supervisor.post(
                first_path + "/actions", data=approval, headers={"Origin": ORIGIN}
            ).status_code,
            200,
        )
        second_path = "/reviews/" + second.entry_id
        reject = action_fields(supervisor.get(second_path).text, "reject_recommendation")
        check(
            "recommendation-rejection",
            supervisor.post(
                second_path + "/actions", data=reject, headers={"Origin": ORIGIN}
            ).status_code,
            200,
        )
        exception = next(item for item in all_items if not item.recommendation_available)
        exception_path = "/reviews/" + exception.entry_id
        html = supervisor.get(exception_path).text
        captures["supervisor-exception.html"] = snapshot(html)
        invalid = action_fields(html, "approve_recommendation")
        check(
            "missing-recommendation-blocked",
            supervisor.post(
                exception_path + "/actions", data=invalid, headers={"Origin": ORIGIN}
            ).status_code,
            409,
        )
        evidence = action_fields(supervisor.get(exception_path).text, "request_additional_evidence")
        evidence["requested_evidence"] = "repair_estimate"
        check(
            "supervisor-evidence-request",
            supervisor.post(
                exception_path + "/actions", data=evidence, headers={"Origin": ORIGIN}
            ).status_code,
            200,
        )
        for item in all_items:
            view = host.api.view(host.fixture.tokens["supervisor"], item.entry_id)
            if (
                view.detail.current_case.decision is not None
                or view.detail.current_case.assessment is not None
                or view.status.final_outcome is not None
                or view.status.settlement_authorized
            ):
                raise ValueError("review UI acquired insurance outcome authority")
        states = [
            str(item.state) for item in host.api.queue(host.fixture.tokens["supervisor"]).items
        ]
    return {
        "milestone": 17,
        "execution_surface": "REAL_FASTAPI_UI_AND_M16_TESTCLIENT_ASGI_NOT_TCP",
        "identity": "HOST_ENROLLED_EPHEMERAL_SYNTHETIC_CAPABILITIES_NOT_ENTRA",
        "azure_operations": 0,
        "live_model_calls": 0,
        "autonomous_outcomes": 0,
        "insurance_outcome_authority": False,
        "storage": "BOUNDED_MEMORY_NOT_DURABLE",
        "audit_clock": "FIXED_SYNTHETIC_M15_TIME",
        "captures": sorted(captures),
        "ui_sha256": sha256(
            b"".join(
                p.name.encode() + b"\0" + p.read_bytes()
                for p in sorted(Path(__file__).parent.glob("*.py"))
            )
        ).hexdigest(),
        "scenarios": cases,
        "final_review_states": states,
    }, captures


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline synthetic claims reviewer operations")
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("serve", "demo"):
        item = sub.add_parser(command)
        item.add_argument("--spec-root", type=Path, default=Path("data/rules/motor/v1"))
        if command == "serve":
            item.add_argument("--port", type=int, default=8767)
        else:
            item.add_argument("--output", type=Path, required=True)
            item.add_argument("--html-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.command == "serve":
            import uvicorn

            with demo_host(args.spec_root, port=args.port) as host:
                print(f"Offline synthetic UI: http://127.0.0.1:{args.port}/login", flush=True)
                for name, code in host.codes.items():
                    print(f"One-use synthetic {name} code (5 minutes): {code}", flush=True)
                uvicorn.run(
                    host.app,
                    host="127.0.0.1",
                    port=args.port,
                    access_log=False,
                    log_level="critical",
                )
        else:
            output, directory = args.output.resolve(), args.html_dir.resolve()
            root = args.spec_root.resolve()
            protected = [
                Path("data").resolve(),
                root,
                *(p for p in root.parents if p.name == "data"),
            ]
            if (
                any(
                    path.exists() or any(path.is_relative_to(p) for p in protected)
                    for path in (output, directory)
                )
                or output.is_relative_to(directory)
                or directory.is_relative_to(output)
            ):
                raise ValueError("evidence paths must be distinct new paths outside reference data")
            report, captures = demonstrate(root)
            output.parent.mkdir(parents=True, exist_ok=True)
            directory.mkdir(parents=True, exist_ok=False)
            for name, html in captures.items():
                (directory / name).write_bytes(html)
            with output.open("xb") as stream:
                stream.write(json_bytes(report))
            print("Real offline UI/API evidence recorded; no TCP or cloud enforcement claim.")
    except Exception as failure:
        parser.exit(
            1,
            "Reviewer demonstration unavailable "
            f"({type(failure).__name__}); raw details omitted.\n",
        )


if __name__ == "__main__":
    main()
