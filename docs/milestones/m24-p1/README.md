# M24 P1 — Offline capability and evidence catalogue

**Coverage: M1–M23 (23/23). Baseline: `11a64399d8e0166d2e1087dcb8e43242a7a7b711`.** These new catalogue documents are not part of that commit. P1 is documentation/file-hash processing only; M24 is not complete and P2 has not started. No application demonstration, dataset/evidence generator, scorer, test suite, SDK client, package installation, network, Docker/build or Azure operation was run.

The catalogue distinguishes **implemented behaviour**, **historically reported validation** and **independently accepted operational outcomes**. Local scope acceptance, an independent installed-wheel test or a host-supplied synthetic approval is not independent business/security/quality acceptance. No reviewer, approval or signature is invented.

## Reading the evidence

- [Machine catalogue](catalogue.json): capability, references, environment, last recorded result, limitations and approval/gap fields for every milestone.
- [Full evidence hashes](evidence-hashes.json): full SHA-256 values, original expected pins/sources where available, Git blob binding and availability. Hash prefixes below are abbreviated; the JSON retains complete digests.
- [P1 verification](verification.json): document/hash checks and preservation only; no runtime or acceptance result.
- **GIT_TRACKED** means present in commit `11a6439`; **IGNORED_LOCAL_ONLY** means present on this host but absent from a fresh Git checkout; **MISSING/UNLOCATED** gaps have no located receipt/path and no invented hash. Directory references have no single file digest.
- **MATCHES_RECORDED_SHA256** compares bytes with a cited historical pin. **CURRENT_BYTES_MATCH_BOUND_GIT_BLOB** binds current tracked bytes. **OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED** is a new catalogue observation, not retrospective proof; it does not assert that no other historical pin exists. None establishes upstream authenticity or fresh execution.
- Implementation references point to the current baseline, not necessarily the source snapshot that produced an old report. Whole-package fingerprints and dependency environments changed across milestones. Validation dates are taken only from cited records; filesystem timestamps are not validation dates.
- This is a selected evidence catalogue, not a copy of all raw archives. Linked local reports remain ignored; P1 does not make them publicly available or redistribute binaries/databases. M22 labels/narratives are not reproduced in the catalogue or introduced into prediction inputs.

## Preserved historical boundaries

- **M8:** Q-007/Q-012/Q-015/Q-029 remain failures; the frozen report retains 26/30 authored-expectation conformance.
- **M12:** cooperative wall-clock deadlines can alter retry/history bytes. M13's earlier 575-pass/one-failure attempt remains part of the record; matching frozen bytes do not repair timing sensitivity.
- **M19:** original 79 PASS / 1 FAIL / 8 NOT_TESTED and corrected **80 PASS / 0 FAIL / 8 NOT_TESTED** remain separate, with F-002 checks outside the 88-case catalog.
- **M22:** 60 cases remain **PENDING_REVIEW** and 12 independent-quality gates **NOT_TESTED**; no holdout release/scoring, independent labels or approvals.
- **M23:** **DEFERRED — SECURITY GATE NO-GO**. B1 refusal, 1 GiB cap and zero-unresolved-Critical/High requirements remain unchanged.

## Coverage index

