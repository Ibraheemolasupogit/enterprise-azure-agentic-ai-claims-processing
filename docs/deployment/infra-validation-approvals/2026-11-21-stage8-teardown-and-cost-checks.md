# Stage 8 teardown and cost-check approval for infraval-20261121-01

**Owner** repository-owner. **Recorded UTC** `2026-11-21T08:48:27Z`.

**Baseline** `f35469d42b4da2b3ad4d27a08b8c88e7811a9e32`. **Run** `infraval-20261121-01`. **Group** `rg-claims-infraval-uks-tmp01`. **Region** `uksouth`.
The hard expiry is **2026-11-21 16:00 UTC**. The recorded subscription commitment and
resource scope are unchanged. This decision adopts the Stage 6/G9 amendment
(`773811f3887fc80fa3c8e0a96b91dbfd90d219720fb8ee5f447ea905e8c8a19f`). The owner reported Stage 6 complete before 11:00 UTC with an empty
group. The saved responses report success and the exact seven-Create check passes.
Recheck current subscription and group state at execution.

| Artifact | SHA-256 |
| --- | --- |
| `validate.json` | `ac6081455df736e966f870a142bd62fbbe7c609017e53cb4e01301166638e7bc` |
| `whatif.json` | `2e329d3001625274eb407a64ee61ec8f6af2764b9960405bd7ed057e0f5abf30` |
| `reviewed.json` | `28c29de5f4d0bc36529a5682246da5324cb9b2db8267583b8227254e55c41a17` |
| `execution.json` | `dfc26600fb9c8748fdf9fead8078bf281f4482ae27ed987c004adf33bb970989` |
| `parameters.json` | `b679e8e0b170b1fa2bc9ed162125ea2c968ebf5e5a7b06c728c11ca937f0a946` |
| `infra_subscription_preflight.py` | `858b102e08fc2634ab74537c4c595fa582b5b641b3b423f22b5799b9daec4287` |
| `infra_validation.py` | `3b971f1f5355efaa0a1824f2fb7d39e83dc336bfc9c0d13a653f387f17b1b2fb` |
| `infra_evidence.py` | `bd5377b3e6f12741013969eef8ec4051233d7b1057f08ad52c481e1db0c653a4` |

Use the committed contract, including the final approval-record evidence hashes, in the
strictly verified eight-file manifest. Each script is checked separately against its
recorded SHA-256. Raw validation, what-if, inventory and target artifacts stay private.

The associated Stage 7 submission window is **09:00–11:00 UTC on November 21, 2026**.
Teardown starts after that authorised submission and can continue toward the separate
16:00 UTC deadline. Receipt-based cost checkpoints follow at +24 h and +72 h.

The owner authorises teardown and read-only cost verification with these exact scripts:

| Procedure | SHA-256 |
| --- | --- |
| `infra_stage8_teardown.sh` | `c83c173f8707a6614c8cd8f4e3eb41ef082730ec0d60f51f1e9a0f3ff4e689ff` |
| `infra_stage8_cost_check.sh` | `8492630a9e6c3cb9d7a14d6924298cf68b9e4937efd7ffdd670aabbc2ea69cf0` |

Use one owner operator and one Cloud Shell session in the Stage 7 directory at a time.
The working state and teardown targets are shared files. Keep other sessions and writers
out of the target group. Following the separately approved Stage 7 submission, begin
cleanup promptly once the decision is made. Verify absence by **16:00 UTC**. If Stage 7
fails after a submission, act only on verified deployment state and the approved run.

The script checks the bound subscription, group and run, rejects other deployments and
unrecognized states, refuses locks, unexpected resources and mismatched targets, and
plans against a fresh inventory. It may cancel only the exact bound deployment if it is
Running or Accepted, then stops for owner review and re-planning. No deletion follows a
cancellation until a later invocation verifies terminal state. Resume only after owner
review with pinned targets preserved. A missing or uncertain deployment record, changed
targets, unsafe inventory or failed check requires a stop and separate recovery decision.
When the group is absent, verify using the pinned targets before any remaining vault purge.
Do not use the teardown script as an alternative to G9 empty-group cleanup before submission.

The permitted order is the run's resource-group budget, permanent removal of the bound
workspace, removal of the bound group, then purge of the bound vault only after checking
its original resource ID. Verify no residue, including soft-deleted resources and scoped
role assignments. Preserve the subscription budget and Network Watcher. Record Network
Watcher group and instance presence or absence again and retain masked evidence, verified
UTC receipt and expiry result. If the deadline is missed, stop for owner review and record
the breach. Later absence cannot count as timely cleanup.

At +24 h and +72 h or later from the verified teardown receipt, run the exact cost-check
script read-only with the corresponding CHECKPOINT_HOURS. Require scoped absence and
the retained subscription budget in GBP with spend below 2 GBP. Record masked receipts,
spend, threshold and any failures. The +72 h result addresses the approved threshold.
Stage 9 remains a separate decision. M23 application deployment remains blocked.
