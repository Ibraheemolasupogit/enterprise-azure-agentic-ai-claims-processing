# Stage 7 and 8 execution evidence — 2026-11-21

Run `infraval-20261121-01`, group `rg-claims-infraval-uks-tmp01`, region `uksouth`,
repository baseline `7b04b1c`. The private Stage 7 and 8 receipts are consistent with
the owner-reported deployment and teardown outcomes. All four Stage 7 receipt digests
matched the original Cloud Shell SHA-256 values supplied by the owner.

| Event | Outcome |
| --- | --- |
| Stage 7 deployment `infraval-20261121-01-deploy` | Owner reported `STAGE7_DEPLOYED PASS`. ARM recorded `Succeeded` at `2026-11-21T09:58:04.656146Z`. The ARM timestamp and the start inferred from its reported duration fall within the 09:00–11:00 UTC window. |
| Stage 8 teardown | The receipt confirms the owner-reported verification time, `2026-11-21T10:02:56Z`, 5h 57m 04s before the 16:00 UTC cleanup deadline. The owner reported `STAGE8_TEARDOWN_VERIFIED PASS`. |
| Network Watcher | Owner reported `NetworkWatcherRG` present (`true`) and untouched. The `NetworkWatcher_uksouth` instance observation remains to be verified separately. |

## Scope, controls and offline verification

- Stage 7 authorised one incremental deployment bound to the approved what-if and required
  an exact, tagged inventory and pinned teardown targets. The saved what-if passed the
  seven-Create check for one network security group, one virtual network, one managed identity,
  one Key Vault, one diagnostic setting, one Log Analytics workspace and one resource-group
  budget. All seven resource IDs match across the deployment outputs, inventory record,
  pinned targets and approved what-if. The recorded resource-group inventory passed
  the exact-inventory check and the teardown plan regenerated from that state matched.
  [Stage 7 approval](infra-validation-approvals/2026-11-21-stage7-provisioning.md)
- Stage 8 required a single operator and a fresh plan against pinned targets. Unexpected state,
  locks or target drift stop teardown. The procedure verifies group and resource absence,
  including soft-deleted items and scoped role assignments, and checks that the subscription
  budget is retained. Network Watcher is observed and left untouched.
  [Stage 8 approval](infra-validation-approvals/2026-11-21-stage8-teardown-and-cost-checks.md)
- The Stage 6 evidence matched the approved SHA-256 digests below. The committed contract,
  approval-record and procedure bindings, and all eight upload files passed offline integrity
  checks. Both repository Bicep parameters remain restricted to `false`.

| Stage 6 input | Verified SHA-256 |
| --- | --- |
| `validate.json` | `ac6081455df736e966f870a142bd62fbbe7c609017e53cb4e01301166638e7bc` |
| `whatif.json` | `2e329d3001625274eb407a64ee61ec8f6af2764b9960405bd7ed057e0f5abf30` |

## Private receipt digests

These SHA-256 digests were computed from the local receipt bytes. The owner verified
the original Cloud Shell output and supplied its four Stage 7 SHA-256 values. The
comparison against those owner-supplied values passed for all four files. The Stage 8
receipt contains the verified UTC timestamp. Its supporting `ev8-*` artifacts were
unavailable for review.

| Receipt | Local SHA-256 |
| --- | --- |
| `deployment.json` | `8a844c64412a366f4a911225245a3a42a7b6efcf37e188a50d4f55099740f9de` |
| `state.json` | `befb985d11f2e5b3c69f33994aa8c6ec9dbe7d47f75ff2839b0b26e5087ef50d` |
| `plan.json` | `0c9a7c94f61b2e4ff9b3ca1bfa0dc9c4b52367b841c3a66b07f1efeb4c933de1` |
| `targets.json` | `db8f31e6efa91733e5f75bf38a0e016476292a8296e931aa0447d59fd313ef65` |
| `teardown-receipt.json` | `ea435ece228247362103a37059f32dba4360c8a3d2a30288dc503306ec9421e5` |

## Stage 9 closure checklist — pending owner decision

- [x] Compare the four Stage 7 receipt digests with the original Cloud Shell values supplied
  by the owner. All four matched.
- [ ] Reconcile the Stage 8 `ev8-*` evidence with the teardown receipt. Confirm absence
  checks, subscription budget retention, and Network Watcher group and instance observations.
  Compare with any contemporaneous digests. Keep originals private and review masked copies
  before sharing.
- [ ] **+24 h, due 2026-11-22 10:02:56 UTC.** Retain the masked result from the approved read-only
  cost procedure. Confirm scoped absence and the retained subscription budget's reported spend
  in GBP below £2. Pending.
- [ ] **+72 h, due 2026-11-24 10:02:56 UTC.** Repeat the approved read-only check and retain the
  masked result. Record any residue, cost threshold breach or missing evidence for owner review.
  Pending.
- [ ] Assemble the verified timeline, hashes, masked evidence, cost results and any exceptions
  for the separate Stage 9 owner decision. M23 application deployment remains blocked.