| Milestone | Capability | Current scoped status |
| --- | --- | --- |
| [M1](#m1) | Charter and architecture baseline | DOCUMENTED_ONLY |
| [M2](#m2) | Python engineering foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M3](#m3) | Business process and architecture refinement | DOCUMENTED_ONLY |
| [M4](#m4) | Synthetic motor claims dataset and ground truth | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M5](#m5) | Document intelligence benchmark foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M6](#m6) | Structured claims evidence processing | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M7](#m7) | Policy knowledge ingestion and retrieval foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M8](#m8) | Policy retrieval and RAG evaluation foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M9](#m9) | Deterministic motor claims rules foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M10](#m10) | Microsoft Agent Framework foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M11](#m11) | Governed agent tools and contract testing | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M12](#m12) | Deterministic claims workflow orchestration | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M13](#m13) | Governed MCP server foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M14](#m14) | MCP HTTP transport and APIM governance foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M15](#m15) | Governed human review workflow | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M16](#m16) | Governed FastAPI claims application foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M17](#m17) | Governed claims reviewer operations UI | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M18](#m18) | Identity and security foundation | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M19](#m19) | AI threat model and adversarial security testing | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M20](#m20) | Durable human case outcomes and recovery | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M21](#m21) | Security and identity hardening | IMPLEMENTED_WITHIN_RECORDED_OFFLINE_SCOPE |
| [M22](#m22) | Reproducible quality and operations | CONDITIONAL_OFFLINE_ENGINEERING |
| [M23](#m23) | Governed Azure deployment | DEFERRED_SECURITY_GATE_NO_GO |

<a id="m1"></a>

## M1 — Charter and architecture baseline

Fictional motor-claims charter, target architecture, security/evaluation/deployment plans and repository exclusions; documentation only.

**Implementation at the bound commit:** [docs/business/project-charter.md](../../business/project-charter.md), [docs/architecture/target-architecture.md](../../architecture/target-architecture.md), [docs/architecture/security-and-governance.md](../../architecture/security-and-governance.md), [docs/quality/evaluation-and-observability.md](../../quality/evaluation-and-observability.md).

**Historical scope/validation records:** [docs/milestones/milestone-1.md](../milestone-1.md).

**Environment:** Documentation/file checks; no runtime environment or executable verification claimed.

**Last recorded status, not rerun by P1:** 2026-10-30: nine-document/file/link/whitespace checks reported; no runtime tests.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-1.md](../milestone-1.md) | GIT_TRACKED | `2afe0b04ab521e06…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Fictional operating model and provisional business targets are not observed insurer outcomes. Architecture is a target; later delivered scopes must be read separately.

**Blockers/approvals:** Owner review before implementation or deployment; no independent operational acceptance established.

**Unlocated/local-publication gaps:** G01; see the gap register below.

<a id="m2"></a>

## M2 — Python engineering foundation

Typed synthetic contracts, immutable validation, lifecycle/human-supervisor guards, local settings/redacted logging and adapter protocols.

**Implementation at the bound commit:** [src/claims_ai/models.py](../../../src/claims_ai/models.py), [src/claims_ai/lifecycle.py](../../../src/claims_ai/lifecycle.py), [src/claims_ai/config.py](../../../src/claims_ai/config.py), [src/claims_ai/logging.py](../../../src/claims_ai/logging.py), [src/claims_ai/ports.py](../../../src/claims_ai/ports.py), [tests/test_models.py](../../../tests/test_models.py).

**Historical scope/validation records:** [docs/milestones/milestone-2.md](../milestone-2.md).

**Environment:** macOS, Python 3.12.8, Pydantic 2.11.7; original venv reused host packages. Independent project-wheel checks shared host dependencies.

**Last recorded status, not rerun by P1:** 2026-10-30: 115 source and 115 independent-wheel tests, Ruff/mypy and package inclusion/rebuild checks reported.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-2.md](../milestone-2.md) | GIT_TRACKED | `0289e1d1ac37cd82…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Library contracts and trusted assertions are not an API, authenticated roles, live processing or durable transactions. Hashes in domain metadata are not original-byte verification; serialisation is not redaction.

**Blockers/approvals:** Real identity, policy approval, persistence and external adapters require separately scoped implementation/review.

**Unlocated/local-publication gaps:** G02; see the gap register below.

<a id="m3"></a>

## M3 — Business process and architecture refinement

Requirements FR-001–FR-015/NFR-001–NFR-009, fictional process/roles, traceability, risks and deterministic/human authority ADR.

**Implementation at the bound commit:** [docs/business/requirements.md](../../business/requirements.md), [docs/business/traceability-matrix.md](../../business/traceability-matrix.md), [docs/business/risk-register.md](../../business/risk-register.md), [docs/architecture/decisions/0001-decision-authority.md](../../architecture/decisions/0001-decision-authority.md).

**Historical scope/validation records:** [docs/milestones/milestone-3.md](../milestone-3.md).

**Environment:** Static document/AST/file checks; no new runtime validation environment claimed.

**Last recorded status, not rerun by P1:** 2026-10-30: 14 documents, 157 links/anchors and 60 symbols checked; no new runtime test run. M2's 115-test result is historical.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-3.md](../milestone-3.md) | GIT_TRACKED | `9a049e9caa2c2363…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Planned verification specifications do not establish requirement satisfaction or regulatory compliance.

**Blockers/approvals:** Named operating-model roles are responsibilities, not staffed reviewers or accepted risks.

**Unlocated/local-publication gaps:** G03; see the gap register below.

<a id="m4"></a>

## M4 — Synthetic motor claims dataset and ground truth

Seeded PDF/PNG/native-text authoring, 12 development scenarios, draft policies and source-linked authored labels.

**Implementation at the bound commit:** [src/claims_ai/dataset](../../../src/claims_ai/dataset), [data/synthetic/motor/README.md](../../../data/synthetic/motor/README.md), [tests/test_dataset.py](../../../tests/test_dataset.py).

**Historical scope/validation records:** [docs/milestones/milestone-4.md](../milestone-4.md).

**Environment:** Python 3.12.8/Pydantic 2.11.7; native macOS PDFKit and pre-existing Pillow for artifact inspection.

**Last recorded status, not rerun by P1:** 2026-10-30: 149 source tests; two 153-file generations equal; PDFKit inspected 65 PDFs and existing Pillow inspected ten PNGs, as historically reported.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-4.md](../milestone-4.md) | GIT_TRACKED | `da9bd9cc169d4256…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [data/synthetic/motor/v1/manifest.json](../../../data/synthetic/motor/v1/manifest.json) | GIT_TRACKED | `0fa7439208fb8d08…`; MATCHES_RECORDED_SHA256 |
| [data/synthetic/motor/v1/ground_truth.json](../../../data/synthetic/motor/v1/ground_truth.json) | GIT_TRACKED | `2c7490c34daca763…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Single-author development labels, simple layouts and schematic images are not independent holdout truth, OCR performance or policy approval. Case documents remain quarantined; coverage outcomes remain null.

**Blockers/approvals:** Independent label/domain/policy review and a genuinely held-out quality scope are outstanding.

**Unlocated/local-publication gaps:** G04; see the gap register below.

<a id="m5"></a>

## M5 — Document intelligence benchmark foundation

Versioned extraction/scoring contracts, denominators/cohorts, clean failures and a deterministic oracle fixture CLI.

**Implementation at the bound commit:** [src/claims_ai/benchmark](../../../src/claims_ai/benchmark), [docs/quality/document-intelligence-benchmark.md](../../quality/document-intelligence-benchmark.md), [tests/test_benchmark_runner.py](../../../tests/test_benchmark_runner.py).

**Historical scope/validation records:** [docs/milestones/milestone-5.md](../milestone-5.md).

**Environment:** Recorded reuse: Python 3.12.8/Pydantic 2.11.7/pytest 8.4.1; OS is not independently restated in this milestone.

**Last recorded status, not rerun by P1:** 202 tests and lint/type/package checks reported; source/wheel fixture reports reproduced. All extraction responses are SIMULATED; latency/usage remain null.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-5.md](../milestone-5.md) | GIT_TRACKED | `5837166b82f16918…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/benchmarks/m5-fixture-a.json](../../../outputs/benchmarks/m5-fixture-a.json) | IGNORED_LOCAL_ONLY | `bdc5031bc5ec7a99…`; MATCHES_RECORDED_SHA256 |
| [outputs/benchmarks/m5-fixture-pdf-only.json](../../../outputs/benchmarks/m5-fixture-pdf-only.json) | IGNORED_LOCAL_ONLY | `bca2a196f0a2e9d6…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Oracle labels do not establish live parser/provider quality, cost or latency; unsupported images are excluded explicitly. The phrase 'approved annotations' in M5 preservation prose is not evidence of independent approval; M4 explicitly identifies authored development labels.

**Blockers/approvals:** Provider implementation/calls and independent label/quality acceptance require separate scope and approval.

<a id="m6"></a>

## M6 — Structured claims evidence processing

Deterministic typed mapping, source/hash/ownership checks, normalisation, quarantine/quality holds and guarded local evidence history/admission.

**Implementation at the bound commit:** [src/claims_ai/evidence](../../../src/claims_ai/evidence), [docs/architecture/structured-evidence-processing.md](../../architecture/structured-evidence-processing.md), [tests/test_evidence.py](../../../tests/test_evidence.py).

**Historical scope/validation records:** [docs/milestones/milestone-6.md](../milestone-6.md).

**Environment:** Recorded reuse: Python 3.12.8/Pydantic 2.11.7; existing simulated extraction fixtures, no live scanner/provider.

**Last recorded status, not rerun by P1:** 251 tests and lint/type/package checks reported. Frozen fixture report: 82 attempts, 75 quarantined, seven duplicates, 334 proposals, zero accepted-history records and no case admission.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-6.md](../milestone-6.md) | GIT_TRACKED | `29415e8ea0a509e5…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/evidence/m6-verified-a.json](../../../outputs/evidence/m6-verified-a.json) | IGNORED_LOCAL_ONLY | `92b00d6b8aa5e865…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Generated single-page source verification is not general PDF/OCR, authentic scan certification or operational admission. Caller-held history is not durable service storage.

**Blockers/approvals:** Authenticated intake/scan/provider assertions and operational integration require separate approval.

<a id="m7"></a>

## M7 — Policy knowledge ingestion and retrieval foundation

Draft-policy parsing, deterministic lexical chunks/citations, exact case/policy/version/date filters and explicit abstention.

**Implementation at the bound commit:** [src/claims_ai/knowledge](../../../src/claims_ai/knowledge), [docs/architecture/policy-knowledge-retrieval.md](../../architecture/policy-knowledge-retrieval.md), [tests/test_knowledge.py](../../../tests/test_knowledge.py).

**Historical scope/validation records:** [docs/milestones/milestone-7.md](../milestone-7.md).

**Environment:** Recorded reuse: Python 3.12.8/Pydantic 2.11.7; local authored PDF/source pairs and unsigned snapshots.

**Last recorded status, not rerun by P1:** 296 tests and lint/type/package checks reported; 36 queries, 20 retrieved/16 abstained, 110 chunks and 20 returned citation checks. These are mechanics counts, not independent quality.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-7.md](../milestone-7.md) | GIT_TRACKED | `105e190d7cfa8883…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/knowledge/m7-verified-a.json](../../../outputs/knowledge/m7-verified-a.json) | IGNORED_LOCAL_ONLY | `0169ba38660ce7cc…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** No approved policy register/resolver, semantic contradictions, hybrid search, embeddings or signed publication.

