"""Finite process-local sessions and one-use host enrollment; no browser role or case grants."""

import secrets
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from threading import RLock
from time import monotonic
from uuid import uuid4

from claims_ai.human_review.contracts import (
    DecisionReason,
    ReviewAction,
    ReviewDecision,
    ReviewDetail,
)
from claims_ai.models import DocumentKind
from claims_ai.reviewer_ui.client import UiError
from claims_ai.rules.specification import digest


@dataclass(frozen=True)
class Profile:
    label: str
    api_token: str = field(repr=False)


@dataclass
class FormTicket:
    detail: ReviewDetail
    decision: ReviewDecision | None = None
    fingerprint: str | None = None


@dataclass
class Session:
    csrf: str = field(repr=False)
    expires: float
    profile: Profile | None = field(default=None, repr=False)
    forms: dict[str, FormTicket] = field(default_factory=dict, repr=False)


class Sessions:
    """Host is trusted; opaque UI cookies never contain API capabilities or serialized claims."""

    def __init__(
        self,
        *,
        timer: Callable[[], float] = monotonic,
        clock: Callable[[], datetime],
        credential_valid: Callable[[str], bool] | None = None,
    ) -> None:
        self._timer, self._clock = timer, clock
        self._credential_valid = credential_valid
        self._sessions: dict[str, Session] = {}
        self._codes: dict[str, tuple[Profile, float]] = {}
        self._attempts = 0
        self._lock = RLock()

    def _purge(self) -> None:
        now = self._timer()
        self._sessions = {k: v for k, v in self._sessions.items() if v.expires > now}
        self._codes = {k: v for k, v in self._codes.items() if v[1] > now}

    def provision(self, profile: Profile) -> str:
        with self._lock:
            self._purge()
            self._check_profile(profile)
            if len(self._codes) >= 8:
                raise UiError(429)
            code = secrets.token_urlsafe(32)
            self._codes[sha256(code.encode()).hexdigest()] = (profile, self._timer() + 300)
            return code

    def _check_profile(self, profile: Profile) -> None:
        if self._credential_valid is not None:
            try:
                valid = self._credential_valid(profile.api_token)
            except Exception:
                valid = False
            if valid is not True:
                self.revoke_profile(profile.api_token)
                raise UiError(401)

    def revoke(self, cookie: str) -> None:
        """Host-only revocation; no browser or administrative endpoint is introduced."""
        with self._lock:
            self._sessions.pop(sha256(cookie.encode()).hexdigest(), None)

    def revoke_profile(self, api_token: str) -> None:
        with self._lock:
            self._sessions = {
                k: v
                for k, v in self._sessions.items()
                if v.profile is None or v.profile.api_token != api_token
            }
            self._codes = {k: v for k, v in self._codes.items() if v[0].api_token != api_token}

    def anonymous(self) -> tuple[str, Session]:
        with self._lock:
            self._purge()
            if len(self._sessions) >= 8:
                raise UiError(429)
            cookie = secrets.token_urlsafe(32)
            session = Session(secrets.token_urlsafe(32), self._timer() + 300)
            self._sessions[sha256(cookie.encode()).hexdigest()] = session
            return cookie, session

    def get(self, cookie: str, csrf: str | None = None, *, human: bool = True) -> Session:
        with self._lock:
            self._purge()
            session = self._sessions.get(sha256(cookie.encode()).hexdigest())
            if session is None or human and session.profile is None:
                raise UiError(401)
            if session.profile is not None:
                self._check_profile(session.profile)
            if csrf is not None and not secrets.compare_digest(session.csrf, csrf):
                raise UiError(403)
            return session

    def login(self, cookie: str, csrf: str, code: str) -> tuple[str, Session]:
        with self._lock:
            self.get(cookie, csrf, human=False)
            if self._attempts >= 16:
                raise UiError(429)
            self._attempts += 1
            enrollment = self._codes.pop(sha256(code.encode()).hexdigest(), None)
            if enrollment is None:
                raise UiError(401)
            self._check_profile(enrollment[0])
            self._sessions.pop(sha256(cookie.encode()).hexdigest())
            rotated, session = self.anonymous()
            session.profile, session.expires = enrollment[0], self._timer() + 900
            return rotated, session

    def logout(self, cookie: str, csrf: str) -> None:
        with self._lock:
            self.get(cookie, csrf)
            self._sessions.pop(sha256(cookie.encode()).hexdigest())

    def prepare(self, cookie: str, detail: ReviewDetail) -> str:
        with self._lock:
            session = self.get(cookie)
            if len(session.forms) >= 4:
                session.forms.pop(next(iter(session.forms)))
            ticket = str(uuid4())
            session.forms[ticket] = FormTicket(detail)
            return ticket

    def decision(
        self, cookie: str, entry_id: str, fields: Mapping[str, tuple[str, ...]]
    ) -> tuple[Profile, ReviewDecision]:
        with self._lock:
            session = self.get(cookie, fields.get("csrf", ("",))[0])
            ticket = session.forms.get(fields.get("ticket", ("",))[0])
            if ticket is None or ticket.detail.entry.entry_id != entry_id:
                raise UiError(412)
            fingerprint = digest(dict(fields))
            if ticket.decision is not None:
                if ticket.fingerprint != fingerprint:
                    raise UiError(409)
                assert session.profile is not None
                return session.profile, ticket.decision
            try:
                action = ReviewAction(fields["action"][0])
                reasons = {
                    ReviewAction.APPROVE: DecisionReason.SUPPORTED,
                    ReviewAction.REJECT: DecisionReason.UNSUPPORTED,
                    ReviewAction.REQUEST_EVIDENCE: DecisionReason.EVIDENCE,
                    ReviewAction.ESCALATE: DecisionReason.SUPERVISOR,
                }
                evidence = fields.get("evidence", ())
                references = {r.evidence_id: r for r in ticket.detail.entry.evidence}
                if len(set(evidence)) != len(evidence) or not set(evidence) <= references.keys():
                    raise ValueError("unknown source reference")
                decision = ReviewDecision(
                    action_id=uuid4(),
                    entry_id=entry_id,
                    expected_review_revision=ticket.detail.entry.review_revision,
                    expected=ticket.detail.entry.binding,
                    action=action,
                    reason=reasons[action],
                    rationale=fields["rationale"][0],
                    evidence=tuple(references[e] for e in evidence),
                    requested_evidence=tuple(
                        DocumentKind(value) for value in fields.get("requested_evidence", ())
                    ),
                    occurred_at=self._clock(),
                )
            except (ValueError, KeyError, IndexError):
                raise UiError(422) from None
            ticket.decision, ticket.fingerprint = decision, fingerprint
            assert session.profile is not None
            return session.profile, decision
