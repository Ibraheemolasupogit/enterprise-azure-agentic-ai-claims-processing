# Infrastructure validation — context handover (2026-11-21)

Authority stays with [`infra/azure-validation/contract.json`](../../infra/azure-validation/contract.json)
and the dated records in [`infra-validation-approvals/`](infra-validation-approvals/). This note
grants nothing. Full procedure: [infrastructure-validation.md](infrastructure-validation.md).

This handover preserves the recording-time test results below. The
[execution and closure runbook](infrastructure-validation.md#execution-and-closure-runbook)
describes the current preparation and remaining owner decisions.

## Repository and recording state

- **HEAD and local `origin/main`:** `7bb5399`; clean before this recording. No Git writes by
  the assistant. The owner must manually review and commit the new record, contract and status docs.
- **Recorded:** Stage 6 `cloud_validation` and G9, at **2026-11-21T00:48:17Z**, repository-owner,
  reviewed baseline `7bb5399`. [Immutable record](infra-validation-approvals/2026-11-21-stage6-cloud-validation.md),
  SHA-256 `3c15dfde020c6a0931628cbeb5c3db0e07c21de980d9c7792ffec4de271dbccb`.
- **Contract:** `APPROVED_FOR_VALIDATION`, `provisioning_allowed=false`. Exactly ten reviewed
  leaf fields changed: four Stage 6 approval fields, five execution bindings and status.
- **No Azure execution occurred.** Recording only was requested. Separate owner instruction,
  committed-file integrity checks and the November 25 schedule are prerequisites to execution.
- Both repository gates remain `@allowed([false])`: `provisioningApproved` in the validation
  template and `deploymentEnabled` in the M23 template. Application deployment remains prohibited.

## Approvals and immutable evidence

| Stage | Approval | Status | Evidence SHA-256 prefix |
| --- | --- | --- | --- |
| 1 | `scope` | APPROVED, subscription-budget amendment | `32218157`; original `ccfa1bab` preserved |
| 1 | `network`, `region_capacity`, `identity_rbac` | APPROVED | `b77a417f`, `0bbf4246`, `66eaf996` |
| 2 | `cost_exposure` | APPROVED | `ccfa1bab` |
| 3 | `provider_registration` | APPROVED, owner performed Microsoft.Network registration | `6ac6063f`; execution `f1ffc2b3`, supplement `d4fcc724` |
| 4 | `budget` | APPROVED; subscription budget owner-created | `55641a5f`; execution `ec041f24` |
| 5 | `execution_template` | APPROVED, recorded conditions retained | `1d69d8bb`; G1 `df2d7079`, G2/G3-A `bcb8f790` |
| 6 | `cloud_validation` and G9 | APPROVED; NOT EXECUTED | `3c15dfde` |
| 7–9 | `provisioning`, `teardown`, `evidence` | PENDING | — |

Never edit a hashed or cited historical record. Corrections require a new dated record.
`H_RECORD` remains symbolic inside the Stage 6 record; its actual file hash is stored only in
the contract, avoiding a self-hash cycle.

## Exact bindings and local bundle

The Stage 6 record contains the full hashes for the two unchanged G9 command blocks, Stage 6
script, reviewed and execution ARM templates, parameters, preflight and validator. The compiler
remains Bicep 0.48.1 (`62cd5958…`); reviewed source `4beed4f7…`, execution source `8715d9a0…`.

- Reviewed ARM: `28c29de5f4d0bc36529a5682246da5324cb9b2db8267583b8227254e55c41a17`.
- Execution ARM: `dfc26600fb9c8748fdf9fead8078bf281f4482ae27ed987c004adf33bb970989`.
- Parameters: `d668581c7e7c0b9a025ebedc9c124058be6ea371ff649084f9dd9c3ed6208b7c`.
- Run ID: `infraval-20261125-01`; group: `rg-claims-infraval-uks-tmp01`; region: `uksouth`.
- Expiry: `2026-11-25T16:00:00Z`. Optional environment remains disabled; daily log cap is 1 GB.
- The what-if hash and Stage 7 window fields remain **null**. No Stage 7/8/9 approval was added.

The new git-ignored bundle is `outputs/deployment/infra-validation-execution/upload-stage6/`:
exactly the six payload files (`contract.json`, `execution.json`, `infra_subscription_preflight.py`,
`infra_validation.py`, `parameters.json`, `reviewed.json`) and `SHA256SUMS`.
`sha256sum --strict -c SHA256SUMS` passes. The older `upload-provisional/` remains unchanged and
must not be used as the approved bundle.

The new manifest currently describes the updated **uncommitted** contract. After manual commit,
compare every bundled byte with the committed sources and approved hashes; regenerate if any
bytes change. The bound Stage 6 script and G9 blocks require their own exact hash comparisons.
Do not upload or execute from an unreviewed directory.

## Offline verification and outstanding check failures

- Contract/repository validation PASS; both repository gates FALSE_ONLY.
- Validation authorization returns `AUTHORIZED_FOR_VALIDATION_ONLY` / `NOT_AUTHORIZED`.
- Provisioning, execution-window authorization and teardown are refused (exit 78).
- All prior approval evidence, pinned artifacts and original draft/proposal bytes are unchanged.
- Strict procedure lint and shell syntax pass; Ruff lint passes; strict mypy passes (194 files).
- Infrastructure suites: **303 passed, 5 failed**. Four tests assume the repository still has
  `PREPARATION_ONLY` and need a separately reviewed test correction for the authorised transition.
  The Stage 8 cancellation/resume stub test also failed because two immediate runs used the same
  second-based `ev8-…` directory name (`mkdir: File exists`). No procedure or test was changed.
- Broad formatting check also fails on the unchanged `docs/milestones/m25-p2/README.md` Python
  example. Its bytes equal baseline `7bb5399`; it was not changed by this recording.
- Full tracebacks and hash inventory are in the git-ignored
  `outputs/deployment/infra-validation-execution/recording-audit/` directory.

These check failures require owner review before a clean-check commit recommendation. Do not
change pinned procedure bytes or historical records to work around a failure. No full application
suite or live Azure integration is claimed by these checks.

## G9 and November 25 timing

G9 creation and empty-group cleanup are limited to the exact proposal blocks bound in the Stage 6
record. Creation proves absence first and checks state, location, exact tags, resources and locks.
Cleanup requires the same subscription and run tags, no resources or locks, and no active
deployment. Failed checks stop without bypass, force or deletion of other resources.

| Time (2026-11-25 UTC) | Requirement |
| --- | --- |
| From 08:00 | Optional Microsoft.Consumption check; G9 creation, only after separate owner instruction |
| By 11:00 | Stage 6 PASS; otherwise abort |
| 11:00–12:45 | Owner reviews what-if; any Stage 7/8 decisions must be separately recorded and committed |
| 13:00–15:00 | Planned deployment window; NOT authorised by Stage 6; contract window fields remain null |
| By 16:00 | Hard expiry; on abort, empty-group cleanup and verified absence must be complete |

Initiate empty-group cleanup immediately on abort, subject to every existing check. If cleanup
cannot complete or absence cannot be verified by expiry, stop, record the failure and request
separately authorised recovery. This supersedes the proposal's earlier cleanup timing without
changing its command bytes. No provisioning, other-resource deletion or Key Vault purge follows
from Stage 6. Moving T0/expiry/run ID requires new dated records and new affected bindings.
The resource-group budget's start date requires deployment in November 2026 UTC.

## Remaining execution prerequisites and inherited limits

1. Owner reviews the recorded diff and check failures, then manually commits the approved files.
2. Owner verifies the bundle and bound commands against committed bytes, and separately instructs
   the November 25 execution. No Azure command is authorised for the assistant by this task.
3. Each Cloud Shell session must pass the subscription preflight using the approved commitment,
   name and Enabled state. G9 absence and post-state checks must all pass before Stage 6.
4. `Microsoft.Consumption` registration remains unverified; the Stage 6 record retains the optional
   read-only check. Any provider or CLI/shape/policy/quota error stops; no registration or workaround.
5. What-if must pass the unchanged exact-seven-Create validator. Unsupported, missing, duplicate
   or unexpected changes stop for owner decision. Its passing hash is for a later Stage 7 decision.

G1 is resolved for its five named providers; G2 and G3-A are approved. G4–G8 retain their recorded
limits: November timing, unknown live what-if shapes, fixed PREPARATION_ONLY tag label, only the
resource-group budget in teardown state, and the subscription-budget retention clarification.

Prior Azure state is **owner-reported on 2026-11-20, not refreshed**: the subscription budget exists
(2 GBP, filtered to this group); the validation group and NetworkWatcherRG were absent. Keep the
subscription budget for post-teardown checks; early deletion needs separate approval.

## Standing prohibitions

- No Azure calls by the assistant; no provisioning, provider registration, Stage 7/8/9 approvals,
  other-resource deletion, teardown, purge, application deployment, or M23 gate change.
- No changes to bound artifact bytes, prior immutable evidence, unrelated approvals or values.
- No downloads, installations, builds, trust-store changes, Git add/commit/push or history rewrite.
- Keep raw subscription identifiers and credentials out of tracked files; approver is repository-owner.
- M22 restrictions, M23 SECURITY GATE NO-GO, M24's six NOT_TESTED demonstrations and M25 OFFLINE
  COMPLETE remain unchanged. Stage 6 approval is not proof of successful cloud validation.