**Blockers/approvals:** Policy-owner approval, authentic source/register authority and independent relevance evaluation remain required.

<a id="m8"></a>

## M8 — Policy retrieval and RAG evaluation foundation

Frozen authored query expectations, separate input/label paths, lexical metrics/cohorts and honest per-query failure reports.

**Implementation at the bound commit:** [src/claims_ai/retrieval_eval](../../../src/claims_ai/retrieval_eval), [docs/quality/policy-retrieval-evaluation.md](../../quality/policy-retrieval-evaluation.md), [tests/test_retrieval_eval.py](../../../tests/test_retrieval_eval.py).

**Historical scope/validation records:** [docs/milestones/milestone-8.md](../milestone-8.md).

**Environment:** Recorded reuse: Python 3.12.8/Pydantic 2.11.7; authored native-text lexical evaluation, no live model/search service.

**Last recorded status, not rerun by P1:** 325 tests reported. Preserved OFFLINE_LEXICAL result: 26/30 authored expectations met; Q-007/Q-012/Q-015/Q-029 remain failures. Fourteen citations/version bindings checked, not general retrieval accuracy.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-8.md](../milestone-8.md) | GIT_TRACKED | `01d3ef7390a4de09…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/retrieval-eval/m8-verified-a.json](../../../outputs/retrieval-eval/m8-verified-a.json) | IGNORED_LOCAL_ONLY | `e1b45e98dc8d9e8d…`; MATCHES_RECORDED_SHA256 |
| [data/evaluation/policy-retrieval/v1/queries.json](../../../data/evaluation/policy-retrieval/v1/queries.json) | GIT_TRACKED | `91b04bb8b8fd73b0…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Authored labels are not independently adjudicated; synonym miss, two false-positive no-answer cases and an irrelevant extra hit remain. Quoted injection text is inert data, not observed command execution.

**Blockers/approvals:** Independent relevance/holdout review and any new release thresholds require explicit approval; preserve the four failures.

<a id="m9"></a>

## M9 — Deterministic motor claims rules foundation

Six versioned provisional rules, exact source/policy/evidence binding, four-state findings and non-binding integer-pence illustrations.

**Implementation at the bound commit:** [src/claims_ai/rules](../../../src/claims_ai/rules), [docs/architecture/deterministic-provisional-rules.md](../../architecture/deterministic-provisional-rules.md), [tests/test_rules.py](../../../tests/test_rules.py).

**Historical scope/validation records:** [docs/milestones/milestone-9.md](../milestone-9.md).

**Environment:** Recorded reuse: Python 3.12.8/Pydantic 2.11.7; supplied synthetic scan/reviewer/classification assertions.

**Last recorded status, not rerun by P1:** 385 tests reported; 23 scenarios/138 findings; zero final outcomes and zero settlement authority. FAIL rule findings are not failed software tests or approved claim denials.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-9.md](../milestone-9.md) | GIT_TRACKED | `f4b2253502d90ffc…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/rules/m9-verified-a.json](../../../outputs/rules/m9-verified-a.json) | IGNORED_LOCAL_ONLY | `2460f9e54a485a2e…`; MATCHES_RECORDED_SHA256 |
| [data/rules/motor/v1/specification.json](../../../data/rules/motor/v1/specification.json) | GIT_TRACKED | `47398a0a1161ddfd…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Policy parameters, cause/category labels and financial illustrations remain fictional/unapproved; no operational Assessment or autonomous decision is produced.

**Blockers/approvals:** Real policy/rule publication and semantic labels require independent owner/domain review.

<a id="m10"></a>

## M10 — Microsoft Agent Framework foundation

Actual pinned SDK with one bounded advisory assistant, typed results, read-only packet tool and scripted offline client.

**Implementation at the bound commit:** [src/claims_ai/agents](../../../src/claims_ai/agents), [docs/architecture/agent-framework-foundation.md](../../architecture/agent-framework-foundation.md), [tests/test_agents.py](../../../tests/test_agents.py).

**Historical scope/validation records:** [docs/milestones/milestone-10.md](../milestone-10.md).

**Environment:** Isolated Python 3.12.8, Agent Framework 1.23.0, Pydantic 2.14.2, pytest 8.4.2; shared pinned dependencies for wheel verification.

**Last recorded status, not rerun by P1:** 422 source and independent-wheel tests reported; deterministic SDK report. M5–M9 later-environment reruns change runtime metadata, not the preserved original files.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-10.md](../milestone-10.md) | GIT_TRACKED | `11a36357ac0506ca…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/agents/m10-final-a.json](../../../outputs/agents/m10-final-a.json) | IGNORED_LOCAL_ONLY | `74aad58a9a47340f…`; MATCHES_RECORDED_SHA256 |
| [requirements/m10-constraints.txt](../../../requirements/m10-constraints.txt) | GIT_TRACKED | `e874b059915a894b…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Real SDK execution with SIMULATED client responses is not live reasoning, prompt-injection resistance or extraction quality. No autonomous outcomes; human authority unchanged.

**Blockers/approvals:** Live provider/model calls, cost scope and independent quality require separate authorisation.

<a id="m11"></a>

## M11 — Governed agent tools and contract testing

Three real SDK read-only functions over verified evidence, exact clauses and provisional findings; case-bound host grants and bounded dispatch.

**Implementation at the bound commit:** [src/claims_ai/agent_tools](../../../src/claims_ai/agent_tools), [docs/architecture/governed-agent-tools.md](../../architecture/governed-agent-tools.md), [tests/test_agent_tools.py](../../../tests/test_agent_tools.py).

