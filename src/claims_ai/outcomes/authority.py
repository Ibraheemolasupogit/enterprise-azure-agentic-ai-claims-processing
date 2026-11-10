"Fresh existing capabilities plus independent canonical sessions and publication permits."

from dataclasses import dataclass
from uuid import UUID

from claims_ai.api.auth import Authenticator
from claims_ai.human_review.contracts import Principal, PrincipalKind, ReviewSession
from claims_ai.models import ClaimId
from claims_ai.outcomes.contracts import ApprovedInput, OutcomeError, StoredCase, input_hash
from claims_ai.outcomes.recovery import verify_approval
from claims_ai.rules.specification import digest


@dataclass(frozen=True, eq=False)
class PublicationPermit:
    "Host-only object capability, never serialized, recovered or issued through an endpoint."

    pass


class Authority:
    def __init__(
        self,
        authenticator: Authenticator,
        host: Principal,
        sessions: tuple[ReviewSession, ...],
        approved: tuple[ApprovedInput, ...],
    ) -> None:
        if host.kind != PrincipalKind.HOST or len(sessions) > 64 or not 1 <= len(approved) <= 16:
            raise OutcomeError("authority_configuration")
        self.authenticator, self.host = authenticator, host
        if any(s.principal.kind != PrincipalKind.HUMAN for s in sessions):
            raise OutcomeError("authority_configuration")
        self.sessions = {s.principal.principal_id: s for s in sessions}
        self.principals = {
            host.principal_id: host,
            **{k: s.principal for k, s in self.sessions.items()},
        }
        if len(self.sessions) != len(sessions) or host.principal_id in self.sessions:
            raise OutcomeError("authority_configuration")
        self.approved = {a.approval_id: ApprovedInput.model_validate(a) for a in approved}
        if len(self.approved) != len(approved):
            raise OutcomeError("authority_configuration")
        self.sources = {k: verify_approval(a) for k, a in self.approved.items()}
        self.permit = PublicationPermit()

    def actor(self, token: str, claim_id: ClaimId) -> Principal:
        try:
            access = self.authenticator.verify(token)
        except Exception:
            access = None
        if access is None or claim_id not in access.scope.claim_ids:
            raise OutcomeError("access_denied")
        actor = access.scope.principal
        if actor.kind == PrincipalKind.HOST:
            if actor != self.host or access.review_session is not None:
                raise OutcomeError("access_denied")
        elif (
            actor.kind != PrincipalKind.HUMAN
            or self.sessions.get(actor.principal_id) is not access.review_session
            or access.review_session is None
            or access.review_session.principal != actor
        ):
            raise OutcomeError("access_denied")
        return actor

    def approval(self, approval_id: UUID) -> ApprovedInput:
        result = self.approved.get(approval_id)
        if result is None:
            raise OutcomeError("publication_not_authorized")
        return result

    def assigned(self, actor: Principal, state: StoredCase) -> None:
        if actor.kind != PrincipalKind.HUMAN or not any(
            assignment.principal == actor
            and assignment.input_sha256 == input_hash(state.case)
            and assignment.assessment_sha256 == state.binding.assessment_sha256
            for assignment in state.assignments
        ):
            raise OutcomeError("assignment_required")

    def forbidden(self, approval_id: UUID) -> set[UUID]:
        return {
            self.approval(approval_id).approved_by,
            *self.sources[approval_id].initial.producer_ids,
        }

    def known(self, actor: Principal) -> None:
        if self.principals.get(actor.principal_id) != actor:
            raise OutcomeError("unknown_historical_actor")

    def artifact(self, approval_id: UUID) -> str:
        return digest(self.approval(approval_id).bundle.model_dump(mode="json"))
