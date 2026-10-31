# Microsoft Agent Framework dependency verification

Status: **INSTALLED AND LOCALLY TESTED** for M10 on Python 3.12.8. The earlier acquisition blocker was resolved by the user-provided isolated project environment. The actual SDK is executed; model behavior remains **SIMULATED** through its custom-client extension. No provider/cloud extra is used.

## Authoritative sources and exact APIs

Selected SDK: [agent-framework-core 1.23.0](https://pypi.org/project/agent-framework-core/1.23.0/), released 2026-10-22. The [versioned Microsoft package manifest](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/pyproject.toml) documents the minimal core dependency ranges. Its Python >=3.10 declaration includes this project's supported Python 3.12. The umbrella package and `[all]` extras are unnecessary.

Authoritative documentation was checked during discovery; the installed distribution's actual signatures and source were inspected and exercised after resuming:

- [Agent](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/agent_framework/_agents.py): real construction with `client`, fixed `instructions`, `id`, `name` and an explicit `tools` list; `Agent.run` with runtime options.
- [BaseChatClient](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/agent_framework/_clients.py): supported `_inner_get_response` override and `_validate_options`; combined with real `FunctionInvocationLayer` for SDK function dispatch.
- [Tools](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/agent_framework/_tools.py): `FunctionTool` with typed `input_model`, `max_invocations` and `max_invocation_exceptions`; `FunctionInvocationConfiguration` for iterations/call count/duration, sequential calls, unknown-call termination and sanitized model-facing errors. SDK batch quotas are best-effort, so host guards enforce the stricter local cap.
- [Messages/content](https://github.com/microsoft/agent-framework/blob/python-1.23.0/python/packages/core/agent_framework/_types.py): `Message`, `Content.from_function_call`, `ChatResponse` and actual assistant/tool conversation flow.
- [Structured outputs](https://learn.microsoft.com/en-us/agent-framework/agents/structured-outputs): runtime `response_format=AgentDraft`, parsed through real `AgentResponse.value`, followed by host provenance validation. `max_tokens`, `allow_multiple_tool_calls=false` and `store=false` are exercised options.

## Exact tested runtime closure

The SDK is declared in the project’s optional `agents` extra. [m10-constraints.txt](../../requirements/m10-constraints.txt) pins the tested Python 3.12 runtime closure; no SDK implementation is vendored or replaced. Versions were read from installed distribution metadata and `pip check` passed.

| Distribution | Tested version |
| --- | --- |
| agent-framework-core | 1.23.0 |
| msgspec | 0.22.0 |
| pydantic / pydantic-core | 2.14.2 / 2.50.2 |
| pydantic-settings | 2.16.2 |
| annotated-types | 0.8.0 |
| typing-extensions / typing-inspection | 4.16.0 / 0.4.4 |
| python-dotenv | 1.2.4 |
| opentelemetry-api | 1.45.2 |
| PyYAML | 6.0.3 |
| regex | 2026.9.29 |

Tooling exercised: pytest 8.4.2, Ruff 0.16.10, mypy 1.20.2, setuptools 82.0.1. `.venv/pyvenv.cfg` confirms `include-system-site-packages=false`. The user's `.venv-backup-m10` directory is untouched and excluded by the environment-backup ignore pattern.

## Reproduction and environment change

```sh
.venv/bin/python -m pip install -c requirements/m10-constraints.txt '.[dev,agents]'
PYTHONPATH=src .venv/bin/python -m claims_ai.agents --output outputs/agents/offline.json
```

Package acquisition is not needed for the already-provisioned environment. Local editable metadata was refreshed successfully without downloads/dependency changes. In this execution context plain module discovery did not activate the editable source path; source commands therefore explicitly use `PYTHONPATH=src`. Independent installed-wheel checks use an isolated temporary target with its package path first, so they cannot accidentally test source imports.

The isolated environment uses Pydantic 2.14.2 rather than M2–M9's recorded 2.11.7. All prior tests and exact M4 reproduction pass without dataset/schema changes. New M5–M9 regression files preserve semantic results; differences are limited to the Pydantic metadata and M5's verified derived run ID. Original artifacts are retained. This is not a claim that historical reports are byte-identical across different environments.

## Earlier blocker and current limits

Initial discovery could not resolve/download PyPI, and the SDK plus `msgspec` were missing. That blocked state is superseded by the installed-package inspection and [M10 evidence](../milestones/milestone-10.md); no previous mock/protocol-only implementation is being relabeled as integration.

Current validation establishes offline framework mechanics and deterministic safety boundaries. It does not establish live provider compatibility, semantic reasoning quality, calibrated token/cost usage, model injection resistance, durable sessions or Azure observability. Provider packages, MCP/APIM, credentials and cloud resources remain outside M10.

## M11 extension evidence

M11 retains every dependency pin and adds no package. Installed SDK signatures and the pinned Microsoft tool source were inspected for `FunctionTool.invoke(arguments=..., skip_parsing=True)`, typed `input_model`, invocation caps and real automatic dispatch. [M11 tests](../../tests/test_agent_tools.py) exercise three actual functions through the supported client extension and parsed Pydantic output; [M11 evidence](../milestones/milestone-11.md) records final checks. This does not add MCP/APIM or any live provider package.