**Historical scope/validation records:** [docs/milestones/milestone-11.md](../milestone-11.md).

**Environment:** Isolated Python 3.12.8, Agent Framework 1.23.0/msgspec 0.22.0/Pydantic 2.14.2; no live model.

**Last recorded status, not rerun by P1:** 478 source and independent-wheel tests reported; ten-case scripted SDK demonstration with successful and safe-error controls.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-11.md](../milestone-11.md) | GIT_TRACKED | `fbdc735140b49418…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/agent-tools/m11-verified-a.json](../../../outputs/agent-tools/m11-verified-a.json) | IGNORED_LOCAL_ONLY | `388a0c3a03d4c5a7…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Host grants are synthetic assertions, not an authentication service; no policy activation, remote gateway or claim authority.

**Blockers/approvals:** Authenticated service identity, distribution/egress and live-provider use require separate review.

<a id="m12"></a>

## M12 — Deterministic claims workflow orchestration

Six host-controlled stages, bounded retry/cancellation, immutable correlated records and caller-held resumable checkpoints.

**Implementation at the bound commit:** [src/claims_ai/workflow](../../../src/claims_ai/workflow), [docs/architecture/deterministic-claims-workflow.md](../../architecture/deterministic-claims-workflow.md), [tests/test_workflow.py](../../../tests/test_workflow.py).

**Historical scope/validation records:** [docs/milestones/milestone-12.md](../milestone-12.md).

**Environment:** Isolated Python 3.12.8, Agent Framework 1.23.0/Pydantic 2.14.2; real cooperative wall-clock deadlines and SIMULATED model client.

**Last recorded status, not rerun by P1:** 531 source and independent-wheel tests reported. Frozen matching reports are historical observations, not a guarantee of repeated byte identity under timing variation.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-12.md](../milestone-12.md) | GIT_TRACKED | `51e0d9e45f5092a6…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/workflow/m12-verified-a.json](../../../outputs/workflow/m12-verified-a.json) | IGNORED_LOCAL_ONLY | `ec0c6c47f439dfd0…`; MATCHES_RECORDED_SHA256 |
| [outputs/workflow/m12-verified-b.json](../../../outputs/workflow/m12-verified-b.json) | IGNORED_LOCAL_ONLY | `ec0c6c47f439dfd0…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Cooperative timing can add a retry/history difference despite the same safe terminal state; M13 records a 575-pass/one-failure wheel attempt caused by this limit. Checkpoints are caller-held/unsigned; no queue-wait deadline, hard preemption, cloud durability or operational assessment/outcome.

**Blockers/approvals:** Timing/timeout semantics must not be weakened for a demo; new state must use current runtime/context. Durable/cloud workflow changes require separate scope.

<a id="m13"></a>

## M13 — Governed MCP server foundation

Actual pinned MCP stdio server, three governed reads, native/framework clients and server-side scope/budget guards.

**Implementation at the bound commit:** [src/claims_ai/mcp_server](../../../src/claims_ai/mcp_server), [docs/architecture/governed-mcp-server.md](../../architecture/governed-mcp-server.md), [tests/test_mcp_server.py](../../../tests/test_mcp_server.py).

**Historical scope/validation records:** [docs/milestones/milestone-13.md](../milestone-13.md).

**Environment:** Python 3.12.8, MCP 2.2.0/Agent Framework 1.23.0, local stdio and synthetic host grant; no network service.

**Last recorded status, not rerun by P1:** 576 source/wheel tests in final run; prior 575-pass/one-M12-timing-failure run explicitly retained in narrative. Native MCP and Agent Framework discovery/calls are real.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-13.md](../milestone-13.md) | GIT_TRACKED | `792943f8cfc98a87…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/mcp/m13-verified-a.json](../../../outputs/mcp/m13-verified-a.json) | IGNORED_LOCAL_ONLY | `19529fe8591ca374…`; MATCHES_RECORDED_SHA256 |
| [requirements/m13-wheel-manifest.json](../../../requirements/m13-wheel-manifest.json) | GIT_TRACKED | `284f2d24ff4a4c16…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Trusted launcher/context and OS are the trust root; no signed user authentication, APIM, resource sandbox or live model. M12 timing sensitivity remains.

**Blockers/approvals:** Remote transport/identity/gateway and hostile-code isolation require separate scope and evidence.

<a id="m14"></a>

## M14 — MCP HTTP transport and APIM governance foundation

Actual Streamable HTTP over governed reads, synthetic gateway identity/host binding, static XML/Bicep and fail-closed protocol checks.

**Implementation at the bound commit:** [src/claims_ai/mcp_http](../../../src/claims_ai/mcp_http), [infra/apim](../../../infra/apim), [docs/architecture/mcp-http-and-gateway.md](../../architecture/mcp-http-and-gateway.md), [tests/test_mcp_http.py](../../../tests/test_mcp_http.py).

**Historical scope/validation records:** [docs/milestones/milestone-14.md](../milestone-14.md).

**Environment:** Python 3.12.8/MCP 2.2.0/Agent Framework 1.23.0; ASGI inside sandbox, supplied loopback report from a permitted external terminal. No new TCP test in P1.

**Last recorded status, not rerun by P1:** Initial 629 source/wheel, corrected 644 source, final 69 focused source and 645 installed-wheel tests are separate snapshots; no final full-source 645 run is invented. Supplied real TCP report is historical source-matched evidence.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-14.md](../milestone-14.md) | GIT_TRACKED | `9490ef19f2713005…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/mcp-http/m14-verified-a.json](../../../outputs/mcp-http/m14-verified-a.json) | IGNORED_LOCAL_ONLY | `7a45bb661db5c609…`; MATCHES_RECORDED_SHA256 |
| [outputs/mcp-http/m14-loopback-verification.json](../../../outputs/mcp-http/m14-loopback-verification.json) | IGNORED_LOCAL_ONLY | `5f373df8044bda5b…`; MATCHES_RECORDED_SHA256 |
| [outputs/packages/m14-final/northstar_claims_ai-0.1.0-py3-none-any.whl](../../../outputs/packages/m14-final/northstar_claims_ai-0.1.0-py3-none-any.whl) | IGNORED_LOCAL_ONLY | `1e480b90640d4b5a…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Pre-correction ASGI report is not evidence of corrected runtime; older TCP report does not verify later identity/current-code changes. No independent closed-port/shutdown-health probe, real Entra/APIM/TLS or cloud enforcement.

**Blockers/approvals:** Any socket/container/cloud verification and real gateway/identity integration require separate approval.

<a id="m15"></a>

## M15 — Governed human review workflow

Assigned synthetic advisory queue/detail, reviewer/supervisor separation, stale/CAS checks and immutable process-local review audit.

