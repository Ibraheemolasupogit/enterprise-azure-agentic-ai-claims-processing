# Milestone 22 — Reproducible quality and operations

**Stage A prepared for review. Stage B NOT AUTHORISED and not implemented. M22 is not complete.** Baseline: committed M21 `9c3cc78a16764411005893371a80ac9f291b354e`; accepted baseline 1,338 source/wheel tests and 111 focused security tests. No baseline test count is a golden-suite result.

## Stage A deliverables

- Versioned input/prediction, candidate-reference, blank-review, ratio/macro/scalar measurement, gate and run-manifest contracts in `claims_ai.quality_ops`. There is no evaluator or telemetry implementation.
- New [60-case candidate suite](../../data/evaluation/m22/README.md), distributed 15 ordinary-damage / 10 exclusion/date / 10 evidence / 10 policy / 10 security / 5 recovery cases. All are PENDING_REVIEW with null actual reviewer/approval/signature fields.
- Exclusive read-only candidate files, exact hash inventories, per-source quotes and per-case reference/review bindings. External candidate-manifest SHA-256: **`42e0eb827c26cbd3202c127f777aef6cd17c59e543548ff5b368f1008a361d8b`**.
- [Frozen proposed gates, denominator rules, leakage disclosures, reproducibility and actual review procedure](../quality/m22-stage-a-contracts-and-holdout.md). No score, actual model prediction, fabricated independent review or release approval is produced.
- [Exact OpenTelemetry dependency proposal](../dependencies/m22-opentelemetry-proposal.md): SDK 1.45.2 plus mandatory semantic-conventions 0.66b2, retaining API 1.45.2 and typing-extensions 4.16.0. Two proposed additions, no installed/declaration changes.

The quality gates are frozen as proposals before scored evaluation: >=95% critical fields and macro recall@5; 100% applicable rule/support/routing/audit/trace coverage; zero unauthorized actions, lost/duplicate acknowledged outcomes or telemetry leaks. Performance/human-effort targets retain their approved-workload/study prerequisites. Unavailable and independently unreviewed measurements remain NOT_TESTED; actually observed safety violations remain FAIL even while labels await review.

## Review and blockers

1. Obtain genuine independent per-case/source review and exposure/leakage assessment. Author-visible native-text/control candidates cannot be advertised as a blind multimodal held-out benchmark. Reference-policy/service mapping needs review; no existing operational rule is changed.
2. Approve applicable gates, denominator rules and any new reviewed candidate version. Keep v1 and every old evaluation/report unchanged. Use a separate authenticated review/release record; a hash or status string does not authenticate an approver.
3. Review the exact SDK closure, Apache-2.0 notices, mandatory prerelease semantic-conventions dependency and local recording budgets. Compatibility is metadata-checked, not runtime-tested; SDK distributions are not installed.
4. Obtain separate explicit Stage B authorisation. No dependency installation/declaration update, evaluator, telemetry, dashboard/alert implementation, M22 fault execution or runbook exercise begins under Stage A.

M20 audit/outbox atomicity and M21 identity/session/grant gates are unchanged. New package code changes whole-package M12/M20 fingerprints; future tests use fresh same-runtime stores, never migrate or rehash historical evidence. Local HMAC/SQLite/anchors, admission races, telemetry/audit separation, real-provider gaps and production risks remain as documented.

The M8 four failures and M12 timing limits remain; original M19 scenarios/reports retain **80 PASS / 0 FAIL / 8 NOT_TESTED**. No live provider/cloud, Azure access/export/spending, new agent, M23 work, Git staging/commit/push or Stage B work is authorised. Stop after Stage A reporting.

## Stage A verification record

- **218 focused source tests passed**: 42 Stage A construction/contract checks plus existing M8 retrieval, benchmark scoring and 111 M21 security checks. These are verification tests, not 60 scored golden cases.
- **42 Stage A tests passed against a separately built wheel**, outside the checkout with isolated Python, pytest source path replaced and all 22 loaded application-module origins verified. Existing pinned dependencies are shared; no package/dependency is installed.
- Ruff lint/format and strict mypy pass across **158** Python files; `pip check` passes. Metadata inspection confirms SDK/semantic-conventions remain uninstalled and all existing dependency declarations remain unchanged.
- Before/after SHA-256 checks preserve all **187** existing output files, **173** existing data files, **125** prior runtime files, **27** prior test files and every existing requirements file. Only MANIFEST, README and the roadmap change among baseline files.

The accepted 1,338-test full source/wheel baseline remains historical; full-suite, SDK runtime and Stage B acceptance validation are not claimed by this Stage A record. Current wheel/source-archive checks use new temporary paths and do not regenerate historical reports or package artifacts. No M22 prediction/scored-evaluation, independent review or telemetry has run.
