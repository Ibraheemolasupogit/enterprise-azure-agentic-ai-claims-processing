# Milestone 2 — Python engineering foundation

Status: **COMPLETE — IMPLEMENTED and LOCALLY TESTED foundation scope**; 2026-10-30. This milestone delivers a Python library, not an operational claims-processing application. Milestone 3 has not started.

## Files and implemented scope

| Files | Delivered behavior |
| --- | --- |
| [pyproject.toml](../../pyproject.toml), [Makefile](../../Makefile), [MANIFEST.in](../../MANIFEST.in) | `src` package, dependency/version constraints, Ruff/mypy/pytest settings, local checks and wheel/sdist builds |
| [Package initializer](../../src/claims_ai/__init__.py), [py.typed](../../src/claims_ai/py.typed) | `claims_ai`, distribution `northstar-claims-ai` version 0.1.0, typed-package marker |
| [models.py](../../src/claims_ai/models.py) | Frozen, extra-forbidden Pydantic v2 contracts with schema version 1.0 and synthetic-only markers |
| [lifecycle.py](../../src/claims_ai/lifecycle.py) | State graph, revision checks, human/supervisor guards and validated transition records |
| [config.py](../../src/claims_ai/config.py), [.env.example](../../.env.example) | pydantic-settings, prefixed environment variables, bounded local defaults and explicit dotenv opt-in |
| [logging.py](../../src/claims_ai/logging.py) | JSON events, context-local UUID correlation, safe-field allowlist and payload redaction |
| [ports.py](../../src/claims_ai/ports.py) | Async structural protocols for document processing, exact-bundle retrieval, atomic case persistence, evidence reconciliation and policy explanation; no adapters |
| [Synthetic fixtures](../../tests/conftest.py), [model tests](../../tests/test_models.py), [state tests](../../tests/test_lifecycle.py), [config tests](../../tests/test_config.py), [logging tests](../../tests/test_logging.py) | Focused local positive/negative unit tests; no service mocks claiming Azure behavior |
| [README](../../README.md), [architecture status](../architecture/target-architecture.md), [roadmap](roadmap.md), this record | Current status, setup, evidence and scope sequencing |

## Contracts and validation

Implemented models cover claims; document metadata/type/scan assertions; source-linked evidence; policy schedule/wording/endorsement artifacts and versions; policy clauses/citations; supplied rule traces/assessments; reviewer decisions; case snapshots and transition requests/records.

Identifiers use distinct `NS-CLM`, `NS-POL`, `NS-DOC`, `NS-EVD` and `NS-ASM` prefixes with eight uppercase alphanumeric suffix characters. Document references must exactly match a synthetic case/document object path and permitted media suffix; URLs and traversal paths are rejected. Hashes are SHA-256-shaped metadata, checked for consistency, not recomputed from bytes. Evidence must reference an accepted, matching document in the same case and a valid page/normalized bounding region. Duplicate/dangling references fail validation.

Policies require ordered effective-date metadata, unique artifact references and nonempty policy/index/rule-pack versions. Citations must match the exact bundle/version/hash. This does not verify policy contents, publication approval, clause semantics or loss-date eligibility. A caller-supplied required-document checklist verifies accepted, referenced evidence; no motor-product coverage checklist is hardcoded. Money uses Decimal with GBP, nonnegative values and at most two decimal places; binary float inputs are rejected. No financial/coverage calculations are implemented.

Models are immutable with tuple collections, nested-instance revalidation and hidden sensitive values in representations/error strings. Normal serialization still contains domain content for future controlled storage; it is not a redaction API. Synthetic markers declare intended data provenance, not proof that arbitrary text is free of real data. Pydantic trusted construction/copy APIs must not be used as untrusted-input validation.

## State and human oversight

Normal flow is `received → validating → extracting → assessing → awaiting_review → closed`. Validation/extraction/assessment can branch to `awaiting_evidence`, `quarantined` or `processing_failed`; recovery restarts at `validating`. Closed cases and quarantined cases can return to validation only through a supervisor. This conservative guard refines the existing human-oversight decision; it prevents a service caller from silently reopening a reviewed outcome or releasing unsafe evidence.

Submitting for review requires a current assessment and matching policy/evidence snapshot. Every closure requires a human decision matching the trusted actor, claim, assessment and expected case revision, with reason and explicit evidence references. Ambiguous, high-risk, conflicting, injection-flagged, unsupported, adverse or undetermined assessments require supervisor handling, including invalidation/requesting evidence. Undetermined results cannot simply be approved closed; a supervisor must request evidence or explicitly override to a supported final outcome. Any adverse final outcome also needs a supervisor. Changed outcomes require an explicit evidence-backed supervisor override.