**Implementation at the bound commit:** [src/claims_ai/human_review](../../../src/claims_ai/human_review), [docs/architecture/governed-human-review.md](../../architecture/governed-human-review.md), [tests/test_human_review.py](../../../tests/test_human_review.py).

**Historical scope/validation records:** [docs/milestones/milestone-15.md](../milestone-15.md).

**Environment:** Python 3.12.8, Agent Framework 1.23.0/MCP 2.2.0/Pydantic 2.14.2; synthetic identity and in-memory state.

**Last recorded status, not rerun by P1:** 729 source and 729 independent-wheel tests, 84 focused; six report scenarios/24 accepted audit events are reported.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-15.md](../milestone-15.md) | GIT_TRACKED | `a6b714bf999bb6ee…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/review/m15-verified-a.json](../../../outputs/review/m15-verified-a.json) | IGNORED_LOCAL_ONLY | `2e215ab9de99aa27…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Recommendation approval does not create an operational M20 outcome or close a claim. Unsigned process-local audit/session state is volatile; denial telemetry and real human identity remain gaps.

**Blockers/approvals:** Canonical real identity/assignment and durable operational outcome integration require separate approval; never promote M15 actions automatically.

<a id="m16"></a>

## M16 — Governed FastAPI claims application foundation

Registered-bundle intake, bounded ASGI processing/status/advisory and assigned recommendation-review endpoints with idempotency/CAS and safe errors.

**Implementation at the bound commit:** [src/claims_ai/api](../../../src/claims_ai/api), [docs/architecture/governed-fastapi-application.md](../../architecture/governed-fastapi-application.md), [tests/test_api.py](../../../tests/test_api.py).

**Historical scope/validation records:** [docs/milestones/milestone-16.md](../milestone-16.md).

**Environment:** Real FastAPI TestClient/ASGI, synthetic capabilities and separate installed-wheel target. Exact Python patch and host OS are not explicitly restated in the selected M16 record/receipts; they are not inferred from current constraints.

**Last recorded status, not rerun by P1:** 2026-11-10: 814 source/814 independent-wheel tests; 85 API cases; actual OpenAPI 3.1.0 with nine paths and 242 resolved references. Fourteen demo scenarios.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-16.md](../milestone-16.md) | GIT_TRACKED | `69f22a4ab242e3ee…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/api/m16-verified-a.json](../../../outputs/api/m16-verified-a.json) | IGNORED_LOCAL_ONLY | `287c2dc709f2fdae…`; MATCHES_RECORDED_SHA256 |
| [outputs/api/m16-openapi-a.json](../../../outputs/api/m16-openapi-a.json) | IGNORED_LOCAL_ONLY | `090228f5352ea615…`; MATCHES_RECORDED_SHA256 |
| [outputs/packages/m16/package-verification.json](../../../outputs/packages/m16/package-verification.json) | IGNORED_LOCAL_ONLY | `f6e3bfe98356bfc1…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** No TCP/browser/TLS/APIM/live Entra, arbitrary uploads or cloud readiness. Stores/tombstones are process-local; M15 recommendation actions do not commit M20 outcomes.

**Blockers/approvals:** Real host/identity/persistence integrations and any operational authority need separate review.

**Unlocated/local-publication gaps:** G08; see the gap register below.

<a id="m17"></a>

## M17 — Governed claims reviewer operations UI

Server-rendered escaped reviewer UI, host-enrolled sessions/tickets and real API consumption with canonical assignment/CSRF guards.

**Implementation at the bound commit:** [src/claims_ai/reviewer_ui](../../../src/claims_ai/reviewer_ui), [docs/architecture/governed-reviewer-ui.md](../../architecture/governed-reviewer-ui.md), [tests/test_reviewer_ui.py](../../../tests/test_reviewer_ui.py).

**Historical scope/validation records:** [docs/milestones/milestone-17.md](../milestone-17.md).

**Environment:** Real in-process API/UI ASGI, synthetic sessions and HTML/protocol checks, not browser execution. Exact Python patch and host OS are not explicitly restated in the selected M17 record/receipts.

**Last recorded status, not rerun by P1:** 2026-11-10: 878 source/878 wheel tests, 64 UI cases and 12 UI/API scenarios in final report; earlier results are historical.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-17.md](../milestone-17.md) | GIT_TRACKED | `0b0520aae135feea…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/ui/m17-verified-a.json](../../../outputs/ui/m17-verified-a.json) | IGNORED_LOCAL_ONLY | `58926daeb71893b3…`; MATCHES_RECORDED_SHA256 |
| [outputs/ui/m17-reproduction-verification.json](../../../outputs/ui/m17-reproduction-verification.json) | IGNORED_LOCAL_ONLY | `6f33e159d5220922…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Structural accessibility is not certification or tested real-browser/TCP/TLS behaviour. No real human identity, durable session/audit or insurance outcome authority.

**Blockers/approvals:** Browser/accessibility, session delivery, real identity and hosting require separate approved validation.

**Unlocated/local-publication gaps:** G08; see the gap register below.

<a id="m18"></a>

## M18 — Identity and security foundation

Exact offline synthetic signature/claims validation, bounded key discovery/rotation/revocation and independent API/MCP host/case binding.

**Implementation at the bound commit:** [src/claims_ai/identity](../../../src/claims_ai/identity), [docs/architecture/identity-and-security-foundation.md](../../architecture/identity-and-security-foundation.md), [tests/test_identity.py](../../../tests/test_identity.py).

**Historical scope/validation records:** [docs/milestones/milestone-18.md](../milestone-18.md).

**Environment:** Real in-process API/UI/MCP ASGI with ephemeral synthetic issuer/context, no live provider. Exact Python patch and host OS are not explicitly restated in the selected M18 record/receipts.

**Last recorded status, not rerun by P1:** 2026-11-10: 975 source/975 wheel tests and 97 identity cases; 15-scenario report with network operations prohibited.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-18.md](../milestone-18.md) | GIT_TRACKED | `8747795188f82ca3…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/identity/m18-verified-a.json](../../../outputs/identity/m18-verified-a.json) | IGNORED_LOCAL_ONLY | `4a706e2ec18a56b9…`; MATCHES_RECORDED_SHA256 |
| [outputs/identity/m18-reproduction-verification.json](../../../outputs/identity/m18-reproduction-verification.json) | IGNORED_LOCAL_ONLY | `dee87a9c745ab65e…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Synthetic signature validity or bearer possession is not proof of real human/workload identity. No live Entra/JWKS/APIM, browser/TLS, shared revocation or production custody evidence.

**Blockers/approvals:** Real provider/identity provisioning, secret custody and deployed ingress require separate authorisation.

**Unlocated/local-publication gaps:** G08; see the gap register below.

<a id="m19"></a>

## M19 — AI threat model and adversarial security testing

