# Microsoft Agent Framework review foundation

Status: **IMPLEMENTED and locally TESTED using actual agent-framework-core 1.23.0**. The model client is explicitly **SIMULATED** through a supported SDK extension. No live model, cloud service, operational policy approval, claims decision or settlement is implemented. [Dependencies](../dependencies/agent-framework.md) record the exact tested environment.

## Purpose and existing authority boundary

`NorthstarAssessmentReview` is one bounded assessment-review assistant within the planned policy-explanation responsibility. It organizes validated findings and their provenance for a human. It is not a third coverage/supervisor agent. Evidence reconciliation and free-form model reasoning remain planned and require comparison with a simpler code baseline before claiming benefit. [ADR-0001](decisions/0001-decision-authority.md), domain contracts, human lifecycle guards and M9 rules retain their authority.

The current output deliberately accounts for the six supplied deterministic findings using **exact** explanations, statuses, evidence IDs and citations. Rephrased or additional policy conclusions are rejected. This is a framework/provenance foundation, not proof of natural-language reasoning, semantic grounding or model quality. All demo responses are scripted; real execution is confined to the framework orchestration, tool dispatch, structured parsing and host guards.

## Deterministic host preflight

[AssessmentInput](../../src/claims_ai/agents/contracts.py) composes unchanged M9 request/specification/evaluation types and M7 retrieval request/response types. [prepare_packet](../../src/claims_ai/agents/prepare.py) runs before exposing data to the agent:

1. Permit only the typed `explain_findings` task. Requests for coverage decisions or unsupported policy conclusions abstain.
2. Recompute M9 findings in host code and compare the complete evaluation to reject stale/forged input. Policy binding and evidence prerequisites must pass; M6 validation/source replay remains inside that deterministic path.
3. Require successful retrieval and compare the response against unchanged, case-bound M7 retrieval. Require exact requested version and all citations needed by the six findings. Empty/outage, wrong-version, manipulated or insufficient citations abstain without a wider query or invented fallback.
4. Create an immutable packet with claim/case/input fingerprints, provisional policy status, minimum reviewer, findings, validated evidence and cited chunks. Limit the serialized packet before model execution.

Thus rules, policy resolution, authorization assertions and lifecycle transitions stay outside the agent and are not tools. Preflight failures report zero model/tool executions and an explicit supervisor abstention. Missing/unknown cause or adverse findings with otherwise validated evidence can be presented as uncertainties with the existing supervisor requirement preserved.

## Actual SDK path

The [offline client](../../src/claims_ai/agents/offline.py) inherits real `FunctionInvocationLayer` and `BaseChatClient`, implements `_inner_get_response` and calls `_validate_options`. It emits SDK `ChatResponse`, `Message` and `Content.from_function_call` objects. It has no endpoint, provider SDK, credential lookup or network transport.

[build_agent/assess](../../src/claims_ai/agents/assessment.py) construct the real `Agent` with fixed `instructions` and one real `FunctionTool`, then invoke `Agent.run` with a Pydantic `response_format`, `max_tokens`, no parallel tools and `store=false`. The SDK executes the function, feeds its result to the client and exposes the parsed `AgentDraft` through `AgentResponse.value`. Tests exercise this execution rather than replacing the framework classes with mocks.

The sole allow-listed tool is `read_review_packet`. It is a read-only closure over one verified packet with an empty Pydantic argument model (`extra=forbid`); the model cannot supply another claim ID, policy, URL, path or query. No state/rule/decision/payment/file/network tool is registered. Fresh unmodified offline clients are required: changed invocation configuration, hidden additional tools, function middleware, relaxed budgets and reused clients are rejected. Framework unknown-call termination and tool invocation caps are also enabled.

## Trust and output controls

Fixed instructions are passed through the SDK's instruction option; the untrusted user note stays in a `user` message. Evidence and retrieved text appear only as JSON data in the `tool` result, tagged untrusted and provisional. No document text is interpolated into privileged instructions or tool definitions. Tests inject instructions into actual in-memory source documents/clauses, replay validation and execute the real SDK. This demonstrates channel separation and deterministic guard behavior with a test double, **not resistance of an untested live model**.

After execution, host code requires exactly the permitted tool-call trace and validates output size before accessing parsed structured data. It binds claim/packet hash, reviewer/disposition and all six summaries to the supplied findings. Bad references, missing/changed statements, unsupported approval text and reviewer downgrades are rejected without returning a partial draft. A model can abstain; it cannot decide the claim. Every result fixes human review required, final outcome null and settlement authorization false. Adverse, high-risk, ambiguous and failure cases retain supervisor handling; the agent cannot close a case.

These are consistency checks on caller-supplied synthetic cases and assertions, not authentication. Case access, scan/reviewer identity and policy authority must come from a future trusted service. The original operational service protocols remain unchanged; no persistence or publication adapter is claimed.

## Bounded execution and failures

| Control | Implemented bound |
| --- | --- |
| Client calls | Two, checked before each offline response is produced |
| Tool execution | One case-bound read; independent host counter plus SDK invocation caps |
| SDK loop | Two iterations, one function budget, sequential invocation, unknown calls terminate, detailed exception results disabled |
| Deadline | Three seconds by default, configurable up to 30; includes measured preflight time and an async timeout around SDK execution |
| Packet/output bytes | Defaults 65,536 / 16,384; validated configured ranges |
| Token option | Default `max_tokens=2048`, maximum 4096; forwarded to the client, not measured/billed offline token usage |

SDK call/duration quotas are documented as best-effort after batches; the host counters, exact tool map and output checks supply the stricter local boundaries. Deadlines are cooperative and cannot preempt arbitrary blocking Python; live/blocking clients need separate isolation and evaluation. This foundation rejects live client types and does not expose streaming or session reuse.

Typed result reasons distinguish input/evidence/retrieval/citation holds, unsupported requests, quota/deadline failures, framework/tool errors, invalid output and model abstention. Failures omit raw exceptions/payloads, require a supervisor and return no draft or final outcome. No retry or fallback broadens scope.

## Reproduction and evidence status

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.agents --spec-root data/rules/motor/v1 --output outputs/agents/offline.json
make agents-check
```

Use a new output path; data directories and overwrites are refused. The six-case demo reuses M9 synthetic inputs without changing them: ordinary review, adverse escalation, missing evidence, injected note, unsupported task and forbidden tool. Reports separate actual framework execution from simulated model behavior and record zero live calls/outcomes. [M10 evidence](../milestones/milestone-10.md) records actual counts, fingerprints and package checks.

M4–M9 data, code and original results are preserved. The new isolated environment changes runtime metadata; comparisons account explicitly for the Pydantic version and the M5 run ID derived from it. M8's four lexical failures remain unresolved. Free-form explanation, independently adjudicated model evaluation, live Foundry integration, real injection testing, authorization, distributed telemetry and durable human-review workflows remain planned. The [M11 governed tool profile](governed-agent-tools.md) now extends this same agent responsibility with host grants and three service-backed reads; this original M10 profile and its limits remain unchanged.
