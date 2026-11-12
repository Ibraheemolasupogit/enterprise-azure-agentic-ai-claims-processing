# ADR-0004 — Offline identity profiles and independent durable grant lifecycle

Status: accepted within the explicitly authorized M21 offline synthetic scope. [ADR-0002](0002-identity-verification-and-host-authority.md) and [ADR-0003](0003-local-synthetic-outcomes-and-recovery.md) remain in force.

Use separate Entra-shaped fixture DTOs/verifiers rather than widening M18's synthetic authority. Fixture signature success cannot create application sessions or grants. Live provider discovery, sign-in, acquisition, cloud identities and deployment remain disabled.

Compose explicit case/resource/permission-bound lifecycle gates around existing API/UI, MCP and outcome verification interfaces. Use a small independent SQLite append-only HMAC-authenticated ledger for bounded issuance, expiry, revocation and principal disablement. The host retains the integrity key, public verification context and current rollback anchor independently. Reopen requires that anchor and never creates or repairs a missing database. No credentials or session objects are stored. All authorization/assignment/publication checks remain in canonical services; there are no new administration endpoints.

Keep independently configured disabled principals available for historical audit verification while denying fresh actions/duplicate receipts. Preserve M20's schema and runtime compatibility rejection. Upgrading whole-package fingerprints requires fresh same-version stores or a separately approved preservation/migration design, never rewriting history. Local process evidence is not directory/distributed revocation, WORM, production TLS/APIM or actual human identity assurance.

Consequences and evidence: [architecture](../security-and-identity-hardening.md), [M21 record](../../milestones/milestone-21.md), FR-010/FR-011/FR-013, NFR-002/NFR-004/NFR-009. No production security or residual-risk acceptance follows from these static contracts and offline tests.
