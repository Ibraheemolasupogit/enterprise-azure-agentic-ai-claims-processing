# Business process requirements

Status: **Documented in Milestone 3; target behavior PLANNED except the foundation/dataset checks explicitly identified in the [traceability matrix](traceability-matrix.md).** Milestone 4 supplies development fixtures/annotations, not satisfaction of live processing requirements. Scope and roles come from the [charter](project-charter.md); component/agent design remains in the [architecture](../architecture/target-architecture.md).

`BR-*` identifies business requirements, `FR-*` functional requirements and `NFR-*` non-functional requirements. IDs are stable; retire rather than reuse them. Each FR/NFR heading is the authoritative requirement and its following acceptance criterion. All are required for the target platform; this does not assert implementation, test completion or insurance-policy approval. Performance/quality targets inherited from Milestone 1 remain provisional until the stated evaluation plan is approved. All examples and verification use synthetic data only.

## Functional requirements

### FR-001 Synthetic case intake

The platform must accept only the initial motor-damage scope, validate claim identifiers/timezones/GBP metadata and unique document references, and bind access to the synthetic case. Acceptance: malformed identifiers, naive timestamps, unsupported currency and duplicate references are rejected; repeated authorized submissions cannot create duplicate cases. Schema checks exist; authentication, intake API and submission idempotency are planned.

### FR-002 Document safety and extraction

Files must pass case-scoped type, configured size, hash and malware/parse validation before extraction; PDFs and JPEG/PNG photos follow the charter. Acceptance: unsafe/unsupported/unscannable input never reaches a model; retained evidence resolves to matching bytes, document, page and extraction version. Document metadata/scan assertions are not an implemented scanner or proof of byte integrity.

### FR-003 Evidence validation and completeness

Code must validate provenance, normalized values and an explicitly approved required-evidence checklist while preserving unknown/conflicting facts. Acceptance: duplicate/dangling/cross-case/hash/page references fail; missing required validated evidence blocks a complete assessment and requests evidence. Confidence thresholds/checklists require approval and evaluation; the existing helper accepts a caller-supplied checklist and makes no coverage decision.

### FR-004 Policy bundle resolution

Code must resolve exactly one approved schedule/wording/endorsement bundle for the reported loss using authoritative synthetic policy metadata. Acceptance: missing, overlapping or conflicting mappings block assessment, enter/retain `awaiting_evidence` through an allowed transition and create a supervisor-owned exception assignment. No version is guessed. That assignment is planned application metadata, not a new state or an existing `Case` field; policy approval/resolution is not implemented.

### FR-005 Policy-version-aware retrieval

Hybrid keyword/vector retrieval must be restricted to the authorized resolved policy and index version. Acceptance: wrong-version/artifact citations are rejected; empty/outage results cause abstention, never broader filters. A golden query includes relevant clause labels to verify recall and support. Current citation validation checks supplied metadata only; content grounding and actual retrieval are planned.

### FR-006 Deterministic assessment

Only owner-approved, versioned rules may compute coverage/financial results outside prompts. Acceptance: approved fixtures reproduce rule IDs/results and evidence links; unknown facts return `undetermined`; mismatched rule/policy versions block evaluation. Until fictional policy approval, contracts may carry clearly labeled supplied test outcomes but no operational recommendation or calculation is released. A supervisor override does not publish a new rule or erase the original result.

The user-authorized [M9 provisional foundation](../architecture/deterministic-provisional-rules.md) runs separate fictional, non-binding offline findings/illustrations with explicit unapproved status; it does not satisfy or weaken this operational release criterion. Its PASS/FAIL/INDETERMINATE/NOT_APPLICABLE findings are not the existing `AssessmentOutcome` values, and no operational assessment or financial outcome is released.

### FR-007 Evidence reconciliation assistance

The proposed evidence agent may compare heterogeneous evidence and propose facts/discrepancies, never change canonical facts or approve outcomes. Acceptance: contradictory synthetic form/photo/estimate inputs surface uncertainties with evidence references; invalid outputs/timeouts become visible exceptions. Bounded tool/token/time limits and comparison against a simpler baseline are required before claiming agent benefit. Only the service protocol exists.

### FR-008 Policy explanation assistance

