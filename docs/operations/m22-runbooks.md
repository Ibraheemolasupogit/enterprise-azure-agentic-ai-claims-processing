# M22 offline operational runbooks

These procedures are exercised against disposable synthetic local services by `make quality-ops-check` and the [M22 CLI](../../README.md#m22-stage-b--offline-evaluation-and-operations). They do not authorise deployment, spend, real claim decisions or automatic remediation. The run record distinguishes injected conditions from actual guards/process recovery. Keep canonical and safe telemetry outputs together; never copy credentials, contexts, narratives or whole databases into incident logs. Owner roles below are responsibilities, not fabricated approvals or notified individuals.

## Dependency failure

Owner: operator. OPS-DEPENDENCY triggers at one failed dependency attempt in the current local snapshot. Inspect safe stage/result counts and correlation, confirm whether failure or timeout exhausted the existing two-attempt budget, and keep failed work in its guarded state. Do not increase retries automatically or substitute a successful assessment. Re-run a fresh approved synthetic workflow only after the local dependency is healthy.

Exercise: `workflow_outage` and `workflow_timeout` each make two real failed policy-stage attempts and end failed with no outcome. `workflow_retry_once` fails once then reaches awaiting_human_review; `workflow_none` has one successful attempt. Timeout uses an actual bounded async deadline. `test_timeout_retry_stale_and_anchor_controls_have_real_positive_controls` checks these observations. This does not recalibrate M12 wall-clock limits.

## Storage and audit

Owner: operator. OPS-STORAGE triggers at one failed write. Stop acknowledgement of the failed operation; retain last known state and independent trust context. Check safe failure category, expected revision and audit/decision counts through authorised reads. Do not repair projections, recompute hashes, discard audit, reset keys or copy an old database over the current one. Escalate corrupt/incompatible state for an explicitly designed recovery path.

Exercise: `storage_projection_failure_rollback` raises a genuine SQLite error after the projection write and verifies rollback to the prior state. `test_storage_failure_and_export_failure_cannot_acknowledge_partial_outcome` fails after the audit write while export also fails: zero decisions, unchanged projection and the original four audit events remain. A fixed safe storage error is returned, never an acknowledged partial outcome.

## Identity and stale requests

Owner: security reviewer. OPS-STALE and OPS-TOOL trigger at one denial. Verify current canonical session, assignment, revision and grant independently; correlation/trace context is not identity. Retain denial/history evidence. Do not replay an old receipt with revoked credentials or restore authority from a saved token, an older lifecycle database or a new signing key.

Exercise: API/UI reject a revoked replay; API and genuine MCP calls reject missing authority despite tracing metadata. `stale_revision` denies an old revision. `revoked_duplicate_after_process_recovery` recreates current authority in a fresh process and denies the revoked reviewer's duplicate while retaining one historical decision/five audit events. `current_anchor_rollback` uses the original fixed public key and a current independent anchor: signature remains valid but stale state is denied. Test: `test_timeout_retry_stale_and_anchor_controls_have_real_positive_controls`. Current-key/anchor custody and shared revocation propagation remain deployment requirements.

## Outbox and process recovery

Owner: operator. OPS-OUTBOX triggers at one dead item. Inspect safe attempt/state metadata. Existing local outbox retries are capped at three; retain dead state and escalate, without resetting its budget or inventing external delivery. Reopen only a same-runtime store with original independently retained approved synthetic source/context, lifecycle integrity key and latest rollback anchor. Acquire fresh canonical authority and read the acknowledged result before attempting its duplicate.

Exercise: `bounded_outbox_retries` records pending/pending/dead. A fresh child observes one dead item with three attempts (`outbox_retries_survive_restart`). Actual SIGKILL before and after business commit, followed by fresh recovery and duplicate execution, yields one decision/five audit events and the same receipt. Test: `test_acknowledged_audit_survives_failed_export_and_fresh_process_recovery`. No historical store is migrated or regenerated; no external communications, exactly-once network delivery or hardware-loss claim follows.

## Telemetry failure

Owner: operator. OPS-EXPORT and OPS-DROP trigger at one failure/drop. Treat trace coverage as incomplete, retain visible counters, and inspect only safe records. Stop asserting full observability; keep business audit independently required. Do not retry a committed outcome to recreate a trace, disable identity checks, copy raw exceptions into logs or increase budgets without review. Use a new bounded telemetry run after correcting the local sink.

Exercise: a real SDK exporter failure leaves an acknowledged M20 outcome intact across fresh-process replay. Capacity one retains one span and drops the second visibly. Exporter exceptions are contained before SDK logs; a zero-sampling test still commits one decision/five audit events. Simultaneous audit-write/export failure cannot commit. Tests: `test_acknowledged_audit_survives_failed_export_and_fresh_process_recovery`, `test_zero_trace_sampling_cannot_remove_business_audit`, `test_storage_failure_and_export_failure_cannot_acknowledge_partial_outcome` and `test_metric_collection_failure_is_visible_in_the_same_health_snapshot`.

## Review backlog

Owner: supervisor. OPS-REVIEW triggers at two pending entries in the current local snapshot. Confirm the queue through currently authorised assigned reads, prioritise human review under existing separation rules and retain recommendation/outcome distinctions. Do not auto-approve work or bypass identity/assignment to reduce the count.

Exercise: actual ASGI queue observation has one entry, therefore CLEAR. `alert_controls` supplies exactly two and one as explicitly SIMULATED positive/negative threshold inputs for this alert, as for the other seven rules. `test_live_signals_trigger_owned_alerts_and_backlog_threshold_stays_clear` verifies real signal status and all threshold controls. No measured staffing/handling-time, continuous monitoring or production notification guarantee is claimed.
