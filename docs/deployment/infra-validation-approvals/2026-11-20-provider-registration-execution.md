# Infrastructure validation execution record — Microsoft.Network registration

**Recorded:** 2026-11-20T00:39:42Z · **Recorded for:** repository-owner · **Baseline:** `41fd2b9`

This is the **execution evidence** for the registration authorised by the separate
[provider-registration approval record](2026-11-20-provider-registration.md). That authorisation
record and its SHA-256 in the contract are unchanged. This record is immutable: corrections or
additions need a new dated record.

## Owner-reported Cloud Shell results (2026-11-20)

Raw command output isn't retained in the repository, so these are **owner-reported** results.

| Evidence item (from the authorisation record) | Reported result | Status |
| --- | --- | --- |
| Subscription `OctoCAT-Agentic-AI` | Enabled | Reported |
| 1. Before: `Microsoft.Network` registration state | `NotRegistered` | Reported; **UTC timestamp not provided** |
| 2. `az provider register --namespace Microsoft.Network --wait` | Completed successfully | Reported (exit status reported as success) |
| 3. After: `Microsoft.Network` registration state | `Registered` | Reported; **UTC timestamp not provided** |
| 4. Live UK South quota (`az network list-usages --location uksouth`) | `VirtualNetworks` **0 used / 1,000 limit**; `NetworkSecurityGroups` **0 used / 5,000 limit** | Reported |
| 5. No resource group or resource created; `NetworkWatcherRG` still absent | — | **NOT REPORTED** |

No stop condition was reported. Item 5 is still needed to close this execution record. It can be
supplied as a new dated record with the results of `az group list --query "length(@)" -o tsv`
(expected `1`) and `az group exists -n NetworkWatcherRG` (expected `false`).

## Effect on the contract

None. The `provider_registration` approval record isn't changed by this execution evidence. The
contract stays `PREPARATION_ONLY` with `provisioning_allowed=false`; no Azure deployment is
authorised.