The proposed explanation agent may draft reviewer rationale from validated facts, applicable clauses and supplied rule results. Acceptance: every material assertion has verifiable support; unresolved questions remain explicit, and attempts to select a policy, invent a rule or approve a claim fail. A plain returned string from the current protocol is not proof of grounded output; future output validation must enforce the acceptance criterion.

### FR-009 Inspectable review packet

The reviewer must see original evidence, normalized candidates/corrections, applicable versions/clauses, rule trace, draft rationale and unresolved flags. Acceptance: a handler can inspect each cited source and reject/correct suggestions; edits invalidate stale assessments before closure. Queue/UI, evidence correction and end-to-end packet generation remain planned.

### FR-010 Human approval

Every initial outcome must require an explicit human reviewer decision on the current claim/assessment/revision. Acceptance: service/model callers, stale references, actor/role mismatches and decisions timestamped after the supplied transition time cannot close a case. Closure includes a supported final outcome, reason and explicit evidence references; operational publication additionally requires the durable commit in FR-013. Local trusted-role guards do not authenticate users or verify a live clock.

### FR-011 Supervisor escalation

Supervisor handling is mandatory under the following existing guard semantics. This is one decision table for the target workflow and the local implementation; assignment/notifications are still planned.

| Condition | Required action/authority |
| --- | --- |
| `eligible` assessment, no risk flags, unchanged eligible outcome | Handler/reviewer or supervisor may explicitly approve. |
| `ineligible` or `undetermined` assessment | Supervisor handles every outgoing review transition, including request for evidence or invalidation. |
| Any `ambiguous`, `high_risk`, `conflicting`, `injection_flagged` or `unsupported` flag | Supervisor handles every outgoing review transition, even if the supplied outcome is eligible. |
| Any final `ineligible` outcome | Supervisor decision required; no autonomous adverse outcome. |
| Requested outcome differs from assessment | Explicit supervisor `override`, reason and referenced evidence required; preserve prior assessment. |
| `undetermined` outcome | Cannot simply approve closure; supervisor requests evidence or explicitly overrides to a supported final eligible/ineligible outcome. Unresolved facts must not be silently treated as proven. |
| Closed-case reopening or quarantine release | Supervisor authorizes return to `validating`; release authorizes revalidation, not a scan bypass. |

Acceptance: exercise each condition and deny handler/service bypasses; the future application must assign/notify a supervisor and record a reason before operational routing. `Assessment.requires_supervisor` and transition/decision guards exist; no work queue or verified identity exists. Self-review separation is an unresolved governance choice, not a current two-person control.

### FR-012 Invalidation and recovery

Changes to evidence, applicable policy/rules or reviewed facts must invalidate earlier assessments and require revalidation/review. Acceptance: evidence requests retain prior history, recovery cannot skip `validating`, stale approvals fail, and closed cases require supervisor reopening. Existing transitions preserve claim input; atomic input-correction/version-update workflows remain planned and cannot be simulated by changing a frozen model in place.

### FR-013 Auditable outcome commit

Case state, decision, revision and append-only audit event must commit atomically with durable duplicate/replay protection. Acceptance: crash/concurrent/repeated submissions cause no lost acknowledged case, duplicated outcome or unaudited closure; changed content under a reused event ID is rejected. Every published outcome reconstructs actor, evidence, policy, assessment/rules and reason. Current transition records and repository protocol define data/obligations only; no persistence guarantee exists.

### FR-014 Evidence requests and claimant status

Handlers must communicate evidence gaps and a case-scoped status/reason to the synthetic claimant persona, with correction requests routed to human review. Acceptance: an evidence request has a reason and resumes validation after replacements; another claimant cannot inspect it; only the approved demo outcome is visible after commit. Real external communication/payment remains excluded. No portal, notification or claimant-authorization implementation exists.

### FR-015 Governed tools

Future agent tools must have typed arguments/results and read-only, case-scoped grants, with selected MCP tools governed through APIM. Acceptance: unauthorized IDs/operations and arbitrary network/shell/SQL/write requests are denied; gateway failure cannot enable direct access. Existing protocols are design boundaries only, not tool execution, MCP servers or a gateway.

## Non-functional requirements

