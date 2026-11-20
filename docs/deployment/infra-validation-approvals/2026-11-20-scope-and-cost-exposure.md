# Infrastructure validation approval record — scope and cost exposure

**Recorded:** 2026-11-20T00:08:07Z · **Approver:** repository-owner · **Baseline:** `ffbb375`

This record is the evidence for two approvals in
[`infra/azure-validation/contract.json`](../../../infra/azure-validation/contract.json):
`scope` (checklist stage 1, partial) and `cost_exposure` (stage 2). It's an immutable record:
any change to the approved scope needs a new dated record and fresh approvals. The contract stays
`PREPARATION_ONLY` with `provisioning_allowed=false`, and **no Azure action is authorised by this
record**.

## Approval 1 — `scope`

The owner approves the scope of a temporary, infrastructure-only Azure validation:

- **Exactly seven resources:** network security group, virtual network, user-assigned managed
  identity, Key Vault, Log Analytics workspace, Key Vault diagnostic setting, and a
  resource-group budget (template `infra/azure-validation/main.bicep`).
- **Optional Container Apps environment disabled** (`includeContainerEnvironment=false`).
- **Subscription:** `OctoCAT-Agentic-AI`.
- **Region:** `uksouth`.
- **Dedicated temporary resource group:** `rg-claims-infraval-uks-tmp01`. The existing
  `rg-claims-agentic-ai-dev` stays untouched.
- **Maximum execution window:** 2 hours.
- **Excluded:** any claims application, container image, claims data, AI service, public IP,
  public ingress or role assignment. M23 application deployment remains blocked.

The subscription and region above are scope decisions. **They don't satisfy `region_capacity`**,
which still needs evidence of SKU support and quota. Stage 1's `region_capacity`,
`identity_rbac` and `network` approvals remain `PENDING`.

## Approval 2 — `cost_exposure`

The owner acknowledges the cost exposure assessed on 2026-11-19 from the Azure Retail Prices
API (UK South, USD) and Microsoft Learn documentation:

- **Realistic cost:** approximately $0 for a 2-hour validation. All seven resources are free or
  usage-based, and nothing generates meaningful log volume.
- **Worst case (2 hours):** up to about $2.88 of Log Analytics ingestion (1 GB at $2.88/GB) if
  the price list's 0–5 GB free tier isn't available to this subscription, which is UNKNOWN,
  plus an unquantified overshoot, because the daily cap isn't a hard spending limit.
- **72-hour fallback worst case:** up to about $11.52 plus overshoot, which could exceed the
  USD 10 billing-account budget.
- **$2 resource-group budget alerts are notifications, not hard caps.** Budgets are evaluated
  every 24 hours on cost data that can take up to 72 hours for pay-as-you-go subscriptions, and
  Microsoft states that consumption isn't stopped. They can't protect a 2-hour window.
  Protection relies on the 2-hour window, the 1 GB daily cap and the fail-closed teardown.
- **Container Apps environment:** would add $0.10/hour (meter effective 2026-11-01). It's
  disabled by this scope.

## Not approved by this record

`region_capacity`, `identity_rbac`, `network`, `provider_registration`, `budget`,
`execution_template`, `cloud_validation`, `provisioning`, `teardown` and `evidence` remain
`PENDING`. All contract `approved_values` and `execution` fields remain `null`. Neither Bicep
deployment gate changes. M22 restrictions, M23 SECURITY GATE NO-GO, M24's six NOT_TESTED
demonstrations and M25 OFFLINE COMPLETE are unchanged.
