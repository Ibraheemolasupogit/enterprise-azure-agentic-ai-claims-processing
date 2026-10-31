# Governed internal assessment tools

Status: **IMPLEMENTED and locally TESTED**, using actual Microsoft Agent Framework core 1.23.0. Chat responses, identity grants and injected outages in demonstrations are **SIMULATED**. No model, Entra, MCP/APIM or cloud integration is supplied. [M11 evidence](../milestones/milestone-11.md) records validation.

## Responsibility and tool selection

The existing `NorthstarAssessmentReview` agent has a new governed tool profile in [claims_ai.agent_tools](../../src/claims_ai/agent_tools/execution.py). Its identity, assessment-review responsibility and M10 structured advisory schema are retained. There is no additional agent. M10's one-packet profile and original demonstration remain available as historical framework evidence; the governed entry point requires an explicit host grant.

Three reads separate the existing service boundaries and permit independent scope/provenance/error testing. No search query, arbitrary field selector, URL, path, rule parameter or executable instruction is accepted from the agent.

| Tool | Typed arguments | Minimal successful data / implemented backing |
| --- | --- | --- |
| `read_claim_evidence` | Exact claim ID | Normalized field values, evidence IDs and M9 processing provenance (document/hash/page/source lines/record/processing key); M6 verification is replayed through existing M9/M10 preflight |
| `read_policy_clauses` | Exact claim/policy/version/incident date/index hash | M7 verified clause chunks, citations and source-line/effective-date metadata; host-selected lexical request is fixed, with no broader fallback |
| `read_rule_findings` | Same exact policy scope plus rule execution key | Existing six M9 findings, rule/specification versions, citations, evidence references, non-binding calculations and minimum reviewer; parameters never come from model arguments |

The rule tool reads/revalidates deterministic findings in host code. It grants no model interpretation, rule-authoring, policy-resolution or execution-parameter authority. These tools cannot transition cases, authorize review, approve/deny, pay or settle claims.

## Host authorization and service boundary

[ToolGrant](../../src/claims_ai/agent_tools/contracts.py) is an immutable **trusted-host assertion**, containing principal/correlation UUIDs, one claim ID, exact case fingerprint and explicit read permissions. It is not a bearer token or evidence of authentication. A future authenticated service must construct it after assignment/role checks; never deserialize it from a model message or public request. Grants are local to one bounded execution and are not cached or persisted. Token expiry, revocation and distributed enforcement remain planned.

The governed assessment checks case/fingerprint and all three required permissions **before preflight/service reads**. [GovernedTools](../../src/claims_ai/agent_tools/tools.py) captures the validated input and verified packet. Every tool independently rechecks permission and exact arguments before calling a [ReadServices](../../src/claims_ai/agent_tools/tools.py) method. Direct host calls can use a subset of read permissions; any missing permission fails closed. Cross-case errors expose neither case existence nor foreign data. The agent cannot replace the principal, correlation ID, grants or trusted case; unexpected arguments are forbidden.

Preflight reuses unchanged M10 validation: M6 source replay and M9 findings/binding/evidence prerequisites, then exact M7 response/citation checks. The actual local service methods replay their existing validations again when read. Returned data must equal the canonical snapshot payload before release; altered hashes, citations, values, findings or scope are rejected. A service protocol alone is not being claimed as an implementation: `LocalReadServices` calls the implemented local paths. No store/client is added.

## SDK dispatch, limits and safe failures

Actual `FunctionTool(func=..., input_model=..., max_invocations=1, max_invocation_exceptions=1)` instances are registered on real `Agent`. Tests exercise both `FunctionTool.invoke(arguments=..., skip_parsing=True)` and `Agent.run` with real SDK `FunctionInvocationLayer` dispatch and Pydantic `AgentResponse.value` parsing. Signatures were inspected in the installed SDK and checked against [Microsoft's pinned tool source](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/agent_framework/_tools.py). The [M10 dependency pins](../../requirements/m10-constraints.txt) are unchanged; no dependency was added.

The default bounded path allows four simulated chat responses, three total tool attempts and one read per named tool. SDK invocation configuration is sequential with four iterations, three function calls and unknown-tool termination. Independent host attempt counters reserve a slot before awaiting, check duplicates and enforce a failure latch. SDK quotas are best-effort after batches; the host guards supply the stricter read limits. Repeated, hidden, unknown or parallel-flood calls cannot gain extra reads. Fresh client configuration is checked; added tools/middleware, relaxed limits and reuse are rejected.

The execution deadline is three seconds, including measured preflight time; each service read has a one-second deadline. Tool replies default to 65,536 bytes and final outputs to 16,384. Deadlines are cooperative; blocking Python requires isolation before external integrations. No latency/token-cost measurement or performance claim follows from these bounds.

Every service-bound reply is typed, correlated and tagged `untrusted_data` / `provisional_unapproved`. Success pins the packet fingerprint; errors contain only tool name, host correlation, status and a stable code, with no data, snapshot fingerprint or raw exception. Schema failures rejected before the SDK invokes the function use sanitized SDK errors; the outer assessment still returns a correlated supervisor abstention. Receipts contain metadata only, not values or document text. A tool failure stops later reads; completed packets are closed against reuse. These receipts are caller-held evidence, not durable audit or distributed tracing.

## Untrusted content and final authority

Policy/document text appears as JSON tool-result data; untrusted user notes stay in a user message. Fixed SDK instructions never interpolate it. Tests reauthor only in-memory synthetic source documents/clauses, replay their provenance and run the real framework. This proves channel/host-boundary behavior with scripted responses, not live-model injection resistance. SDK/debug logs must not be enabled with sensitive payload capture; the demo has no exporter or raw-payload logging configuration.

The host requires the exact three successful call receipts and validates the final draft with M10's unchanged `validate_draft`: exact claim/packet hash, six deterministic findings, explanations, evidence/citations and reviewer/disposition. Unsupported conclusions or supervisor downgrades return no draft. Missing/quarantined/conflicting/unverified evidence fails before execution. Every result retains mandatory human review, null final outcome and no settlement authority. Ambiguous, high-risk and adverse findings require a supervisor.

## Reproduction and remaining work

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.agent_tools --output outputs/agent-tools/offline-v1.json
make agent-tools-check
```

Use a new output filename. The ten-case report records actual SDK reads, correlated metadata and safe failures while labeling model/identity/fault assertions simulated. The CLI protects the selected reference pack, its ancestor `data/` directory and the current `data/` directory, including execution from another working directory; existing outputs cannot be overwritten.

M4–M9 reference data, M8 failures and the M10 runtime profile are unchanged. Authenticated access, signed/expiring grants, durable audit, live model quality, gateway controls, operational policy approval and integration resilience remain planned. Roadmap sequencing follows the newly authorized M11 scope; no M12 implementation is included.
