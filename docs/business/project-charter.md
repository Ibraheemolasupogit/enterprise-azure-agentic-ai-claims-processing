# Project charter

Status: **Documented business baseline, refined in Milestone 3; operating model PLANNED.** Northstar Insurance Group and its processes are fictional. The current-process description is a design assumption, not an observed insurer assessment. Milestone 2 supplies locally tested contracts/guards, not this end-to-end process.

## Problem, objective and stakeholders

Assumed current process: handlers receive documents separately, rekey claim details, locate policy versions, compare repair evidence and record decisions manually. Missing evidence and unclear handoffs create rework and weak traceability.

Target process: authenticated intake → validated evidence → applicable policy lookup → deterministic rule assessment → evidence-backed recommendation → authorized human decision → auditable closure. The project demonstrates engineering and governance, not insurance regulatory certification.

| Stakeholder role | Responsibility in the proposed operating model |
| --- | --- |
| Sponsor/product owner | Approve scope, priorities and measurable acceptance |
| Claimant (synthetic persona) | Supply fictional loss details and requested evidence; inspect case status and request correction through a handler; cannot approve coverage or access another case |
| Claims handler/reviewer | Verify evidence, request corrections, approve ordinary eligible/no-flag assessments and escalate other cases |
| Claims supervisor | Review high-risk cases and authorize overrides with reasons |
| Policy owner | Approve fictional policy versions and executable rule mappings |
| Security/privacy and responsible AI reviewer | Review threat model, access, retention and model limitations |
| Platform engineer/operator | Own deployment, budgets, monitoring and recovery |
| Quality/evaluation owner | Curate independent golden labels and release evidence |
| Compliance/audit reviewer | Review provenance, reasons, overrides, access/retention evidence and release limitations; report control exceptions without changing case outcomes |

These are responsibilities, not claims that a staffed organization exists; one portfolio maintainer may perform multiple roles with explicitly recorded review limitations.

Handlers own evidence completeness and ordinary review; supervisors own escalated review, adverse outcomes, overrides, reopening and quarantine release. Operators own recovery and cost control, without claims-decision authority or blanket evidence access. Compliance/audit receives authorized audit access, not operational write rights. The policy owner approves fictional wording and rule mappings; an operational supervisor cannot invent or publish rules through an override. Queue assignment, service identities and audit-read access are planned application controls; they are not fields/roles already implemented in `ReviewerRole`.

## Manual process and target workflow

The manual sequence below is a synthetic scenario walkthrough, not measured process research. Target steps reference the existing architecture; only schema and in-memory transition guards are currently implemented.

