# Infrastructure validation execution record — registration supplement (item 5)

**Recorded:** 2026-11-20T00:45:38Z · **Recorded for:** repository-owner · **Baseline:** `41fd2b9`

This supplements the [registration execution record](2026-11-20-provider-registration-execution.md)
(SHA-256 `f1ffc2b39d2e5c61e4895825f0f0292809f926db242f44d27bc4c0f449b309d2`), which is unchanged.
It records evidence item 5 from the [authorisation record](2026-11-20-provider-registration.md):
confirmation that registering `Microsoft.Network` didn't create a resource group or Network
Watcher.

## Owner-reported read-only observations (Cloud Shell, after registration)

Raw command output isn't retained in the repository, so these are **owner-reported** results.

| Observation | Reported result | Expected |
| --- | --- | --- |
| Resource-group count in `OctoCAT-Agentic-AI` | **1** (unchanged from the pre-registration count of 1) | 1 |
| `NetworkWatcherRG` | **Absent** | Absent |
| `rg-claims-infraval-uks-tmp01` | **Absent** | Absent |

## Scope of these observations

They show that **no new resource group** was created and that the Network Watcher group and the
dedicated validation group **don't exist**. They **don't** amount to a full inventory: resources
inside the one existing resource group weren't listed, and no subscription-wide resource
inventory was taken. Item 5 is therefore closed **at resource-group level only**.

UTC timestamps for the before and after registration states (items 1 and 3) remain **not
provided**.

## Effect on the contract

None. No approval record or evidence hash changes. The `region_capacity` approval and its record
are unchanged. The contract stays `PREPARATION_ONLY` with `provisioning_allowed=false`; no Azure
deployment is authorised.
