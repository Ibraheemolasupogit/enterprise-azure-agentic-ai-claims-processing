# Milestone 12 — Deterministic claims workflow orchestration

Status: **COMPLETE within the bounded offline workflow scope**. The user's M12 request replaces the earlier planned ingestion-service milestone with deterministic offline orchestration. No API, deployment or subsequent milestone implementation is included.

## Files and decisions

- New [workflow contracts](../../src/claims_ai/workflow/contracts.py), [service composition](../../src/claims_ai/workflow/stages.py), [runner/replay validation](../../src/claims_ai/workflow/engine.py), [CLI/synthetic authoring](../../src/claims_ai/workflow/__main__.py) and package initializer.
- New [focused tests](../../tests/test_workflow.py), [architecture guide](../architecture/deterministic-claims-workflow.md) and this record. Updated README, architecture status, traceability, quality guidance, roadmap and Makefile.
- No dependency or existing runtime/service/domain changes. M4–M9 reference artifacts and M8 results are preserved; M10/M11 agent profiles remain unchanged.

Six deterministic stages compose M2 lifecycle guards, M6 evidence mapping/admission/history, M7 policy ingestion/exact-version lexical retrieval, M9 provisional findings, M11 governed assessment and advisory human routing. No business-rule implementation is duplicated and no additional agent exists. The runtime never repins stale reviewer facts.

The case proceeds through RECEIVED → VALIDATING → EXTRACTING → ASSESSING using M2 transitions and M6 admission revisions. Successful provisional processing creates an independent review task while leaving the case ASSESSING; it cannot fabricate the operational `Assessment` required by M2's AWAITING_REVIEW. This preserves existing decision-authority rules. Missing evidence and quarantine use existing M2 safe transitions; other holds create explicit workflow abstention/failure states.

## Framework, safety and recovery

The agent stage calls the implemented M11 `assess`, real Agent Framework 1.23.0 `Agent.run`, three genuine `FunctionTool` dispatches and Pydantic output parsing. Its supported offline client returns explicitly **SIMULATED** chat. Host-side grants are checked before replay/services, delegated only across verified same-case changes and rechecked by tools. Evidence/source replay, policy/version/date/index checks and exact deterministic draft support remain mandatory.

Every record is frozen, correlated, ordered and content-linked. An execution key binds request content (including excluded raw bytes), principal/grants, code/runtime/configuration. Same-runner duplicates reuse validated checkpoints without repeating SDK calls; caller-supplied serialized checkpoints can resume a new runner. Deterministic stages replay, while cached agent results undergo the existing provenance validator. Hashes are not signatures or execution attestations.

At most two attempts per stage, cooperative stage/run/tool timeouts, bounded input/checkpoint/journal sizes and typed safe failure states apply. Only dependency errors/timeouts/cancellation retry; exhausted budgets remain terminal across resumes. Cancellation accounts for an interrupted attempt before propagation. No raw exception text is retained. Unsupported/adverse/ambiguous/high-risk paths cannot remove human/supervisor approval or create a final outcome.

## Verification

Tested isolated environment: Python **3.12.8** (`include-system-site-packages=false`), Agent Framework **1.23.0**, msgspec **0.22.0**, Pydantic **2.14.2**, pytest **8.4.2**, Ruff **0.16.10**, mypy **1.20.2**, setuptools **82.0.1**. No dependency was added/upgraded; only the project wheel was installed into a temporary verification target without downloading dependencies.

| Check | Actual result |
| --- | --- |
| Complete source suite | **531 passed**: all 478 baseline tests plus 53 new parametrized workflow tests; final local verification took 74.49 seconds, not a business-performance benchmark |
| Ruff format/lint | Passed on all 71 Python files |
| Strict mypy | No issues in 71 source/test files |
| Dependency/corpus integrity | `pip check`: no broken requirements; 12 scenarios validated, existing exact M4 reproduction test passes |
| Packaging | Offline wheel and source distribution builds passed; five workflow modules match packaged source, SDK extra metadata retained, source archive includes tests/docs/constraints and all 161 tracked data files |
| Installed wheel | Isolated temporary package target verified with `python -I`; pytest source path overridden to that target; **531 passed** in 74.93 seconds |
| Independent wheel CLI | Executed from a temporary working directory with explicit specification root and wheel-only package import; byte-identical to source reports |
| Reproduction | Two source reports and independent wheel report match exactly; partial policy-stage JSON round-trip resumes to the same checkpoint as uninterrupted processing |
| Documentation | 35 Markdown files, 541 local links and 167 named test references checked; anchors, tables, fences, whitespace and `git diff --check` pass |
| Preservation | All 161 tracked data files match Git blobs; no existing runtime/test file modified; M10/M11 reports reproduced byte for byte and original M8 report preserved |

