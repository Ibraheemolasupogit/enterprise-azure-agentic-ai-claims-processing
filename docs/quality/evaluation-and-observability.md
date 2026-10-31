# Evaluation and observability baseline

Status: **IMPLEMENTED offline field-benchmark and lexical retrieval evaluation foundations; extraction fixture results SIMULATED. Live/held-out model evaluation and distributed observability remain PLANNED.** M2 supplies foundation tests/local logs; M4 supplies the [development corpus](../../data/synthetic/motor/README.md); M5 supplies [common extraction contracts, deterministic scoring and a fixture-only runner](document-intelligence-benchmark.md). M8 supplies [offline lexical retrieval metrics against authored queries](policy-retrieval-evaluation.md), with policy/citation checks and explicit simulated dependency faults. No actual Azure/Mistral/GPT comparison, measured model performance, distributed telemetry or operational fault-injection run exists. Targets below remain proposals for the [architecture](../architecture/target-architecture.md). [Traceability](../business/traceability-matrix.md#milestone-8-retrieval-evaluation-evidence) separates local diagnostics from future service verification.

## Synthetic golden dataset and reproducibility

Plan an initial 60-case suite: 15 straightforward covered damage, 10 exclusions/out-of-period, 10 missing/conflicting/poor-quality evidence, 10 policy-version/endorsement boundaries, 10 adversarial/security cases and 5 operational recovery cases. Assign one primary category per case and overlapping tags for image quality, document format and language variation. Include exact effective-date boundaries, superseded clauses, currency/excess arithmetic, duplicate submissions and unsupported injury claims.

The implemented `motor-v1` set is a smaller development precursor, not this 60-case deliverable. Its policies and coverage hypotheses require approval; no eligible/ineligible ground truth or financial rule output is provided. Keep a future independently reviewed held-out split separate from these public generator inputs/labels before measuring model or insurance accuracy.

The M5 runner evaluates 75 unique documents and 335 field labels, retaining duplicate scenario references without duplicate scoring weight. The original 366 annotations and 153 corpus files remain unchanged. The oracle fixture copies known answers and reports no measured latency/tokens/cost. The [benchmark methodology](document-intelligence-benchmark.md#scoring-methodology--field-v1) defines denominators; simulated conformance cannot satisfy the proposed live quality gates below.

M8's [30-query development set](../../data/evaluation/policy-retrieval/README.md) has authored source-based relevance/citation expectations, not independently adjudicated ground truth. Its real local lexical measurements at k=3 keep no-answer, policy-safety, invalid-query and technical-failure cohorts separate. These diagnostics do not complete the proposed independently reviewed recall@5 gate, evaluate answer grounding or measure semantic/hybrid RAG. [M8 results](../milestones/milestone-8.md#measured-offline-results) include all observed failures.

Each case will contain generated artifacts with hashes, a synthetic policy bundle/rule version, labeled critical fields (policy ID, loss date, vehicle reference, estimate amount/currency), relevant clause IDs, expected rule results, expected routing and prohibited actions. Labels must be independently reviewed where feasible; disclose single-maintainer review. Separate development and held-out cases; track changes without silently rewriting expected outputs.

Every evaluation run will record source revision or pre-Git content hashes, dataset manifest/hash, schema/rules/policy/index versions, model/deployment/version, inference parameters, prompts, tools, package lock, environment and evaluator versions. Repeat probabilistic steps three times per held-out case; report all runs and worst-case safety failures. Fixed inputs and manifests make runs comparable, not bitwise deterministic. Distinguish local stub results (**SIMULATED**) from actual service tests (**TESTED**); current foundation unit tests establish neither service-integration nor golden-evaluation evidence.

## Proposed acceptance metrics

| Area | Measurement and initial gate |
| --- | --- |
| Critical extraction | At least 95% normalized exact-match accuracy over labeled fields, with missing predictions counted as errors; report per-field accuracy and difficult-input slices |
| Retrieval | Relevant-clause recall@5 at least 95% on labeled queries; zero clauses outside the authorized resolved policy bundle; report denominator and empty-result rate |
| Rules | 100% exact agreement on rule IDs/results/calculations; missing facts yield `undetermined`; no dependence on model text |
| Grounding | 100% of material recommendation facts have resolvable supporting evidence; all policy citations match the resolved version; reviewer verifies support, not merely citation syntax |
| Oversight/safety | 100% of labeled ambiguous/high-risk cases routed correctly; zero unauthorized writes, cross-case disclosures or autonomous outcomes across the release suite |
| Human outcomes | 100% of closures have authorized reviewer, current assessment revision, reason and audit event; stale approvals rejected |
| Recovery | No lost acknowledged cases or duplicate outcomes in restart/replay tests; failed dependencies never become a positive coverage result |
| Usability/performance | For valid cases up to 10 pages and 5 photos, propose p95 reviewer-packet readiness under 120 seconds at 2 concurrent cases, excluding human wait; cold starts reported separately |
| Business/cost | Compare paired active handling times against the charter target; report tokens, pages, request counts, estimated GBP/case and fixed service costs separately |

Aggregate accuracy cannot waive a safety failure. Report counts, denominators, per-slice results and uncertainty; a small synthetic suite cannot establish real-world reliability. LLM judging may assist explanation scoring but cannot establish rule correctness or authorize outcomes. Cost ceilings require an approved budget and price assumptions before paid tests; none is set or incurred here.

## Telemetry and audit evidence

Use OpenTelemetry with an Azure Monitor/Application Insights export path; verify the supported Python integration when dependencies are selected ([Microsoft configuration guidance](https://learn.microsoft.com/en-us/azure/azure-monitor/app/opentelemetry-configuration/)). Propagate W3C trace context across HTTP, outbox and queue boundaries, and link retries to the original operation.

Planned spans: intake, upload validation/scan, extraction, policy resolution, retrieval, each agent/model/tool call, rule evaluation, review action and recovery. Record opaque case/run/evidence IDs, service/environment/version, duration, result code, retry count, model/prompt/tool/rule/index versions, token/page counts and normalized error category. Do not record raw evidence, prompts/responses, credentials, signed URLs or chain-of-thought. Keep case IDs out of metric labels to avoid high cardinality.

Dashboards/alerts will cover API errors, queue depth/oldest age, dead letters, extraction failures, empty retrieval, wrong-version blocks, validation failures, model throttling, tool denials, review backlog, audit-write failures, token use and spend estimates. Operators own dependency/backlog alerts; supervisors own review backlog. Initial thresholds require baseline calibration; failed audit writes block outcome commits. Sampling may reduce routine traces, but the separate business audit ledger must retain every decision event. Test telemetry redaction and missing-span detection.

## Failure engineering and release approach

| Scenario | Required behavior and verification |
| --- | --- |
| Model/Document Intelligence 429, timeout or outage | Honor retry hints with bounded exponential backoff/jitter; enforce deadlines/circuit breaker; leave recoverable state and visible reason |
| Search outage, empty results or wrong version | Abstain and route to review; never widen filters or substitute another policy |
| Malicious file or injected tool/document instructions | Quarantine or flag; no unauthorized tool call or external egress; supervisor review |
| Duplicate queue delivery or worker crash | Replay by idempotent step key; checkpoint safely; no duplicate outcome or missing audit event |
| Database/audit or publication failure | Fail closed for outcomes; atomic outbox commit; retry delivery without losing acknowledged work |
| Stale reviewer, revised evidence or rules | Reject stale writes; invalidate assessment and require fresh review |
| APIM unavailable or token expired | Deny protected tool use; no deployed direct-access bypass; local stubs remain explicitly simulated |
| Telemetry outage or runaway usage | Bounded telemetry buffering without payload leakage; audit persists separately; suspend new model work at configured usage limits |

Implementation will progress through schema/rule unit tests, component contract tests, local synthetic integration, held-out evaluation, security/failure tests and authorized Azure smoke tests. Publish run manifests, failures and limitations before any release claim. Gate model/prompt/rule/tool changes on regression evidence; allow threshold changes only through recorded review. See [roadmap](../milestones/roadmap.md).

## Implemented offline workflow evidence — M12

The [workflow](../architecture/deterministic-claims-workflow.md) records immutable stage/attempt outcomes, correlation IDs, input/output/previous hashes, M2 transitions, M6 admissions and available governed-agent results. [Workflow tests](../../tests/test_workflow.py) cover stage order, duplicate/concurrent execution, checkpoint replay/tampering, retries, cancellation, timeouts, provenance, cross-case denial and human/supervisor routing. The reproducible CLI includes injected source content and simulated outages. These local checks extend failure-contract evidence; they do not satisfy live model, distributed queue, throughput, restore/recovery or telemetry release gates above.

Transition times and scan/identity/reviewer facts are synthetic caller assertions. Hashes are content bindings, not signed execution evidence. Checkpoints include synthetic content and require protected trusted storage; they are not operational logs. No OpenTelemetry exporter, Application Insights trace, dashboard, alert, persistent audit or model-quality measurement is implemented. Interrupted SDK attempt counts can be unavailable and are never zero-filled. [M12 evidence](../milestones/milestone-12.md) distinguishes actual SDK dispatch from simulated chat and records final validation.
