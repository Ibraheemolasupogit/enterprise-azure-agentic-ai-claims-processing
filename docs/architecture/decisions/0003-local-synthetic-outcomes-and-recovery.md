# ADR-0003 — Local synthetic outcomes and transactional recovery

Status: **Accepted for the explicitly authorised M20 offline foundation only**. This adds no production insurance authority. [ADR-0001](0001-decision-authority.md) and [ADR-0002](0002-identity-verification-and-host-authority.md) remain in force.

Decision: use standard-library SQLite for bounded local case, versioned supplied assessment, explicit human decision, assignment, receipt, append-only audit and transactional outbox storage. Reuse M2 lifecycle guards and M12/M15 provenance replay. A separate independent host-approved synthetic assessment registry and nonserialized publication permit gate publication; M9 findings and M15 recommendation acceptance never become final outcomes automatically.

Current authentication uses the existing host-verified M16/M18 capability interface and canonical M15 sessions. Restart restores domain history, never credentials or authorisation from stored role claims. The host independently reprovisions approved sources and principal/session configuration. Every human action still requires current case assignment, separation of duties and exact revision/content binding; supervisor rules remain mandatory.

FULL synchronous DELETE-journal transactions atomically commit state, decision/audit, receipt and outbox. Pure replay and independent source equality validate persisted projections. Delivery is solely a local metadata sink with durable bounded retries/idempotent receipts; no communications or financial system is invoked. Fault verification must terminate real subprocesses before/after commit and prove fresh-process replay.

Consequences: runtime/schema mismatches, missing bytes, corruption and unapproved inputs fail closed, without repair or automatic migration. Same-version restart is supported; upgrades need a separate preservation/migration decision. Unsigned SQLite history is not WORM or protection against a trusted owner rewriting all data/anchors. Local SQLite tests establish neither Azure PostgreSQL semantics nor distributed exactly-once effects, real human identity, power-loss assurance or production readiness. Canonical-session/host-source trust and all prior documented limitations remain.

Trace: FR-006/FR-010/FR-011/FR-012/FR-013; NFR-002/NFR-004/NFR-009. See [architecture](../governed-durable-outcomes.md) and [M20 evidence](../../milestones/milestone-20.md).
