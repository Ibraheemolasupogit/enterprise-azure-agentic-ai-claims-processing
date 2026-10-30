# Requirements traceability

Status: **Requirements baselined in Milestone 3; dataset mapping added in Milestone 4**. Every row maps a requirement to its business parent, actual foundation symbols, planned capability and verification. **PARTIAL** means a narrow contract/local guard is implemented and tested, not that the end-to-end requirement is satisfied. **PLANNED** means no enforcing adapter/workflow exists; a protocol/model is not runtime evidence. Original foundation results are recorded in [Milestone 2](../milestones/milestone-2.md#verification); they were rerun within the expanded [Milestone 4 suite](../milestones/milestone-4.md#verification), not promoted into service-integration evidence.

Milestone 4 adds the [dataset evidence mapping](#milestone-4-dataset-evidence) below. The original requirement IDs/acceptance criteria and future VT specifications remain unchanged; dataset validation alone does not satisfy their planned runtime behavior. The 115-test count in historical rows is the M2 baseline, not the current expanded suite.

Definitions: [business requirements](project-charter.md#business-requirements), [FR/NFR acceptance](requirements.md), [target architecture](../architecture/target-architecture.md). Foundation symbols are qualified by module and link to their real source file. Future `VT-*` IDs below are stable verification specifications, **not existing test functions/files or passing results**.

| Requirement | Business parent | Actual contract/guard and current status | Remaining capability | Existing check / future verification |
| --- | --- | --- | --- | --- |
| FR-001 | BR-001, BR-004 | PARTIAL: [models.Claim](../../src/claims_ai/models.py) | Authenticated API, case assignment, repeat-submission protection | [test_invalid_claim_data](../../tests/test_models.py); VT-001 |
| FR-002 | BR-001, BR-004 | PARTIAL: [models.DocumentMetadata](../../src/claims_ai/models.py), [ports.DocumentProcessor](../../src/claims_ai/ports.py) (protocol only) | Byte validation, scanner, real extraction | [test_document_validation](../../tests/test_models.py), [test_image_metadata](../../tests/test_models.py); VT-002 |
| FR-003 | BR-001 | PARTIAL: [models.Evidence](../../src/claims_ai/models.py), [models.Case](../../src/claims_ai/models.py), [models.validate_required_evidence](../../src/claims_ai/models.py) | Approved checklist/thresholds and evidence-request workflow | [test_case_provenance](../../tests/test_models.py), [test_required_evidence_is_explicit_not_a_coverage_rule](../../tests/test_models.py); VT-003 |
| FR-004 | BR-002, BR-003 | PLANNED resolver; [models.Policy](../../src/claims_ai/models.py) validates supplied metadata only | Approved register/date/endorsement resolver and supervisor exception assignment | [test_policy_metadata](../../tests/test_models.py) (metadata only); VT-004 |
| FR-005 | BR-002 | PARTIAL: [models.PolicyCitation](../../src/claims_ai/models.py), [models.Assessment](../../src/claims_ai/models.py); [ports.PolicyRetriever](../../src/claims_ai/ports.py) is a protocol | Filtered hybrid retrieval, content grounding and recall measurement | [test_exact_policy_citation](../../tests/test_models.py); VT-005 |
| FR-006 | BR-002 | PLANNED engine; [models.RuleResult](../../src/claims_ai/models.py) carries supplied results only | Policy/rule approval, deterministic rule evaluation and match enforcement | No rule-engine test exists; VT-006 |
| FR-007 | BR-001, BR-006 | PLANNED: [ports.EvidenceReconciliationService](../../src/claims_ai/ports.py) protocol | Bounded semantic reconciliation agent/output validation | No agent test exists; VT-007 |
| FR-008 | BR-002, BR-006 | PLANNED: [ports.PolicyExplanationService](../../src/claims_ai/ports.py) protocol | Grounded explanation agent and material-claim support validator | No agent test exists; VT-008 |
| FR-009 | BR-001, BR-003, BR-006 | PLANNED UI/workflow; [models.Case](../../src/claims_ai/models.py) carries source-linked snapshots | Packet generation, source inspection and correction workflow | No UI/packet test exists; VT-009 |
| FR-010 | BR-003 | PARTIAL: [models.ReviewerDecision](../../src/claims_ai/models.py), [lifecycle.TransitionActor](../../src/claims_ai/lifecycle.py), [lifecycle.transition_case](../../src/claims_ai/lifecycle.py) | Verified human identity/assignment and durable publication gate | [test_normal_lifecycle_requires_human_decision](../../tests/test_lifecycle.py), [test_service_actor_cannot_approve](../../tests/test_lifecycle.py), [test_invalid_or_stale_decisions](../../tests/test_lifecycle.py); VT-010 |
| FR-011 | BR-003 | PARTIAL: [models.Assessment.requires_supervisor](../../src/claims_ai/models.py), [models.validate_decision](../../src/claims_ai/models.py), [lifecycle.transition_case](../../src/claims_ai/lifecycle.py) | Supervisor assignment/notifications and authenticated enforcement | [test_escalation_cannot_be_bypassed](../../tests/test_lifecycle.py), [test_override_is_explicit_and_evidence_backed](../../tests/test_lifecycle.py), [test_high_risk_review_cannot_be_discarded_by_reviewer](../../tests/test_lifecycle.py); VT-011 |
| FR-012 | BR-001, BR-003, BR-005 | PARTIAL: [lifecycle.CaseTransition](../../src/claims_ai/lifecycle.py), [models.Case](../../src/claims_ai/models.py) | Atomic input changes and durable reprocessing/review | [test_recovery_restarts_validation](../../tests/test_lifecycle.py), [test_request_evidence_invalidates_snapshot_but_retains_history](../../tests/test_lifecycle.py), [test_reopen_and_quarantine_release_need_supervisor](../../tests/test_lifecycle.py); VT-012 |
| FR-013 | BR-003, BR-005 | PLANNED persistence; [ports.CaseRepository](../../src/claims_ai/ports.py) protocol and [lifecycle.CaseTransition](../../src/claims_ai/lifecycle.py) records | Atomic audit/outcome commit, concurrency and durable replay protection | [test_direct_transition_records_use_the_same_guards](../../tests/test_lifecycle.py) checks record validation only; VT-013 |
| FR-014 | BR-001, BR-003, BR-006 | PARTIAL local action: [models.DecisionAction](../../src/claims_ai/models.py), [models.ReviewerDecision](../../src/claims_ai/models.py) | Claimant status, handler requests and access-controlled demo interface | [test_request_evidence_invalidates_snapshot_but_retains_history](../../tests/test_lifecycle.py) (local only); VT-014 |
| FR-015 | BR-004 | PLANNED tools; [ports.PolicyRetriever](../../src/claims_ai/ports.py) and other protocols do not enforce runtime grants | Typed tool boundary, MCP/APIM, backend authorization | No gateway/tool-security test exists; VT-015 |
| NFR-001 | BR-004 | PARTIAL: [logging.redact_fields](../../src/claims_ai/logging.py), [logging.JsonFormatter](../../src/claims_ai/logging.py); synthetic marker/immutable contracts | Sensitive-upload detection, end-to-end redaction and approved deletion | [test_payloads_keys_messages_and_exception_text_never_escape](../../tests/test_logging.py), [test_frozen_and_private_representations](../../tests/test_models.py); VT-016 |
| NFR-002 | BR-003, BR-004 | PLANNED auth; [lifecycle.TransitionActor](../../src/claims_ai/lifecycle.py) accepts trusted assertions only | Entra, managed identity, case/role checks and audit-read grants | No authentication or cloud-RBAC test exists; VT-017 |
| NFR-003 | BR-003, BR-004 | PLANNED AI defenses; [models.RiskFlag](../../src/claims_ai/models.py) records supplied flags, not attack detection | Content isolation, injection detection/evaluation and bounded tools | [test_escalation_cannot_be_bypassed](../../tests/test_lifecycle.py) checks supplied flags only; VT-018 |
| NFR-004 | BR-005 | PARTIAL local recovery edges: [lifecycle.transition_case](../../src/claims_ai/lifecycle.py); persistence protocol unimplemented | Outbox/workers, retries/deadlines, dead letters and recovery | [test_recovery_restarts_validation](../../tests/test_lifecycle.py) (local only); VT-019 |
| NFR-005 | BR-003, BR-005 | PARTIAL: [logging.correlation_scope](../../src/claims_ai/logging.py), [logging.log_event](../../src/claims_ai/logging.py) | Distributed traces, owned alerts and separate audit retention | [test_structured_event_and_correlation](../../tests/test_logging.py), [test_async_contexts_are_isolated](../../tests/test_logging.py); VT-020 |
| NFR-006 | BR-002, BR-005, BR-006 | PLANNED business/model evaluation; foundation unit tests are not a golden dataset | Versioned held-out corpus, manifests and approved gates | No golden evaluation run exists; VT-021 |
| NFR-007 | BR-005, BR-006 | PLANNED measurement | Manual/target handling study and latency workload manifest | No performance/effort result exists; VT-022 |
| NFR-008 | BR-005 | PLANNED deployment/cost enforcement; [config.Settings](../../src/claims_ai/config.py) is local/test-only | Compatibility/quota matrix, budgets, usage caps and stop procedure | [test_safe_defaults](../../tests/test_config.py) validates defaults, not capacity/budgets; VT-023 |
| NFR-009 | BR-005 | PARTIAL: [pyproject.toml](../../pyproject.toml), [Makefile](../../Makefile) and historical M2 checks | Future change/regression gates and release evidence | M2 recorded 115 passing tests, strict typing, lint and package checks; VT-024 |

## Planned verification specifications

These specifications inherit the corresponding requirement's acceptance criterion. Implementations must attach actual test paths, manifests, environment and results before changing status; never rename a planned VT into historical evidence without a run.

| ID | Requirement | Required synthetic scenario/evidence |
| --- | --- | --- |
| VT-001 | FR-001 | Submit invalid inputs, duplicate authorized requests and a cross-case attempt; verify errors, access denial and one case identity. |
| VT-002 | FR-002 | Upload allowed, oversized, malformed, malicious and unscannable artifacts; prove extraction/model calls occur only after accepted validation. |
| VT-003 | FR-003 | Vary missing evidence, duplicate/hash/page/claim references and unknown fields; verify explicit gaps and no false completeness. |
| VT-004 | FR-004 | Resolve boundary-date/endorsement cases; missing/overlapping mappings create a supervisor exception without a fabricated bundle/assessment. |
| VT-005 | FR-005 | Query labeled clauses across two policy versions; verify exact-scope results, citation support, recall and outage/empty-result abstention. |
| VT-006 | FR-006 | After owner approval, run approved rule fixtures including unknown facts/version mismatch; compare exact results and deny prompt-owned rules. |
| VT-007 | FR-007 | Contradict form/estimate/photo facts and exhaust execution limits; inspect source-linked discrepancy output and no canonical mutation. |
| VT-008 | FR-008 | Ask for unsupported explanations and plant conflicting clauses; reject unsupported assertions and policy/decision authority changes. |
| VT-009 | FR-009 | Reviewer locates original evidence, rejects a suggestion and requests a correction; previous assessment cannot be used for closure. |
| VT-010 | FR-010 | Attempt agent/service, stale and mismatched-human approval; verify no published closure and inspect one valid human commit. |
| VT-011 | FR-011 | Exercise every supervisor decision-table row, assignment and handler bypass; reconstruct original assessment and explicit override. |
| VT-012 | FR-012 | Change input/policy versions, restart failed work and attempt quarantine/closed-case bypass; verify fresh validation and retained history. |
| VT-013 | FR-013 | Inject crashes, concurrent revisions and same/different-content duplicate events at commit boundaries; verify one auditable outcome. |
| VT-014 | FR-014 | Synthetic claimant sees only own evidence request/status and committed reasons; replacement evidence goes through validation. |
| VT-015 | FR-015 | Deny forbidden tools/IDs, expired gateway access and direct-backend bypass; verify no write/egress capability. |
| VT-016 | NFR-001 | Inspect logs for nested payload/secret leakage, reject accidental sensitive input and execute approved deletion/backup-expiry evidence. |
| VT-017 | NFR-002 | Wrong/expired identity, cross-case, operator/audit approval and unauthorized policy publication attempts are denied. |
| VT-018 | NFR-003 | Inject instructions in each content channel; verify no unauthorized action/exfiltration and supervisor handling of flagged outputs. |
| VT-019 | NFR-004 | Dependency timeout/throttle/outage and queue replay/restart preserve acknowledged cases and show bounded recovery/failure state. |
| VT-020 | NFR-005 | Trace one case across dependencies, trigger owned failure/backlog alerts and verify all decision audits survive trace sampling. |
| VT-021 | NFR-006 | Re-run a pinned held-out synthetic manifest; report labels, versions, denominators, slices and every safety failure against approved gates. |
| VT-022 | NFR-007 | Time paired manual/target cases under the documented workload and correction effort; publish quality alongside effort/latency, including misses. |
| VT-023 | NFR-008 | Review approved compatibility/cost record and test usage suspension/cleanup in a later authorized environment; do not spend merely to prove a document. |
| VT-024 | NFR-009 | For the next authorized code change, run applicable quality/package/regression checks and link their actual outputs to changed requirements. |

## Milestone 4 dataset evidence

The [motor-v1 guide](../../data/synthetic/motor/README.md) defines the authored expectations. All scenarios are development fixtures; no VT specification is promoted to complete merely because its inputs now exist.

| Requirements / future verification | Corpus support | Actual new test evidence / remaining gap |
| --- | --- | --- |
| FR-001/FR-013; VT-001/VT-013 | 12 submissions, 11 claims; SCN-10 reuses SCN-01 payload with a new submission ID | [test_duplicate_reuses_exact_payload](../../tests/test_dataset.py); no API/store idempotency demonstrated |
| FR-002/FR-003; VT-002/VT-003 | PDF/PNG artifacts, source/hash/page labels, SCN-03/04 missing evidence | [test_integrity_and_exact_regeneration](../../tests/test_dataset.py), [test_corrupt_corpus_rejected](../../tests/test_dataset.py); no scanner/extraction accuracy claim |
| FR-004/FR-005; VT-004/VT-005 | Two draft versions, conflict/expired/wrong-version/exact-boundary cases | [test_policy_version_labels_are_metadata_not_coverage](../../tests/test_dataset.py); no production resolver, Search or retrieval recall run |
| FR-006/FR-011; VT-006/VT-011 | Draft X01 and authored high-risk/escalation labels; all coverage outcomes null | [test_schema_compatibility_and_no_processed_evidence](../../tests/test_dataset.py), [test_distinct_scenario_inventory](../../tests/test_dataset.py); no approved rule/financial engine or executed routing |
| FR-007/FR-008/NFR-003; VT-007/VT-008/VT-018 | Conflicting facts and SCN-11 visible untrusted instructions with source provenance | [test_untrusted_payload_is_labeled_data](../../tests/test_dataset.py); no agent, detector or adversarial model evaluation |
| NFR-001/NFR-006/NFR-009; VT-016/VT-021/VT-024 | Synthetic provenance markers, typed versioned annotations, schema, manifest, code fingerprint and seeded reproduction | [test_reproducible_for_seed](../../tests/test_dataset.py), [test_bad_ground_truth_rejected](../../tests/test_dataset.py), [test_rehashed_but_false_extraction_label_rejected](../../tests/test_dataset.py); no independent held-out labels, real-data certification or service-performance result |
