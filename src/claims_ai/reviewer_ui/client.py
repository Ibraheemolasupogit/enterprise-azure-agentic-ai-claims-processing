"""Bounded typed consumer of actual M16 endpoints, never a review-service replacement."""

from dataclasses import dataclass
from typing import TypeVar
from uuid import uuid4

from fastapi.testclient import TestClient
from pydantic import BaseModel

from claims_ai.api.contracts import AdvisoryResponse, ClaimStatus, ReviewQueueResponse
from claims_ai.human_review.contracts import ReviewDecision, ReviewDetail, ReviewEvent

T = TypeVar("T", bound=BaseModel)


class UiError(Exception):
    def __init__(self, status: int) -> None:
        self.status = (
            status if status in {400, 401, 403, 404, 409, 412, 413, 415, 422, 429} else 503
        )
        super().__init__("reviewer_operation_unavailable")


@dataclass(frozen=True)
class CaseView:
    detail: ReviewDetail
    status: ClaimStatus
    advisory: AdvisoryResponse


class ApiClient:
    """Host-provided lifespan-managed TestClient; no browser-configured URLs or credentials."""

    def __init__(self, transport: TestClient) -> None:
        self._transport = transport

    def _request(
        self,
        token: str,
        method: str,
        path: str,
        model: type[T],
        *,
        decision: ReviewDecision | None = None,
    ) -> T:
        headers = {"Authorization": "Bearer " + token, "X-Correlation-ID": str(uuid4())}
        if decision is not None:
            headers.update(
                {
                    "Idempotency-Key": str(decision.action_id),
                    "If-Match": f'"{decision.expected_review_revision}"',
                    "Content-Type": "application/json",
                }
            )
        try:
            response = self._transport.request(
                method,
                path,
                headers=headers,
                content=decision.model_dump_json().encode() if decision else None,
            )
            if response.status_code != 200:
                raise UiError(response.status_code)
            if (
                len(response.content) > 8388608
                or response.headers.get("content-type", "").split(";", 1)[0] != "application/json"
            ):
                raise UiError(503)
            result = model.model_validate_json(response.content)
            revision = None
            if isinstance(result, ReviewDetail):
                revision = result.entry.review_revision
            elif isinstance(result, ReviewEvent):
                revision = result.sequence
            elif isinstance(result, ClaimStatus):
                revision = result.application_revision
            if revision is not None and response.headers.get("etag") != f'"{revision}"':
                raise UiError(503)
            return result
        except UiError:
            raise
        except Exception:
            raise UiError(503) from None

    def queue(self, token: str, offset: int = 0) -> ReviewQueueResponse:
        if offset not in range(0, 65, 16):
            raise UiError(400)
        return self._request(
            token, "GET", f"/api/v1/reviews?limit=16&offset={offset}", ReviewQueueResponse
        )

    def view(self, token: str, entry_id: str) -> CaseView:
        detail = self._request(token, "GET", "/api/v1/reviews/" + entry_id, ReviewDetail)
        if detail.entry.entry_id != entry_id:
            raise UiError(503)
        claim_id = detail.entry.binding.claim_id
        status = self._request(token, "GET", f"/api/v1/claims/{claim_id}/status", ClaimStatus)
        advisory = self._request(
            token, "GET", f"/api/v1/claims/{claim_id}/advisory", AdvisoryResponse
        )
        if (
            detail.current_case.claim.claim_id != claim_id
            or detail.advisory_snapshot.case.claim.claim_id != claim_id
            or status.claim_id != claim_id
            or status.review_entry_id != entry_id
            or advisory.claim_id != claim_id
            or advisory.review_binding != detail.entry.binding
        ):
            raise UiError(503)
        return CaseView(detail, status, advisory)

    def act(self, token: str, decision: ReviewDecision) -> ReviewEvent:
        result = self._request(
            token,
            "POST",
            f"/api/v1/reviews/{decision.entry_id}/actions",
            ReviewEvent,
            decision=decision,
        )
        if (
            result.entry_id != decision.entry_id
            or result.claim_id != decision.expected.claim_id
            or result.decision != decision
        ):
            raise UiError(503)
        return result
