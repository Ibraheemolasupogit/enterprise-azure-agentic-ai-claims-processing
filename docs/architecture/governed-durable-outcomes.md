# Durable synthetic human outcomes and recovery — M20

Status: implemented local SQLite foundation; final verification is recorded in [M20 evidence](../milestones/milestone-20.md). [ADR-0003](decisions/0003-local-synthetic-outcomes-and-recovery.md) limits the authority and durability claims. M15 recommendation approval remains advisory; M16/M17 contracts and three read-only MCP tools are unchanged. No real insurer decision, settlement, payment, notification, Azure service or new agent exists.

## Publication and current authority

The trusted host independently configures a finite `ApprovedInput` registry, synthetic principal/session registry and existing `Authenticator`. A publication input supplies an explicit M2 `Assessment` test outcome, approval ID, separate synthetic policy-owner identity, rationale and exact source/recovery bundle. It is not constructed from a recommendation action or automatic M9 PASS/FAIL mapping. `actual_insurance_authority` and `settlement_authorized` remain false. M9 rules, data and unapproved status are unchanged; this does not activate an operational policy register.

Approval verification reuses M15's M12 semantic restoration and M6/M7/M9 source, evidence, exact policy/version/index and rule binding. Its case must match the verified source (with the selected policy and explicitly versioned adoption revision), assessment input hash, exact evidence inventory and real citations. An adverse/ambiguous M12 source cannot be downgraded to an ordinary eligible/no-risk assessment. Publication requires both a current host capability and an opaque host-owned `PublicationPermit`; neither is deserialized from the database.

Every read/action/delivery verifies the current capability and case scope using the existing M16/M18 authenticator interface. Humans additionally require the exact canonical M15 `ReviewSession` object and current durable assignment. Assigned-role authority is checked against independently configured principals; stored actors/roles are historical evidence only. M18 signed verification/revocation adapters also work through this interface. Restart requires independent host reprovisioning; old capabilities and copied sessions do not recover authority. Credentials, JWTs, keys, cookies and sessions are not persisted. Historical M11 ToolGrant metadata is retained solely for M12 source replay, never as current outcome access.

The source workflow producer, reviewed-fact authors and publication approver cannot be assigned to review that assessment. A host/agent/MCP/model principal cannot decide. Adverse, ambiguous, high-risk or conflicting assessments retain supervisor handling; overrides and closed-case reopening require a supervisor. Every decision has exact case/assessment/policy bindings, current store and case revisions, rationale, evidence references, host-checked time and correlation. Current identity/assignment checks precede duplicate-receipt lookup. A receipt is historical, not a current-state projection; lost assignment/snapshot authority can deny an old receipt. Evidence requests require a renewed snapshot assignment before subsequent actions/retries.

## SQLite schema and transaction contract

Schema `m20-sqlite-v1`, SQLite `user_version=1`, is compared against the exact expected tables/triggers. Unknown, extra or modified schema and runtime fingerprints are rejected. No automatic migration, rehashing, data repair or old-runtime replay exists. Future migrations require a separately reviewed procedure preserving the original database and evidence; current compatibility is same-code/same-runtime only.

| Table | Responsibility |
| --- | --- |
| `meta` | Format and whole-package runtime compatibility |
| `cases` | Current case/store revision and canonical projection |
| `artifacts` | Original versioned recovery bundles with explicit base64 evidence bytes |
| `assessments` | Immutable published synthetic assessment versions |
| `decisions` | Immutable explicit human decisions |
| `assignments` | Current case/assessment-bound canonical assignments |
| `audit` | Immutable ordered commands, canonical actors, reasons, times, correlation, snapshots and actual M2 transitions |
| `receipts` | Durable case/actor/request identity and normalized command fingerprint |
| `outbox` | Transactional local audit-projection work and delivery state |
| `delivery_events` | Immutable bounded attempt/result history |
| `deliveries` | Idempotent local sink receipt keyed by audit event |

