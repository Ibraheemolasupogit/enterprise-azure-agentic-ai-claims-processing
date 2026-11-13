# Milestone 22 Stage B — offline evaluation and operational observability

Stage B is separately authorised and implemented for offline engineering. Independent held-out review is pending; M22 independent-quality/production acceptance is not granted. The [Stage A record](milestone-22.md), [frozen contracts](../quality/m22-stage-a-contracts-and-holdout.md), candidate labels/manifests/review templates and historical evidence are preserved byte-for-byte. Its earlier NOT AUTHORISED statements describe that historical stage, not this later authorisation.

## Delivered scope

- Deterministic case/cohort runner with the externally pinned 60-case candidate roster, all PENDING_REVIEW / NOT_TESTED, and all 12 independent/live-quality gates NOT_TESTED/null. Unconfigured independent approval always rejects; no flag, signature string or CLI option bypasses it.
- Six separate development inputs, separately authored SIMULATED labels and a real bounded native-text parser in an isolated trusted subprocess. Missing outputs retain their denominators; harness errors remain NOT_TESTED/incomplete. This is not independent quality, OCR, live model or claim decision evidence.
- Genuine private OpenTelemetry SDK trace and metric providers over opt-in wrappers around existing workflow stages, governed tools, API/UI/MCP and M20 recovery. Bounded W3C context crosses actual ASGI/process boundaries. Safe local spans/logs/metrics omit credentials, identity claims, narratives and evidence bodies. Operational telemetry never replaces required audit or changes business/identity decisions.
- Eight versioned local dashboard panels/owned alerts, executable snapshot checks and separately classified positive/negative threshold controls. Seventeen real local fault/guard/recovery controls cover dependency outage/deadline/retry, stale requests, SQL/export/capacity failure, outbox exhaustion/restart, current-anchor rollback and actual pre/post-commit SIGKILL.
- [Architecture](../architecture/offline-quality-and-operations.md), [exercised runbooks](../operations/m22-runbooks.md), requirements traceability and risk updates. Existing production risks remain open.

## Reviewed dependency installation

API and SDK are **1.45.2**, semantic-conventions **0.66b2**; Python is 3.12.8. Official PyPI metadata, actual downloaded wheel SHA-256, Apache-2.0 licence text/hash, resolver output and SDK API execution were verified before implementation. Installation was hash-required and local/offline from those two wheels, into the existing repository `.venv` only. No previous pin or global package was changed. The complete retained closure grows from 37 to 39 distributions.

[M22 constraints](../../requirements/m22-constraints.txt) chain unchanged M21 pins; the optional observability extra declares only the SDK. [Wheel verification inventory](../../requirements/m22-wheel-manifest.json) retains filenames, published/actual hashes, requirements and actual licence hashes. The separately retained install/resolution/environment evidence records the two additions. No OTLP, Azure Monitor, auto-instrumentation or provider extra was added. SDK APIs exercised include TracerProvider, SpanLimits, SimpleSpanProcessor/SpanExporter, MeterProvider, View, InMemoryMetricReader, Counter/Histogram and W3C propagation; global providers remain unchanged.

## Evidence and interpretation

Final validation, package inventories, canonical reproduction and preservation checks are retained in new Stage B output paths. Full test results are engineering checks rather than golden-suite scores. Canonical reports bind the complete runtime fingerprint, actual 39-distribution environment, candidate/gate/spec hashes and exclusions. Raw local telemetry retains genuine IDs/parents/measured durations separately; its canonical report hash links it to the deterministic report. All artifacts are exclusively created outside input trees; historical reports are not regenerated.

Actual fault controls use private temporary stores with fresh same-runtime supplied synthetic approval, current M21 authority and independently retained keys/anchors. Export failure, pre/post-commit death and recovery retain one decision/five audit events and the same duplicate receipt. A revoked identity's duplicate is denied after restart; retained outbox state still has three exhausted attempts. Storage failure rolls back, including simultaneous audit/export failure tests. Trace sampling zero leaves required audit intact. Alert backlog is actually measured below threshold; its positive condition is explicitly simulated, not invented operational backlog.

## Remaining limits and acceptance boundary

Engineering acceptance is for the authorised offline infrastructure only. Genuine independent per-case/source review, exposure assessment, approved quality gates and an authenticated review/release verifier remain required before any independent scoring. No held-out benchmark is RELEASED. Native-text author-visible development conformance cannot establish independent model/retrieval/rule/routing/human-effort/performance quality; all unavailable metrics remain NOT_TESTED.

No live Entra, provider, cloud deployment/export, Azure operation/spend, remote notification, production SLO, browser/TCP assurance, real insurance authority or autonomous claim outcome is added. The trusted subprocess is not an OS sandbox; bounded local memory telemetry is not durable/WORM audit or a hard CPU/latency limit. Same-runtime local SQLite recovery is not power-loss/distributed/cloud durability. M20/M21 key/current-anchor custody, cross-store admission races and host-compromise limits remain. Whole-package runtime fingerprints intentionally reject historical workflow/stores; no silent migration or rehash occurs. Preserve M8's four failures, M12 timing sensitivity and M19 **80 PASS / 0 FAIL / 8 NOT_TESTED**. M23 is not started; no Git staging, commit or push is performed.

## Final Stage B verification record

Verified on Python 3.12.8 / macOS arm64 in the isolated project environment. These are engineering test totals, not independent golden-suite results.

