# M19 synthetic adversarial catalog

This is a new authored development security catalog, separate from the immutable M4–M9 data/evaluations. It contains **88** bounded synthetic scenarios: runtime controls, scripted-model guard cases, declared host-injected faults and eight unconfigured production scopes. Expectations are authored, not independently adjudicated or attack-success probabilities.

`manifest.json` pins `scenarios.json` by SHA-256. The loader rejects duplicate JSON keys/case IDs/criteria, oversized inputs and unknown target types. Attack parameters choose fixed local code paths; no payload is executed as Python, a command or a URL. Descriptions and strict-type criteria are distinct from observed runtime facts. No credential, key, session cookie or real person/claim data belongs in this catalog.

The catalog intentionally expects the MCP consumer to reject consistently altered policy content in ADV-MCP-09. The existing consumer currently accepts it; the evaluator reports **FAIL** rather than rewriting the expectation. A matching regression label in the test suite documents that finding; it does not feed the evaluator's classification or make security green.

The direct/indirect content cases demonstrate data containment/typed host authority under existing simulated clients. They do not demonstrate live-model semantic resistance. The production rows remain NOT_TESTED with explicit reasons. The MCP response mutation is a simulated compromised-return path after a genuine SDK read, not evidence of a remote network exploit or an insurance outcome bypass.

Read [the threat model](../../../../docs/architecture/ai-threat-model-and-adversarial-testing.md) and [M19 evidence](../../../../docs/milestones/milestone-19.md). Run from the repository with all existing `mcp`, `ui` and `identity` extras:

```sh
PYTHONPATH=src .venv/bin/python -m claims_ai.adversarial --output outputs/adversarial/new-report.json
```

Use a new output filename outside reference data. Exit 0 means completed evaluation with no failed criteria; **exit 2** means completed evidence with findings; exit 3 means invalid setup, incomplete harness/network-guard evidence or an observed operational outcome. NOT_TESTED is never called a blocked attack. No external target, cloud, live identity/model or browser/network load test is configured.