Each operation opens an independent connection, enables foreign keys and FULL synchronous DELETE-journal mode, and uses `BEGIN IMMEDIATE`. Case, assessment/decision, assignment, audit, receipt and outbox updates commit in one transaction or roll back together. Revision/binding checks occur within the write transaction. Competing connections/processes cannot both apply incompatible commands at one expected revision. Identical authorised retries return the original event; changed reuse fails. An after-commit/lost-ack retry does not repeat the decision.

Before reads and mutations, SQLite integrity/foreign-key checks, schema/runtime verification, canonical typed JSON, independent approved source bundles, hash chains and pure M2 semantic replay must agree with every projection/receipt/outbox row. Append-only tables have UPDATE/DELETE triggers. Modified projections, rehashed invented case histories, missing sources and incompatible versions are rejected rather than reconstructed into silently trusted state. `expected_heads` allows the host to supply independently retained audit-head anchors to reject coherent rollback. A database owner who can replace all records and anchors remains outside the trust boundary: hashes/triggers are not WORM retention or cryptographic actor attestation.

Limits: private owned directory and 0600 regular database, no file symlinks/hardlinks, 64 MiB physical database, 32 MiB aggregate serialized state, eight cases, 256 total business events, 128 revisions per case, 16 independently approved input versions and 64 canonical sessions. Bundles are bounded to 12 MiB including at most 8 MiB decoded evidence. Capacity errors fail closed; no audit eviction or automatic cleanup occurs. SQLite lock wait is bounded; Python/SQLite/native execution is not a hard CPU or adversarial filesystem sandbox.

## Corrections, revalidation and reopening

An authorised correction first reuses M2 invalidation/revalidation transitions, then increments the case revision for an explicit input replacement. Replacement data has no admitted evidence, selected policy, assessment or decision. Original source bytes, assessments and history remain in immutable versions. Cross-case/policy-ID replacement and invented admitted evidence are denied. Closed cases require supervisor reopening first. Corrections/reopening clear assignments and invalidate stale assessment authority. A correction from a stored VALIDATING case (after supervisor reopening or an earlier correction) takes the same existing VALIDATING → AWAITING_EVIDENCE → VALIDATING invalidation hop as ASSESSING (M25 P3); the lifecycle table and all assignment, self-review, supervisor and independent-approval checks are unchanged.

A new independently approved recovery bundle must match the corrected claim/documents and exact parent binding. M12 re-verifies original bytes/quotes and policy/rule provenance; M2 VALIDATING → EXTRACTING → ASSESSING transitions plus an explicit adoption revision install its verified evidence. This does not publish an assessment. A separate host-permitted publication and new assignments are required before any human decision. Tests and demonstration include genuinely changed narrative/document bytes, not just clearing a model field.

## Recovery and local outbox

Recovery explicitly retains byte-bearing inputs excluded by ordinary `model_dump`, plus M12 checkpoints, limits, grant provenance and runtime fingerprint. The host supplies matching independent approval sources; database content cannot create new approval authority. Missing/altered bytes, changed code or absent historical principals fail closed. Restoring an old schema/checkpoint after a software upgrade is not claimed. M12's timing-dependent retry/reproduction limitation remains unchanged.

The outbox is a local metadata projection only: no email, insurer system, payment or network transport. A delivery attempt, local sink receipt and acknowledgment commit atomically. Duplicate delivery has one local receipt. Three unavailable attempts lead to a durable `dead` state; host restart cannot reset attempts. No distributed exactly-once delivery is claimed. Real SIGKILL probes cover projection/audit/pre-commit rollback, post-commit lost acknowledgment, sink-before-ack and delivery-commit boundaries.

The synchronous service reuses existing contracts; it adds no API/UI endpoint and does not make M16/M17's volatile adapters durable. Future asynchronous integration must explicitly coordinate projections and authority rather than copying sessions or bypassing M15. Store files and journals contain private synthetic domain data, not redacted logs or encrypted storage. Live identity, shared revocation, production PostgreSQL/queues, backup/restore, power-loss/filesystem guarantees, retention, WORM audit and host compromise remain unproved. M8's four failures and all eight M19 production NOT_TESTED scopes remain preserved.