| Check | Observed result |
| --- | --- |
| Focused M22 source checks | **98 passed**: 42 unchanged Stage A cases and 56 Stage B unit/integration/security/operational cases |
| Complete source pytest | **1,436 passed**, 537.11 seconds |
| Independent installed-wheel pytest | **1,436 passed**, 515.89 seconds; unmodified copied tests outside the original checkout, real byte-identical reference data, all loaded application origins under wheel site-packages |
| Ruff lint / formatting / strict mypy | PASS across **174** Python files; strict settings retained |
| Dependencies | `pip check` PASS; all **39** runtime pins match; full **52**-distribution environment recorded; exactly the two reviewed additions and no changed prior distribution |
| SDK evidence | **74** primary spans, **3** linked recovery-process spans, **44** metric points; no primary drops/export/metric/instrumentation failures; actual measured durations retained separately |
| Operational and alert checks | **17 PASS / 0 FAIL** runtime controls; eight positive/eight negative alert threshold controls. Seven actual fault signals TRIGGERED; actual one-item backlog CLEAR |
| Reproducibility | Two source reports and one independent-wheel report are byte-identical; raw telemetry IDs differ as expected and bind the same canonical content hash |
| Wheel/source package | Wheel has all **144** current Python runtime files byte-identical plus `py.typed` and correct observability metadata. Final source archive verifies all **443** nonignored repository files, including frozen data/contracts/tests and updated documentation |
| Historical preservation | All **187** original outputs, **182** original data files, **131** pre-existing runtime files and **28** pre-existing test files unchanged. Of **607** initial files, only the seven intended README/roadmap/risk/traceability/build/dependency declaration files changed; **600** remain byte-identical |
| Git | HEAD remains `9c3cc78a16764411005893371a80ac9f291b354e`; no staged changes, commit or push |

Authoritative evidence is under [package/validation outputs](../../outputs/packages/m22-stage-b/), with `source-accepted.txt`, `wheel-accepted-real-data.txt`, `focused-accepted.txt`, `quality-checks-accepted.json`, `dependencies-final.json`, `reproducibility-accepted.json`, `packaging-accepted.json`, `preservation-accepted.json` and the exact [Stage B file inventory](../../outputs/packages/m22-stage-b/stage-b-files.json). Canonical reports and their private safe telemetry are [retained separately](../../outputs/quality/m22-stage-b/) as `accepted-source-a`, `accepted-source-b` and `accepted-wheel`. Their identical serialized report SHA-256 is `0c401924d24a2e4d24a0467d6a2d72475fbc1a1afb68daa9d369f460c3429bc2`. Generated evidence is retained locally outside the distributable source inventory.

The earlier symlinked-data wheel setup recorded **1,434 PASS / 2 FAIL**, preserved in `wheel-accepted.txt`. It exposed the unchanged Stage A authoring guard's assumption that repository `data` is a real directory: canonical destinations under an aliased data root escaped its repository-relative namespace comparison. Only two newly generated test directories were moved to private scratch; every original data/evidence file remained unchanged. All 42 Stage A wheel checks then passed with real data copies, followed by the complete passing wheel rerun. No failed run is rewritten as a pass. Stage B's canonical output exclusion is separately tested; authoring through aliased repository roots remains unsupported and requires a separate correction before that topology is accepted.

**Recommendation: CONDITIONAL ACCEPT for M22 engineering.** The authorised Stage B infrastructure passes in the tested canonical-data layout. Independent holdout review/release is still pending, and the preserved Stage A authoring-alias limitation remains open. Neither this recommendation nor the passing engineering reports releases the benchmark or accepts production security/deployment.

## Independent golden-suite review packet

Documentation-only review preparation adds the [reviewer-only v1 packet](../quality/m22-independent-review/v1/README.md), [60-case inventory](../quality/m22-independent-review/v1/case-inventory.md), source-bound case notes, checklist, separate blank adjudication/release templates and [integrity verification](../quality/m22-independent-review/v1/verification.json). All 60 original cases remain PENDING_REVIEW; all labels remain author proposals. There is no fabricated reviewer, approval, signature, independent-quality score or benchmark release.

Submitted candidate: `data/evaluation/m22/v1`; candidate-manifest SHA-256 `42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b`. Independently retained SHA-256 of the packet's [hash-inventory.json](../quality/m22-independent-review/v1/hash-inventory.json): **`3111f57a4ce0f9edbe332501c0a7b25c0bb1356999816d8a5b19c2da10bc8658`**. The inventory binds the eight other packet files; the submission manifest binds all eight original candidate artifacts and each case/asset. No self-hashing cycle or signature claim is introduced.

Preparation validation checked 60 case/label/review bindings, 178 native-text asset hashes, 290 quoted and ten explicit-null field proposals, 106 policy clause references, 180 per-case review questions, all 12 unchanged gate proposals and local source links. Eleven selected source integrity/approval-guard tests passed. A monitored prediction loader opened only its two frozen allowlisted input files; runtime source, input bytes and runtime paths remain unchanged. These are preparation/structural checks, not independent correctness, blindness or training-contamination verification.

All pre-existing source, test, data, dependency and output files are preserved byte-for-byte; only this existing milestone record receives the packet reference. No historical report/package is regenerated. Earlier 1,436 source/wheel and 17 operational-control results remain the historical Stage B record and were not rerun for this documentation-only packet. Published packet files are read-only; reviewers complete copies in separately retained actual review records rather than editing v1.

Remaining acceptance requirements: genuine independent source/label adjudication and exposure/holdout-eligibility assessment; a real owner's gate/applicability/release decision; reviewed candidate-to-service mapping, future prediction isolation/freeze and an independently authenticated approval verifier before separately authorised scoring. Fresh unexposed cases may be required in a new version. The Stage A authoring-alias limitation remains open; unavailable live/model/production metrics remain NOT_TESTED. This packet changes no M22 acceptance recommendation and authorises no cloud/model/spending, current claim authority, M23 work, commit or push.