Authored attack evaluation over real offline boundaries plus source-bound MCP response and canonical CLI-output-root remediation.

**Implementation at the bound commit:** [src/claims_ai/adversarial](../../../src/claims_ai/adversarial), [src/claims_ai/mcp_server/client.py](../../../src/claims_ai/mcp_server/client.py), [src/claims_ai/rules/__main__.py](../../../src/claims_ai/rules/__main__.py), [docs/architecture/ai-threat-model-and-adversarial-testing.md](../../architecture/ai-threat-model-and-adversarial-testing.md), [tests/test_m19_remediation.py](../../../tests/test_m19_remediation.py).

**Historical scope/validation records:** [docs/milestones/milestone-19.md](../milestone-19.md), [docs/milestones/milestone-19-remediation.md](../milestone-19-remediation.md).

**Environment:** Real offline SDK/runtime guards, explicitly simulated/injected rows and eight unexecuted production scopes; independent wheel checks share pinned dependencies. Exact Python patch and host OS are not explicitly restated in the selected M19 records/receipts.

**Last recorded status, not rerun by P1:** 2026-11-10: original 1,090 source/wheel tests and 79 PASS/1 FAIL/8 NOT_TESTED; remediation 1,128 source/wheel tests and retained 80 PASS/0 FAIL/8 NOT_TESTED baseline. F-002 has separate nine-check evidence.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-19.md](../milestone-19.md) | GIT_TRACKED | `0b623fa8e460ec4e…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/milestones/milestone-19-remediation.md](../milestone-19-remediation.md) | GIT_TRACKED | `188eaf0308b4599d…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/adversarial/m19-verified-a.json](../../../outputs/adversarial/m19-verified-a.json) | IGNORED_LOCAL_ONLY | `7e3faefd23333482…`; MATCHES_RECORDED_SHA256 |
| [outputs/adversarial/m19-remediation-source-verified-a.json](../../../outputs/adversarial/m19-remediation-source-verified-a.json) | IGNORED_LOCAL_ONLY | `08bd7136c68eda87…`; MATCHES_RECORDED_SHA256 |
| [outputs/adversarial/m19-remediation-paths-source.json](../../../outputs/adversarial/m19-remediation-paths-source.json) | IGNORED_LOCAL_ONLY | `a82025c792092867…`; MATCHES_RECORDED_SHA256 |
| [outputs/adversarial/m19-remediation-summary.json](../../../outputs/adversarial/m19-remediation-summary.json) | IGNORED_LOCAL_ONLY | `be07eea7fcb4665f…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** F-001/F-002 closure is limited to demonstrated local paths; host compromise, real semantic model attacks, live identity/gateway/browser and distributed limits remain untested. 80/0/8 is not a production security score; eight NOT_TESTED identities remain unchanged.

**Blockers/approvals:** Independent production security/risk acceptance and live external testing remain separate; no residual-risk owner approval is inferred.

**Unlocated/local-publication gaps:** G08; see the gap register below.

<a id="m20"></a>

## M20 — Durable human case outcomes and recovery

Bounded local SQLite outcome lifecycle, explicit approved supplied synthetic assessments, current human decisions, atomic audit/receipts/outbox and fixed-context process recovery.

**Implementation at the bound commit:** [src/claims_ai/outcomes](../../../src/claims_ai/outcomes), [docs/architecture/governed-durable-outcomes.md](../../architecture/governed-durable-outcomes.md), [tests/test_outcomes.py](../../../tests/test_outcomes.py).

**Historical scope/validation records:** [docs/milestones/milestone-20.md](../milestone-20.md).

**Environment:** Local SQLite and trusted child processes with supplied synthetic source/approval/current authority, not cloud services. Exact Python patch and host OS are not explicitly restated in the selected M20 record/receipts.

**Last recorded status, not rerun by P1:** 2026-11-10: 1,227 source/1,227 wheel tests, 99 M20 cases; 13 report scenarios and seven actual SIGKILL/restart probes per demonstration.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-20.md](../milestone-20.md) | GIT_TRACKED | `f803f767ce910a02…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/outcomes/m20-source-verified-a.json](../../../outputs/outcomes/m20-source-verified-a.json) | IGNORED_LOCAL_ONLY | `5a7797e44f9f39b0…`; MATCHES_RECORDED_SHA256 |
| [outputs/outcomes/m20-reproduction-verification.json](../../../outputs/outcomes/m20-reproduction-verification.json) | IGNORED_LOCAL_ONLY | `d87be84f0ab3a617…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/packages/m20/source-tests.json](../../../outputs/packages/m20/source-tests.json) | IGNORED_LOCAL_ONLY | `c78b4686c1cac03a…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** M9 findings/M15 approvals are not automatically operational assessments/outcomes; explicit separate host approval is required. Same-runtime process recovery is not power-loss, WORM, cloud/distributed durability or external exactly-once delivery.

**Blockers/approvals:** Fresh same-runtime stores need original approved source/context and current authority; never migrate/rehash historical stores silently. Production policy/identity/persistence, retention and recovery need separate approval.

**Unlocated/local-publication gaps:** G08; see the gap register below.

<a id="m21"></a>

## M21 — Security and identity hardening

Six isolated fixture identity classes, bounded fixture reads, least privilege and authenticated local grant revocation/expiry/disablement composed with canonical API/UI/MCP/outcome services.

**Implementation at the bound commit:** [src/claims_ai/security_hardening](../../../src/claims_ai/security_hardening), [docs/architecture/security-and-identity-hardening.md](../../architecture/security-and-identity-hardening.md), [tests/test_security_hardening.py](../../../tests/test_security_hardening.py).

**Historical scope/validation records:** [docs/milestones/milestone-21.md](../milestone-21.md).

**Environment:** Synthetic fixture profiles, local SQLite and fixed-public-key subprocess restart checks; shared pinned dependency environment recorded. Exact Python patch and host OS are not explicitly restated in the selected M21 record/receipts; no live Entra/provider.

**Last recorded status, not rerun by P1:** Original retained M21 receipts: 1,334 source/wheel tests and 107 focused. M22 Stage A separately cites the accepted corrected baseline of 1,338 source/wheel and 111 focused. Catalogue does not replace original logs or claim correction receipts located.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-21.md](../milestone-21.md) | GIT_TRACKED | `a852f9fca95e13b9…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/security/m21-source-verified-a.json](../../../outputs/security/m21-source-verified-a.json) | IGNORED_LOCAL_ONLY | `a0e74d5ac1470d76…`; MATCHES_RECORDED_SHA256 |
| [outputs/security/m21-reproduction-verification.json](../../../outputs/security/m21-reproduction-verification.json) | IGNORED_LOCAL_ONLY | `a427a755d415a386…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/packages/m21/source-pytest.log](../../../outputs/packages/m21/source-pytest.log) | IGNORED_LOCAL_ONLY | `3a38442cfab4525b…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/packages/m21/installed-wheel-pytest.log](../../../outputs/packages/m21/installed-wheel-pytest.log) | IGNORED_LOCAL_ONLY | `6684e7fa31789256…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/packages/m21/file-manifest.json](../../../outputs/packages/m21/file-manifest.json) | IGNORED_LOCAL_ONLY | `fecdaa66cd46f62b…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [docs/milestones/milestone-22.md](../milestone-22.md) | GIT_TRACKED | `3c6b7d746e2951bc…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** Shared/global revocation, key/latest-anchor custody, cross-store admission races and host compromise remain outside local assurance. file-manifest.json is a changed-path inventory, not per-file hashes; package/report hash evidence is separately retained.

