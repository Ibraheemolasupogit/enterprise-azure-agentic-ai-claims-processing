# Stage 7 provisioning approval for infraval-20261121-01

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

The owner authorises **one synchronous incremental deployment submission** via the exact
`deployment/infra_stage7_deploy.sh` (SHA-256 `9db00d75a01554cf0042b6653897b0629b68614cdbbb92f5acc673e18e81ec4a`),
named `infraval-20261121-01-deploy`, only in the **09:00–11:00 UTC** window on November 21.
The separate Stage 8 approval and reviewed recovery arrangements are prerequisites.
Before submitting, verify owner availability through cleanup, sufficient time to finish
by 16:00, a successful subscription preflight and the exact empty, unlocked G9 group
with no prior deployments. Use one owner-controlled session and exclude other writers.

The validated scope is one NSG, one virtual network and its subnet, one user-assigned
identity, one Key Vault, its diagnostic setting, one Log Analytics workspace and one
resource-group budget. Use only the bound template, parameters and passing raw what-if.
The optional Container Apps environment stays off. Keep the existing log cap and budget
limits. Record the exact resulting inventory, deployment hash and pinned teardown targets.
Record Network Watcher group and instance presence or absence at this checkpoint under
the recorded read-only evidence scope. Existing M23 application-deployment restrictions apply.

Stop on any disagreement, refused check, authorization error, unexpected cloud state
or missed time boundary. A failed or uncertain deployment is never resubmitted. Stop
and review the expected deployment record and the separate Stage 8 recovery authority.
If no deployment was submitted and the group qualifies, the existing amended G9
empty-group cleanup is the abort path. This record grants provisioning scope only.
