# Infrastructure validation execution record — subscription budget creation (stage 4)

**Recorded:** 2026-11-20 · **Reported by:** repository-owner · **Baseline:** `5093fd1`

This record documents the owner-performed creation of the single subscription-scope budget
authorised by the [scope amendment](2026-11-20-scope-amendment-subscription-budget.md) and created
with the values of the [stage 4 budget approval](2026-11-20-budget.md) (SHA-256
`55641a5f8886e940c4a768f093b24fce9527f7e3bc56b0a35a6e82dd7bd5d410`, unchanged). The owner
separately approved the creation. It's an execution record, not an approval: no entry in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json) changes.
The contract stays `PREPARATION_ONLY` with `provisioning_allowed=false`. The record is immutable;
corrections need a new dated supplement.

## Result

| Item | Owner-reported Cloud Shell result |
| --- | --- |
| Budget | `infraval-uks-tmp01-budget` (`Microsoft.Consumption/budgets`, API `2021-10-01`) |
| Scope | Subscription `OctoCAT-Agentic-AI` |
| Creation (single REST PUT) completed | 2026-11-20T02:18:10Z |
| GET verification passed | 2026-11-20T02:18:13Z |
| Amount and grain | 2 GBP, Monthly |
| Period | 2026-11-01 to 2026-12-31 |
| Filter | `ResourceGroupName` `In` `["rg-claims-infraval-uks-tmp01"]` |
| Notifications | `actual50`, `actual80`, `actual100`; `Actual`; `GreaterThanOrEqualTo` |
| Checks | `BODY CHECK PASS` (before the PUT), `GET CHECK PASS` (after it) |
| Current spend | 0.00 GBP |

**Billing currency: GBP**, established from `currentSpend.unit` in the verification GET. That
resolves the "not yet determined" currency in the budget approval. The approved amount of 2 is
therefore 2 GBP; it applies to this budget and the template's resource-group budget. The cost
estimates in the [scope and cost-exposure record](2026-11-20-scope-and-cost-exposure.md) are
expressed in USD, from the Azure Retail Prices API. That record is unchanged and no currency
conversion is recorded here.

## Evidence hashes (SHA-256, from the run's `hashes.txt`)

| Evidence | SHA-256 | Offline cross-check |
| --- | --- | --- |
| Embedded checker `budget_check.py` | `7d575ade5803c9790d82826ce92c60f83fdc2238fe8e896b815a462a6e1e0c7b` | Equals the checker embedded in procedure v3 |
| Request body `budget-body.json` | `c7983afcda375232c79783da4d9f78bf4fdcadc2c06315018726012c0c2d8654` | Equals the hash of v3's fixed request body |
| PUT response | `031af662d2a35661bdb4bca17832cea45ffd60ae8fbdec35196cd396c8c645e5` | Owner-held; not reproducible offline |
| GET response | `dab02f6e5ea085a61e40658819c0cb8e304ec13e5d360525c7fab31cfeaa8aea` | Owner-held; not reproducible offline |

The raw responses contain the subscription ID and stay with the owner; they aren't committed.
The procedure v3 script is SHA-256
`e82a9f7882eead6e24604c07d8e6e1f6e73debaf48a1fe46803c3cb583c260ab`; the owner didn't report a
hash for the uploaded script file, so the binding is through the checker and request hashes
above.

## Earlier attempts (both stopped before any write)

| Run | Procedure | Stopped | Effect |
| --- | --- | --- | --- |
| 1 | v1 (script `44e0cc61…`, checker `8892fd70…`) | 2026-11-20T01:54:23Z, `ABSENCE NOT_CONFIRMED` | No PUT; nothing created |
| 2 | v2 (script `07b1c58c…`, checker `add4ceab…`) | 2026-11-20T02:02:16Z, `ABSENCE NOT_CONFIRMED` | No PUT; nothing created |

Between runs, the owner confirmed by a separate read-only GET that the budget returned 404.

**Diagnosed cause (parser defect, not an Azure fault).** A read-only diagnostic (script SHA-256
`edbe8a9b919fe7ee2ba7aece6ca6c9d3ea3a55acc4cf643da738908da842db4e`) printed only methods, hosts,
the redacted budget path, HTTP statuses and the CLI version. It showed that Azure CLI 2.91.0
writes request lines as `DEBUG: urllib3.connectionpool: https://management.azure.com:443 "GET
<budget path> HTTP/1.1" 404`, alongside unrelated authentication requests.

- v1 required exactly one `GET` request line in the whole transcript; the authentication
  requests made that count exceed one.
- v2 ignored other hosts but anchored the line format to a single leading token, so the
  `DEBUG: ` prefix stopped every line from matching.

v3 changed only the absence check. It accepts that observed prefix and ignores requests to other
hosts. It still requires exactly one request to `https://management.azure.com:443`: a `GET` of
the exact budget path with `api-version=2021-10-01`, answered 404. It fails closed on any
management request line it can't parse. It passed 112 offline checker tests and 10 offline
end-to-end scenarios (at most one PUT, never a DELETE) before the owner ran it.

## Retention and what stays unapproved

- **Retention:** per the scope amendment, the budget stays for the +24 h and +72 h post-teardown
  monitoring, or until its approved expiry (end date 2026-12-31, when Azure deletes it
  automatically). **Deleting it earlier needs a separate owner approval.**
- **Not approved:** further Azure writes; `execution_template`, `cloud_validation`,
  `provisioning`, `teardown` and `evidence`. No resource group or in-group resource was created.
  Both Bicep deployment gates stay `@allowed([false])`. M22 restrictions, M23 SECURITY GATE NO-GO,
  M24's six NOT_TESTED demonstrations and M25 OFFLINE COMPLETE are unchanged.