**Blockers/approvals:** Real identity/provider and deployed security need separate authorisation; current independent anchors and same-runtime context remain mandatory.

**Unlocated/local-publication gaps:** G05, G08; see the gap register below.

<a id="m22"></a>

## M22 — Reproducible quality and operations

Frozen 60-case candidate suite/review packet, reference-isolated development evaluator, genuine bounded local OpenTelemetry SDK, executable alerts and audit/fault-recovery controls.

**Implementation at the bound commit:** [src/claims_ai/quality_ops](../../../src/claims_ai/quality_ops), [docs/architecture/offline-quality-and-operations.md](../../architecture/offline-quality-and-operations.md), [docs/operations/m22-runbooks.md](../../operations/m22-runbooks.md), [tests/test_quality_ops_operational.py](../../../tests/test_quality_ops_operational.py).

**Historical scope/validation records:** [docs/milestones/milestone-22-stage-b.md](../milestone-22-stage-b.md), [docs/milestones/milestone-22.md](../milestone-22.md).

**Environment:** Isolated Python 3.12.8/macOS arm64; OpenTelemetry API/SDK 1.45.2 and semantic-conventions 0.66b2; local ASGI, SQLite and child processes, no remote exporter.

**Last recorded status, not rerun by P1:** Python 3.12.8/macOS arm64: final 1,436 source/1,436 independent-wheel tests; 98 focused M22 and 17 operational controls. Earlier 1,434 PASS/2 FAIL wheel topology run remains preserved; no label scores were produced.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-22-stage-b.md](../milestone-22-stage-b.md) | GIT_TRACKED | `655a431d03876040…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/milestones/milestone-22.md](../milestone-22.md) | GIT_TRACKED | `3c6b7d746e2951bc…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [outputs/quality/m22-stage-b/accepted-source-a.json](../../../outputs/quality/m22-stage-b/accepted-source-a.json) | IGNORED_LOCAL_ONLY | `0c401924d24a2e4d…`; MATCHES_RECORDED_SHA256 |
| [outputs/packages/m22-stage-b/acceptance-summary.json](../../../outputs/packages/m22-stage-b/acceptance-summary.json) | IGNORED_LOCAL_ONLY | `52fe5aece15028a4…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/packages/m22-stage-b/wheel-accepted.txt](../../../outputs/packages/m22-stage-b/wheel-accepted.txt) | IGNORED_LOCAL_ONLY | `1cfaa4f3fa4a4584…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/packages/m22-stage-b/wheel-accepted-real-data.txt](../../../outputs/packages/m22-stage-b/wheel-accepted-real-data.txt) | IGNORED_LOCAL_ONLY | `f320e2b866d88dae…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [data/evaluation/m22/v1/candidate-manifest.json](../../../data/evaluation/m22/v1/candidate-manifest.json) | GIT_TRACKED | `42e0eb827c26cbd3…`; MATCHES_RECORDED_SHA256 |
| [docs/quality/m22-independent-review/v1/hash-inventory.json](../../quality/m22-independent-review/v1/hash-inventory.json) | GIT_TRACKED | `3111f57a4ce0f9ed…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** All 60 candidates remain PENDING_REVIEW; 12 independent-quality gates remain NOT_TESTED. Author-visible native text is not an approved blind benchmark. Stage A authoring through an aliased data root is unsupported; local snapshot alerts/telemetry are not production monitoring or durable audit.

**Blockers/approvals:** Genuine independent label/source/exposure adjudication, gate/release decision, approved predictor mapping/isolation and authenticated verifier are required before separately authorised scoring. Cloud export, real data/provider and production operations remain separately gated.

<a id="m23"></a>

## M23 — Governed Azure deployment

Disabled Stage A IaC/workflow/host definitions, B1 signed input admission with unconditional build refusal, pinned Bookworm/Trixie acquisition/static evidence and supported-remediation investigations.

**Implementation at the bound commit:** [infra/azure](../../../infra/azure), [deployment/build_container.py](../../../deployment/build_container.py), [deployment/supply_chain.py](../../../deployment/supply_chain.py), [deployment/containers/entrypoint.py](../../../deployment/containers/entrypoint.py), [.github/workflows/m23-deploy.yml](../../../.github/workflows/m23-deploy.yml), [tests/test_container_supply_chain.py](../../../tests/test_container_supply_chain.py).

**Historical scope/validation records:** [docs/milestones/milestone-23.md](../milestone-23.md), [docs/milestones/milestone-23-stage-a.md](../milestone-23-stage-a.md), [docs/milestones/milestone-23-stage-b1.md](../milestone-23-stage-b1.md), [docs/deployment/m23/stage-b2d-offline-supply-chain-review.md](../../deployment/m23/stage-b2d-offline-supply-chain-review.md), [docs/deployment/m23/stage-b2d-r3-replacement-base-review.md](../../deployment/m23/stage-b2d-r3-replacement-base-review.md), [docs/deployment/m23/stage-b2d-r4-trixie-acquisition.md](../../deployment/m23/stage-b2d-r4-trixie-acquisition.md), [docs/deployment/m23/stage-b2d-r6-supported-remediation-feasibility.md](../../deployment/m23/stage-b2d-r6-supported-remediation-feasibility.md).

**Environment:** Stage A/B1 host checks: Python 3.12.8/macOS arm64. Linux AMD64 image contents were acquired/read as data; no Linux container build/run. R6 captured public metadata previously; P1 makes no requests.

**Last recorded status, not rerun by P1:** Stage A: 12 Bicep compilations, 1,506 full-source tests and 299 focused wheel tests; B1: 434 focused, not a new full suite. R4 reconciles four Trixie layers/87 installed packages/2,653 publisher hashes. R6 stops with no complete supported authenticated remediation route.

