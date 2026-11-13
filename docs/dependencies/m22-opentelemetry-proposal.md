# M22 OpenTelemetry dependency proposal — Stage A

Status: **PENDING EXPLICIT REVIEW; NOT INSTALLED OR IMPLEMENTED.** Checked against installed metadata and official published release metadata on 2026-11-12. This document is a proposal, not a dependency declaration, lock update, licence approval or runtime compatibility test.

## Minimum proposed closure

| Distribution | Exact version | Licence | Change |
| --- | --- | --- | --- |
| opentelemetry-api | 1.45.2 | Apache-2.0 | Retain installed M10/M21 pin |
| opentelemetry-sdk | 1.45.2 | Apache-2.0 | One new direct optional dependency |
| opentelemetry-semantic-conventions | 0.66b2 | Apache-2.0 | One new mandatory SDK dependency; prerelease pin requires explicit review |
| typing-extensions | 4.16.0 | PSF-2.0 | Retain installed pin; satisfies >=4.5.0 |

The [SDK 1.45.2 release metadata](https://pypi.org/pypi/opentelemetry-sdk/1.45.2/json) requires `opentelemetry-api==1.45.2`, `opentelemetry-semantic-conventions==0.66b2` and `typing-extensions>=4.5.0`. Its optional `file-configuration` extra is excluded. [Semantic-conventions 0.66b2 metadata](https://pypi.org/pypi/opentelemetry-semantic-conventions/0.66b2/json) requires that same API and typing floor. [API 1.45.2 metadata](https://pypi.org/pypi/opentelemetry-api/1.45.2/json) requires only the typing floor. All three declare Python >=3.10; the project's Python 3.12.8 meets that metadata requirement. The proposed wheels are pure Python (`py3-none-any`), not native-platform wheels. No existing pin needs changing.

Published wheel SHA-256 pins, for verification before a separately approved install:

| Wheel | SHA-256 |
| --- | --- |
| opentelemetry_sdk-1.45.2-py3-none-any.whl | `ff974ea70ee4f1d51e2ec152db37c2b626c7bf82bb3f7d86114fd8704e7199c6` |
| opentelemetry_semantic_conventions-0.66b2-py3-none-any.whl | `4cbe61e5f9275d57ab31708446e7938ef4291ebbe6a7fca6f7a629c5acae87d8` |

Only metadata was inspected. No wheel was installed, imported or executed. Licence text/NOTICE retention, distribution hash verification, a current dependency/security review and actual SDK/API tests remain approval/install-time checks. Published metadata is not a production-security attestation.

## Proposed declaration/constraint impact after approval

Add an optional `observability` extra containing only `opentelemetry-sdk==1.45.2`. Add a new M22 constraints file chaining the unchanged M21 constraints, then pin SDK 1.45.2 and semantic-conventions 0.66b2. The existing 37-distribution closure becomes **39**, assuming the same extras/Python platform and no other change. The installed API and typing pins stay unchanged. Inspect resolver output before proceeding if any extra distribution or pin change appears.

No requirements file, pyproject dependency table or prior wheel manifest is changed in Stage A. Future manifests must record the complete actual environment, not just these two additions. Recheck the two release records and hash/licence evidence when approval is given.

No OTLP exporter, Azure Monitor distro/exporter, gRPC, automatic instrumentation, collector, FastAPI instrumentation extra or file-configuration extra is proposed. Local manual SDK recording does not need a network exporter. Azure export remains disabled and requires separate future scope and cloud authorisation.

## Local recording strategy proposed for Stage B

Use explicit host-created SDK TracerProvider/MeterProvider objects. Reuse existing UUID correlation and safe logging. No provider configuration, worker thread, environment-based resource discovery, credentials or export occurs at import. Use the installed API's W3C propagation; validate bounded untrusted context and never derive authority from it.

The [trace export interfaces](https://opentelemetry-python.readthedocs.io/en/latest/sdk/trace.export.html) support local exporters/processors. Propose a memory-only, allowlisted SpanExporter and nonblocking local processor; redact before retaining or serializing anything. Do not use raw console exporters or an unbounded in-memory accumulation as the application sink. Propose a pull-based local metric reader using the [SDK metric interfaces](https://opentelemetry-python.readthedocs.io/en/latest/sdk/metrics.export.html), with bounded series and no periodic cloud export. Verify these APIs against the pinned SDK after approval; documentation alone is not execution evidence.

Proposed budgets: 128 spans per case, 4,096 retained spans and 4 MiB serialized telemetry per run, 64 metric series, 16 allowlisted attributes per event and 128 characters per string value. Predetermine the expected trace graph before collection. Overflow increments a bounded drop counter and makes missing evidence visible; it cannot be silently scored as full coverage. Any future file sink must be explicit, private, bounded and exclusively created outside source/reference data. Measure local overhead; no hard native-CPU or exporter-latency guarantee is claimed.

Record stage/result/error category, bounded attempts/durations and safe version identifiers. Omit document text, prompts/responses, tokens/cookies/keys, arbitrary exception details, URLs/baggage and case IDs in metric labels. Telemetry stays operational evidence, separate from every unsampled M20 business decision/audit transaction. Export failure cannot grant access, rewrite state or turn an audit-write failure into a successful commit. Preserve M21's existing fail-closed identity/logging behaviour.

Stage A adds no telemetry implementation. Stage B still needs explicit approval of this dependency closure, prerelease dependency, budgets, instrumentation boundaries and the complete remaining implementation scope.