### NFR-001 Confidentiality and retention

Use synthetic artifacts with provenance and exclude raw evidence/prompts/responses/secrets from operational logs. Acceptance: nested sensitive payloads and exception text do not escape the package logger; later ingestion detects/quarantines accidental sensitive data, and approved deletion tests cover stores/indexes/backups/exports. Retention values remain provisional in [security and governance](../architecture/security-and-governance.md#responsible-ai-and-privacy); synthetic markers and redaction do not prove anonymization or compliance.

### NFR-002 Verified identity and least privilege

Authenticate users/workloads, enforce assignment/roles on each API/tool/store action and separate operations, claims decisions and policy publication. Acceptance: expired/wrong-audience/unauthorized/cross-case requests are denied, runtime identities cannot publish rules/deploy/grant access, and operator/audit roles cannot approve claims. Entra, managed identities and network grants are planned; local trusted-role values cannot satisfy this requirement alone.

### NFR-003 Responsible AI and injection resistance

Treat all uploaded/retrieved/tool content as untrusted; bound execution and prevent instructions in evidence from acquiring tool/decision authority. Acceptance: adversarial synthetic inputs cause no unauthorized calls, exfiltration, unsupported material conclusions or automatic closure; uncertainty is visible and flagged assessments require supervisor review. Defense detection, guardrails and adversarial service tests remain planned; images cannot establish causation, fraud or roadworthiness.

### NFR-004 Recoverability and unavailable dependencies

Use atomic outbox/persistence, idempotent workers, bounded retries/deadlines and failure visibility. Acceptance: dependency outage/throttling, duplicate delivery and restart scenarios preserve acknowledged cases and produce neither positive coverage defaults nor authorization bypasses. Retry/time limits must be configured before integration testing. Local recovery edges are not tested queue delivery, concurrency or disaster recovery.

### NFR-005 Observability and audit separation

Correlate intake, extraction, retrieval, agent/tool, rule and review operations without sensitive telemetry. Acceptance: a synthetic run can be traced across services, dependency failures/backlogs trigger owned alerts and every decision has a separate unsampled audit event. Local UUID JSON correlation exists; OpenTelemetry/W3C propagation, Application Insights, dashboards and protected audit retention are planned under the [quality baseline](../quality/evaluation-and-observability.md#telemetry-and-audit-evidence).

### NFR-006 Reproducible evaluation

Release claims must identify dataset/source/model/prompt/tool/rule/policy/index/evaluator versions and distinguish local tests, simulations and live service tests. Acceptance: a held-out synthetic manifest supports repeatable evaluation; report denominators, slices and all safety failures against the [proposed gates](../quality/evaluation-and-observability.md#proposed-acceptance-metrics). Approve/freeze targets before using them for release; aggregate accuracy cannot waive a safety failure. The 115 foundation tests are not golden-data or insurance-performance results.

### NFR-007 Performance and handler effort

Measure packet readiness and active handling effort using paired synthetic cases, including cold starts, corrections, concurrency and quality. Acceptance: publish a timed manual baseline and comparable target-run manifest against the charter's provisional effort goal and quality baseline's latency envelope, recording failures as well as successes. No measurement or SLA is available; approve the measurement protocol before claiming improvement.

### NFR-008 Capacity and cost governance

Cloud work must be gated by approved region/residency, service/SKU/model quota compatibility, monthly/run budgets and application usage caps. Acceptance: an operator can inspect the compatibility/estimate record, suspend new model work at configured limits and verify residual costs; unavailable services cause pause/explicit simulation, never a gateway/policy fallback. Exact numbers and capacity are unverified. Use the existing [deployment gates](../deployment/deployment-strategy.md#region-quota-and-apim-lessons-recorded-as-constraints), not assumed capacity or a new resource deployment.

### NFR-009 Change quality and evidence status

Future code changes must preserve strict typing, focused tests, package validity and documented schema/decision compatibility. Acceptance: applicable `make check`/package checks and regression evidence pass before promoting implementation status; docs-only changes validate links, symbols and traceability. Retain prior milestone evidence as historical, record scope changes and avoid claiming planned services as implemented. Milestone 3 authorized documentation only; subsequent runtime changes require their own approved milestone scope.
