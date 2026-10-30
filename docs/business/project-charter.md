# Project charter

Status: **PLANNED business and operating model**; documentation delivered in Milestone 1. Northstar Insurance Group and its processes are fictional. The current-process description is a design assumption, not an observed insurer assessment.

## Problem, objective and stakeholders

Assumed current process: handlers receive documents separately, rekey claim details, locate policy versions, compare repair evidence and record decisions manually. Missing evidence and unclear handoffs create rework and weak traceability.

Target process: authenticated intake → validated evidence → applicable policy lookup → deterministic rule assessment → evidence-backed recommendation → authorized human decision → auditable closure. The project demonstrates engineering and governance, not insurance regulatory certification.

| Stakeholder role | Responsibility in the proposed operating model |
| --- | --- |
| Sponsor/product owner | Approve scope, priorities and measurable acceptance |
| Claims handler/reviewer | Resolve ambiguity, correct evidence and approve every outcome |
| Claims supervisor | Review high-risk cases and authorize overrides with reasons |
| Policy owner | Approve fictional policy versions and executable rule mappings |
| Security/privacy and responsible AI reviewer | Review threat model, access, retention and model limitations |
| Platform engineer/operator | Own deployment, budgets, monitoring and recovery |
| Quality/evaluation owner | Curate independent golden labels and release evidence |

These are responsibilities, not claims that a staffed organization exists; one portfolio maintainer may perform multiple roles with explicitly recorded review limitations.

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
