"""Async boundaries only: no clients, stores, processors or agents are implemented."""

from typing import Protocol

from claims_ai.lifecycle import CaseTransition
from claims_ai.models import (
    Assessment,
    Case,
    ClaimId,
    DocumentMetadata,
    Evidence,
    Policy,
    PolicyClause,
)


class DocumentProcessor(Protocol):
    async def process(self, document: DocumentMetadata, *, content: bytes) -> tuple[Evidence, ...]:
        """Process only validated/scanned input; preserve document/hash/page provenance."""
        ...


class PolicyRetriever(Protocol):
    async def retrieve(self, query: str, *, policy: Policy, limit: int) -> tuple[PolicyClause, ...]:
        """Restrict every result to the supplied exact policy/index bundle; never widen scope."""
        ...


class CaseRepository(Protocol):
    async def get(self, claim_id: ClaimId) -> Case | None: ...

    async def save_transition(self, transition: CaseTransition) -> None:
        """Atomically compare previous revision, store current state and append the audit event.

        Reject conflicts and duplicate event IDs with different content. Idempotent retries
        of an identical event must not duplicate outcomes. No adapter implements this yet.
        """
        ...


class EvidenceReconciliationService(Protocol):
    async def reconcile(self, case: Case) -> tuple[Evidence, ...]:
        """Return evidence candidates only; do not mutate authoritative case facts."""
        ...


class PolicyExplanationService(Protocol):
    async def explain(self, assessment: Assessment) -> str:
        """Draft an explanation only; cannot approve a decision or compute coverage."""
        ...