Stale updates, mismatched actors, future-dated decisions and unsupported transitions fail. Transitions preserve the previous snapshot, increment the revision once and invalidate the current assessment on return to evidence/validation. Direct construction of a transition record passes the same guards. Records include caller-supplied audit IDs/time/reasons; **nothing is persisted**. The repository protocol requires eventual atomic revision comparison, outcome and audit writes, including duplicate-event protection; no store or concurrency guarantee is implemented.

Role assertions are trusted inputs, not Entra authentication or case-level authorization. The future authenticated application must construct caller context and enforce access. No rule engine produces the supplied assessment outcomes in the fixtures.

## Configuration and confidentiality

Settings support only `local`/`test`, default INFO logging and a 10 MiB document-size setting bounded at 50 MiB. Production mode, cloud endpoints and credential fields are absent. Environment values override explicitly selected dotenv values; constructor values override environment values. Settings do not scan upload bytes or enforce limits at a nonexistent API boundary.

Logging emits fixed event names and validated operational IDs/counts/status/durations. Unknown field names/values, nested payloads, raw messages, formatted arguments and exception text are suppressed; known malformed fields become `[REDACTED]`. UUID correlation scopes reset safely and remain isolated across asynchronous tasks. This is local structured logging, not OpenTelemetry or a business audit store. Other application/dependency loggers are outside this package's redaction boundary.

## Verification

Verified on macOS with Python 3.12.8, Pydantic 2.11.7, pydantic-settings 2.10.1, pytest 8.4.1, Ruff 0.16.4, mypy 1.16.1 and setuptools 82.0.1. A local `.venv` reused preinstalled host libraries through `--system-site-packages`; no dependencies were downloaded/upgraded. Dependency ranges are bounded but no transitive lockfile or multi-version CI matrix is claimed.

- `make check`: **115 tests passed**, Ruff formatting/lint passed, strict mypy passed across 11 Python files.
- `make package`: wheel and source distribution built with no build isolation or dependency downloads. Verified six package modules and the `py.typed` marker in the wheel, and test fixtures in the source archive.
- Installed the wheel without dependencies into a separate temporary virtual environment reusing host libraries; isolated-mode Python verified imports came from that environment, distribution/package version agreement, schema generation and exactly two runtime requirements. The same **115 tests passed against the installed wheel**, using `-o pythonpath= --import-mode=importlib` to disable source injection.
- Rebuilt a wheel from the extracted source distribution without downloads; every package source file and `py.typed` matched the original wheel byte for byte. This checks code inclusion, not reproducible archive hashes or a clean-room dependency installation.
- Tests explicitly import `src`; independent wheel checks must override that test-path setting to establish installation correctness. Editable installation was also attempted, but this managed macOS filesystem marks generated `.pth` files hidden between tool calls, causing Python to skip them. Source-based tests plus independent non-editable installation avoid depending on that environment behavior.
- Documentation links, source whitespace and read-only Git diff checks passed. Git already contains the manual Milestone 1 baseline commit; no Git mutation was performed by this milestone. Existing Milestone 1 records describe their historical snapshot; current capability status is in this file and the README.

The existing host `packaging` 23.2 produces a non-blocking setuptools warning about optional license-expression validation. Builds succeed; no such license validation is claimed and no host package was upgraded. The local working virtual environment uses a non-editable wheel installation to avoid the managed filesystem's editable-path issue.

## Decisions, remaining gaps and acceptance

Python support is initially `>=3.12,<3.13`, matching the tested interpreter minor; widening it requires validation. Runtime dependencies are Pydantic v2 and pydantic-settings only. No FastAPI, cloud SDK, agent, search, gateway or telemetry package is added.

The approved request narrows the original Milestone 2 roadmap to foundation code. FastAPI/concrete persistence move to Milestone 3; fictional policy approval and rule implementation remain future work. No Milestone 1 architectural decision is replaced. Golden data, artifact parsing/scanning, input correction workflows, durable idempotency/audit, authenticated identities, policy resolution, coverage rules, service integration and operational performance are unverified/unimplemented.

Acceptance applies only to the listed foundation behavior and local checks. No cloud resources, deployment, spending, commit or push was performed. Stop after Milestone 2.
