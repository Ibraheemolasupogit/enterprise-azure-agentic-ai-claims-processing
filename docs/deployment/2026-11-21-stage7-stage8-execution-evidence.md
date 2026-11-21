# Stage 7 and 8 execution evidence — 2026-11-21

Run `infraval-20261121-01`, group `rg-claims-infraval-uks-tmp01`, region `uksouth`,
repository baseline `7b04b1c`. The private Stage 7 and 8 receipts are consistent with
the owner-reported deployment and teardown outcomes. All four Stage 7 receipt digests
matched the original Cloud Shell SHA-256 values supplied by the owner.

| Event | Outcome |
| --- | --- |
| Stage 7 deployment `infraval-20261121-01-deploy` | Owner reported `STAGE7_DEPLOYED PASS`. ARM recorded `Succeeded` at `2026-11-21T09:58:04.656146Z`. The ARM timestamp and the start inferred from its reported duration fall within the 09:00–11:00 UTC window. |
| Stage 8 teardown | The receipt confirms the owner-reported verification time, `2026-11-21T10:02:56Z`, 5h 57m 04s before the 16:00 UTC cleanup deadline. The owner reported `STAGE8_TEARDOWN_VERIFIED PASS`. |
| Network Watcher | The original teardown archive records `NetworkWatcherRG` present (`true`). Its observation file has a UTC modification time of `2026-11-21T10:02:56Z`, matching the receipt. The approved script only observes the group, and the owner reported it was left untouched. The original procedure did not capture `NetworkWatcher_uksouth` instance status. |

## Scope, controls and offline verification

- Stage 7 authorised one incremental deployment bound to the approved what-if and required
  an exact, tagged inventory and pinned teardown targets. The saved what-if passed the
  seven-Create check for one network security group, one virtual network, one managed identity,
  one Key Vault, one diagnostic setting, one Log Analytics workspace and one resource-group
  budget. All seven resource IDs match across the deployment outputs, inventory record,
  pinned targets and approved what-if. The recorded resource-group inventory passed
  the exact-inventory check and the teardown plan regenerated from that state matched.
  [Stage 7 approval](infra-validation-approvals/2026-11-21-stage7-provisioning.md)
- Stage 8 required a single operator and a fresh plan against pinned targets. The archived
  pre-teardown deployment matches the Stage 7 receipt byte-for-byte. The captured state
  reproduced the approved teardown plan and showed the expected inventory and resource-group
  budget, zero locks and an empty scoped role-assignment list.
  The teardown receipt is written only after the approved procedure confirms the validation
  group is absent, the bound vault and workspace are absent from soft-delete listings, no
  recorded IDs or validation-tagged resources remain, there are no scoped role assignments,
  and the subscription budget is retained. These post-teardown checks are supported by that
  receipt and the owner-reported PASS. The script did not persist the individual query results.
  [Stage 8 approval](infra-validation-approvals/2026-11-21-stage8-teardown-and-cost-checks.md)
- The Stage 6 evidence matched the approved SHA-256 digests below. The committed contract,
  approval-record and procedure bindings, and all eight upload files passed offline integrity
  checks. Both repository Bicep parameters remain restricted to `false`.

| Stage 6 input | Verified SHA-256 |
| --- | --- |
| `validate.json` | `ac6081455df736e966f870a142bd62fbbe7c609017e53cb4e01301166638e7bc` |
| `whatif.json` | `2e329d3001625274eb407a64ee61ec8f6af2764b9960405bd7ed057e0f5abf30` |

## Private receipt digests

These SHA-256 digests were computed from the local evidence bytes. All four Stage 7
receipt digests match the original Cloud Shell values verified and supplied by the
owner. The original Stage 8 archive matched the owner-supplied digest and was inspected
without extracting files. It contains the pre-teardown capture, the `WITHIN_EXPIRY`
start marker and the final Network Watcher group observation. The separately retained
teardown receipt establishes the completion time.

| Receipt | Local SHA-256 |
| --- | --- |
| `deployment.json` | `8a844c64412a366f4a911225245a3a42a7b6efcf37e188a50d4f55099740f9de` |
| `state.json` | `befb985d11f2e5b3c69f33994aa8c6ec9dbe7d47f75ff2839b0b26e5087ef50d` |
| `plan.json` | `0c9a7c94f61b2e4ff9b3ca1bfa0dc9c4b52367b841c3a66b07f1efeb4c933de1` |
| `targets.json` | `db8f31e6efa91733e5f75bf38a0e016476292a8296e931aa0447d59fd313ef65` |
| `teardown-receipt.json` | `ea435ece228247362103a37059f32dba4360c8a3d2a30288dc503306ec9421e5` |
| `stage8-evidence-private-20261121.tar.gz` | `7182f3cff02c1b32d857c2803e18826c7a5eeb2af7cc9fa6da832ad61f18debb` |

## Stage 9 closure checklist — pending owner decision

- [x] Compare the four Stage 7 receipt digests with the original Cloud Shell values supplied
  by the owner. All four matched.
- [x] Reconcile the original Stage 8 archive with the teardown receipt and record which
  checks are supported by the receipt. Keep originals private and review masked copies
  before sharing.
- [ ] Record the missing execution-time `NetworkWatcher_uksouth` instance observation as
  an evidence gap for the owner decision. Date any later observation separately.
- [ ] **+24 h, due 2026-11-22 10:02:56 UTC.** Retain the masked result from the approved read-only
  cost procedure. Confirm scoped absence and the retained subscription budget's reported spend
  in GBP below £2. Pending.
- [ ] **+72 h, due 2026-11-24 10:02:56 UTC.** Repeat the approved read-only check and retain the
  masked result. Record any residue, cost threshold breach or missing evidence for owner review.
  Pending.
- [ ] Assemble the verified timeline, hashes, masked evidence, cost results and any exceptions
  for the separate Stage 9 owner decision. M23 application deployment remains blocked.