Historical CLI subtests continue to select source as before; the installed-wheel suite runs from the repository root for existing relative fixtures. The new workflow CLI subtest selects the active package location and runs from another directory, so it also exercises the wheel during wheel testing. Independent isolated CLI execution separately excludes source imports.

New tests cover exact stage ordering, real governed SDK execution without network access, the complete M2 transition/M6 admission revision chain, concurrent/idempotent execution, all five resumable stage boundaries, transient recovery with retained attempt history, terminal exhausted budgets, authorization before replay, missing/conflicting/quarantined/unverified evidence, exact version/date boundaries, adverse/ambiguous/high-risk routing, injected source content, forbidden/cross-case tool calls, unsupported conclusions, governed tool outages, cooperative cancellation/timeouts, capacity bounds, stale reviewer facts and forged stage/checkpoint data even after recomputing unsigned hashes.

Two fresh source reports, `outputs/workflow/m12-verified-a.json` and `m12-verified-b.json`, plus the independent wheel CLI, produce the same `offline-workflow-run-v1` JSON. SHA-256: `ec0c6c47f439dfd08a7954c220c688446a6ab457340dacd83727f25d53a0adb0`. The report is approximately 21.7 MB because it includes full immutable snapshots/records for seven cases, plus the partial resume checkpoint. These ignored local artifacts can be regenerated; they are not a durable storage implementation.

| Synthetic report case | Workflow terminal state | Case state / required reviewer | Recorded stage attempts |
| --- | --- | --- | --- |
| Advisory | Awaiting human review | ASSESSING / reviewer | 6 |
| Missing evidence | Awaiting evidence | AWAITING_EVIDENCE / supervisor | 2 |
| Retrieval failure | Failed after two policy attempts | ASSESSING / supervisor | 4 |
| Injected document | Awaiting supervisor review | ASSESSING / supervisor | 6 |
| Adverse exclusion candidate | Awaiting supervisor review | ASSESSING / supervisor | 6 |
| High-risk amount | Awaiting supervisor review | ASSESSING / supervisor | 6 |
| Serialized checkpoint resume | Awaiting human review | ASSESSING / reviewer | 6 |

The report contains 36 stage records, including five successful agent stages with 20 scripted responses and 15 actual governed tool reads. Cached duplicate checks add no agent calls. The CLI separately executes one uninterrupted comparison for the resume case: total execution per CLI invocation is six real SDK runs, 24 simulated responses and 18 read-only tool bodies. All cases retain null final outcomes, no settlements and no operational assessments. Exhausted retries retain processing data and add an explicit supervisor task.

The original M10 and M11 demonstrations were rerun into separate preservation files and match their original bytes (SHA-256 respectively `74aad58a9a47340f3f16a926fcd60ce8d5644511a407db19364f6aaa367a53ca` and `388a0c3a03d4c5a730a7ba4432acc832ee470e4e35b1fc4b7a975e6aa9f47f57`). Original M8 report SHA-256 remains `e1b45e98dc8d9e8d6209e3443a3049b5ce5cfde6cdfcb11ab4c62e3f9f7f9340`; failures Q-007/Q-012/Q-015/Q-029 are unresolved.

## Limitations and acceptance

Offline trusted synthetic assertions are not authentication, scanning or approved reviewer actions. Local checkpoints are caller-held content, not durable cloud persistence, signed audit, distributed locks or exactly-once processing. Pure replay adds local CPU cost; deadlines are cooperative, start after per-runner lock admission and cannot preempt blocking Python. There is no separate queue-wait deadline. Abrupt process failure can lose an uncommitted attempt. SDK invocation counts for interrupted calls may be unavailable and are not fabricated.

Model quality, live injection resistance, approved policy/rule publication, end-to-end human review, OpenTelemetry, upload ingestion, cloud identity, MCP/APIM and deployment remain planned. Acceptance is met for explicit stage/prerequisite enforcement, reused real governed SDK execution, immutable correlated records, bounded retry/cancellation, safe human routing and reproducible caller-held recovery. This does not approve policy wording, an insurance outcome, live model quality or operational deployment.

Four M8 lexical failures remain unresolved. No live model/Azure calls, spending, commits or pushes. **Stop after M12.**