| Existing evidence / record | Availability | Hash verification |
| --- | --- | --- |
| [docs/milestones/milestone-23.md](../milestone-23.md) | GIT_TRACKED | `ed9d0231dfecc10c…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/milestones/milestone-23-stage-a.md](../milestone-23-stage-a.md) | GIT_TRACKED | `603bc058d82c2a84…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/milestones/milestone-23-stage-b1.md](../milestone-23-stage-b1.md) | GIT_TRACKED | `842bb73ae9e44978…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/deployment/m23/stage-b2d-offline-supply-chain-review.md](../../deployment/m23/stage-b2d-offline-supply-chain-review.md) | GIT_TRACKED | `0f1622248b158421…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/deployment/m23/stage-b2d-r3-replacement-base-review.md](../../deployment/m23/stage-b2d-r3-replacement-base-review.md) | GIT_TRACKED | `acb0dd259e0c027b…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/deployment/m23/stage-b2d-r4-trixie-acquisition.md](../../deployment/m23/stage-b2d-r4-trixie-acquisition.md) | GIT_TRACKED | `2eac5083e41eb7f1…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/deployment/m23/stage-b2d-r6-supported-remediation-feasibility.md](../../deployment/m23/stage-b2d-r6-supported-remediation-feasibility.md) | GIT_TRACKED | `092fb0500ed11cb7…`; CURRENT_BYTES_MATCH_BOUND_GIT_BLOB |
| [docs/deployment/m23/b2b-acquisition-inventory.json](../../deployment/m23/b2b-acquisition-inventory.json) | GIT_TRACKED | `818ec99db7e67488…`; MATCHES_RECORDED_SHA256 |
| [docs/deployment/m23/r3-replacement-base-metadata.json](../../deployment/m23/r3-replacement-base-metadata.json) | GIT_TRACKED | `c134c3eab5626d38…`; MATCHES_RECORDED_SHA256 |
| [docs/deployment/m23/r4-trixie-artifact-inventory.json](../../deployment/m23/r4-trixie-artifact-inventory.json) | GIT_TRACKED | `e9cadab3476480d7…`; MATCHES_RECORDED_SHA256 |
| [outputs/deployment/m23-b2d/security-decision.json](../../../outputs/deployment/m23-b2d/security-decision.json) | IGNORED_LOCAL_ONLY | `ea3543b8e68a99c7…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/deployment/m23-b2d-r4/validation.json](../../../outputs/deployment/m23-b2d-r4/validation.json) | IGNORED_LOCAL_ONLY | `5df5222ca7771f01…`; OBSERVED_SHA256_NO_RECORDED_PIN_CHECKED |
| [outputs/deployment/m23-b2d-r6/assessment.json](../../../outputs/deployment/m23-b2d-r6/assessment.json) | IGNORED_LOCAL_ONLY | `c2914abf291ca679…`; MATCHES_RECORDED_SHA256 |

**Independent outcomes:** NOT_ESTABLISHED_BY_SELECTED_EVIDENCE. No new acceptance decision is issued.

**Limitations:** DEFERRED — SECURITY GATE NO-GO. Frozen Bookworm baseline 355 occurrences/158 CVEs (two Critical, 29 distinct High) is not a fresh Trixie scan. R6 lists one unapplied zlib update and eight High CVEs without established supported Trixie fixes; applicability and CVE attribution gaps persist. Retained DB 1,764,941,824 bytes exceeds unchanged 1 GiB cap; authenticity, CPython/bundled OpenSSL/Cargo/native coverage, licences/reviewer trust, physical builder isolation and Linux runtime remain incomplete. AZU-0058, real Entra/cloud adapters/private integration/cost/restore approval remain unresolved; no Azure deployment acceptance.

**Blockers/approvals:** All five reopening criteria in milestone-23.md, zero unresolved Critical/High and complete authenticated fresh database within 1 GiB remain mandatory. Separate explicit acquisition, builder implementation/build, runtime and Azure/spending approvals; B1 refusal is not removed by documentation.

**Unlocated/local-publication gaps:** G06, G07; see the gap register below.

## Gap register

These entries mean evidence was not located in the reviewed repository/local output inventory, or is not portable through Git. They do not assert that no private copy exists elsewhere. P1 does not fill them with reconstructed logs, reruns or assumed approvals.

| Gap | Milestone | Classification | Unresolved evidence |
| --- | --- | --- | --- |
| G01 | M1 | MISSING_NOT_LOCATED_IN_REVIEWED_INVENTORY | No separately retained raw M1 document-validation receipt is identified; the tracked milestone narrative is the available record. |
| G02 | M2 | MISSING_NOT_LOCATED_IN_REVIEWED_INVENTORY | The milestone does not identify a durable original 115-test log or a source-bound M2 archive path/hash; current dist files are not assumed to be M2 artifacts. |
| G03 | M3 | MISSING_NOT_LOCATED_IN_REVIEWED_INVENTORY | Separate raw M3 document-check/per-file preservation receipts are not identified by the record. |
| G04 | M4 | MISSING_NOT_LOCATED_IN_REVIEWED_INVENTORY | Temporary render/contact-sheet QA is described outside repository deliverables; no retained path is provided for independent reinspection. |
| G05 | M21 | MISSING_NOT_LOCATED_IN_REVIEWED_INVENTORY | Known outputs/packages/m21 logs retain 1,334 results; separately linked raw 1,338/111 acceptance-correction receipts are not located. The later baseline claim is retained as documentary evidence only. |
| G06 | M23 | CONVERSATION_ONLY_NO_REPOSITORY_ARTIFACT | R1/R2/R5 have conversation-only assessments; no separate repository reports are claimed. |
| G07 | M23 | IGNORED_LOCAL_ONLY_PUBLICATION_GAP | Full raw scanner/validation/acquisition evidence is ignored/local-only; public tracked summaries/pins are not a portable complete evidence archive. |
| G08 | M16–M21 | MISSING_ENVIRONMENT_DETAIL_IN_SELECTED_EVIDENCE | Exact Python patch and host OS are not explicitly restated in the selected M16–M21 records/receipts. Execution surfaces and isolation are recorded; nearby milestone environments and current dependency declarations are not substituted as observations. |

## Recommendation for P2

**GO for separately authorised offline architecture reconciliation and demonstration design.** Use this catalogue to freeze supported entry points, selected synthetic scenarios, expected controls, evidence exclusions and measurable acceptance before any run. Keep M15/API/UI recommendation approval separate from M20's independently host-approved synthetic outcome path; do not invent the missing deployed integration.

P2 must carry the missing-receipt and local-only limitations into its plan, distinguish historical results from current-runtime verification, preserve all failure/holdout/deployment statuses, and specify fresh disposable same-runtime contexts for any later approved recovery exercise. Independent release/readiness claims remain blocked by the recorded gaps and M22/M23 acceptance requirements.

**No P2 execution, application changes, acquisitions, builds, containers, Azure operations, live services or independent scoring are authorised by P1.** Any subsequent runtime demonstration needs its own explicit scope/approval; M23 deployment reopening remains a separate security process.