| Step | Assumed manual process and handoff | Proposed AI-assisted target and accountable owner |
| --- | --- | --- |
| 1. Report loss | Claimant supplies a form and separate attachments; handler creates a case and checks identifiers manually. | Claimant submits fictional data; authenticated intake creates `received` and checks case-scoped access. Handler owns completeness. |
| 2. Check documents | Handler opens files, checks missing items and requests replacements. | `validating` quarantines files pending validation/scanning; unsafe files remain quarantined. Missing evidence routes to `awaiting_evidence`; handler requests replacements. |
| 3. Assemble facts | Handler rekeys dates/amounts and compares forms, estimates and photos. | `extracting` produces source-linked candidates; code normalizes/validates fields and the evidence agent flags semantic discrepancies. Handler verifies uncertain facts. |
| 4. Establish policy | Handler finds the schedule, wording and endorsements applicable to the reported loss. | Code resolves one approved policy bundle; no unique bundle means no coverage assessment. Supervisor triages the exception through planned assignment while the case awaits evidence; a policy owner resolves publication/version questions. |
| 5. Assess | Handler interprets wording and records a recommendation; supervisor considers exceptions. | In `assessing`, approved deterministic rules produce results; version-filtered retrieval and the explanation agent assemble cited rationale. Missing facts/unsupported scope remain explicit; no agent decides coverage. |
| 6. Review | Handler checks the file; supervisor handles adverse or ambiguous recommendations. | `awaiting_review` presents original evidence, rule trace and uncertainties. An ordinary eligible/no-flag assessment may be approved by a handler; other assessments and adverse outcomes require a supervisor under [FR-011](requirements.md#fr-011-supervisor-escalation). |
| 7. Record outcome | Reviewer records the decision and explanation; claimant receives an update. | A current human decision and durable audit commit are required before operational closure. Synthetic claimant-facing status/reasons are planned; real communications/payment remain excluded. Compliance/audit can reconstruct authorized outcomes. |
| 8. Recover or correct | Handler reopens the file; operator investigates technical problems. | Evidence corrections invalidate stale assessments; recovery restarts validation. Supervisors authorize closed-case reopening/quarantine release. Operators restore service without approving claims. |

An unresolved policy bundle cannot be forced into a fabricated `Assessment`: current `Case` validation requires exact policy metadata for `awaiting_review`. Exception-queue assignment and input corrections remain future workflow work. [FR-004](requirements.md#fr-004-policy-bundle-resolution) and [FR-012](requirements.md#fr-012-invalidation-and-recovery) define the required behavior without adding states or contracts here.

## Business requirements

Stable identifiers are not renumbered or reused; changed/retired requirements retain their history. Owners approve later scope/acceptance changes before implementation.

| ID | Required business outcome | Accountable role |
| --- | --- | --- |
| BR-001 | Assemble complete, inspectable motor-loss evidence with explicit gaps and source provenance. | Claims handler |
| BR-002 | Base coverage recommendations on the applicable approved policy/version and deterministic rules. | Policy owner |
| BR-003 | Keep a current, attributable human decision for every outcome and supervisor control over escalations/adverse results. | Claims supervisor |
| BR-004 | Protect case confidentiality and prevent unsafe evidence or AI instructions from gaining operational authority. | Security/privacy reviewer |
| BR-005 | Demonstrate reproducible, recoverable and cost-governed operation before any deployment/readiness claim. | Platform operator |
| BR-006 | Reduce handler rework while retaining evidence quality and explainable decisions. | Sponsor/product owner |

[Functional/non-functional requirements](requirements.md) specify acceptance criteria. The [traceability matrix](traceability-matrix.md) maps each to actual contracts, existing tests and explicitly planned verification. The [risk register](risk-register.md) records unresolved threats and owners.

## Initial motor-claims boundary

In scope: English-language synthetic first-party private motor accidental-damage claims; fictional GBP amounts; PDF claim forms, policy schedules/wordings and repair estimates; JPEG/PNG damage photographs. Exact upload limits and supported service versions will be fixed during implementation. A policy schedule must resolve the applicable wording and endorsements for the loss date.

Inputs include a synthetic policy register and versioned rules approved by the policy owner. Outputs include normalized evidence, unresolved facts, clause citations, rule results, a reviewer packet and a human-approved demo outcome. Photos support visible-damage description only; they cannot establish causation, liability, repair safety or a reliable valuation.

Excluded: bodily injury/medical claims, liability disputes, litigation, total-loss valuation, real fraud determinations, payments, external insurer systems and real customer communications. Unsupported or suspected high-risk cases go to a supervisor without an automated adverse decision.

## Proposed measurable outcomes

All targets are provisional acceptance goals, **not results**. Establish a timed synthetic manual baseline before claiming improvement; record sample size and reviewer effort.

| Outcome | Proposed measure and target |
| --- | --- |
| Traceable recommendations | 100% of material recommendation facts link to evidence; all policy citations match the resolved version |
| Predictable rules | 100% agreement with approved expected results on deterministic rule cases |
| Effective oversight | 100% of outcomes human-approved; all labeled ambiguous/high-risk cases escalated |
| Evidence quality | At least 95% normalized exact match on labeled critical fields, with per-field and difficult-document breakdowns |
| Reduced handling effort | Target at least 25% reduction in median active review time on paired synthetic cases; include correction effort and report quality alongside time |
| Governed operations | No unauthorized access/state changes in the release suite; reproducible evaluation manifest and complete outcome audit records |

Technical metrics and release gates are defined in [evaluation and observability](../quality/evaluation-and-observability.md). The [roadmap](../milestones/roadmap.md) sequences delivery. Scope or threshold changes require a documented rationale, owner and evaluation impact before release.
