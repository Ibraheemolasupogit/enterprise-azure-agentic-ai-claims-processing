# Azure infrastructure validation (Option C)

**Status: PREPARATION ONLY — NOT PROVISIONED.** Prepared 2026-11-19 at baseline `43cbf5b` under
the owner's approval to prepare an infrastructure-only validation. No Azure call, validation,
provisioning or spending has occurred, and none is authorised by this document.

This validation deploys **no claims application, container image, claims data, AI service,
public IP or public ingress**. It's separate from the M23 deployment foundation:
`infra/azure/main.bicep` and its false-only `deploymentEnabled` gate are unchanged. **M23 remains
DEFERRED — SECURITY GATE NO-GO**, M22's independent-review restrictions and M24's six
NOT_TESTED demonstrations are unchanged, and nothing here represents application, quality or
production readiness.

## Purpose

Prove, with real evidence, that a minimal landing zone can be validated, provisioned within an
approved budget and lifetime, monitored, and completely torn down. Specifically:

- the template validates and the what-if matches the approved resource list;
- the deployment identity is scoped to one resource group;
- tags, budget alerts and log caps work;
- teardown leaves no resources or charges.

## Artifacts

| File | Purpose |
| --- | --- |
| [`infra/azure-validation/main.bicep`](../../infra/azure-validation/main.bicep) | Minimal template with its own hard `@allowed([false])` provisioning gate |
| [`infra/azure-validation/contract.json`](../../infra/azure-validation/contract.json) | Scope, resource allow-list, approval records (all pending) and approved values (all null) |
| [`deployment/infra_validation.py`](../../deployment/infra_validation.py) | Offline validator: contract shape, scope, resource allow-list, gate, tags, secure settings and the unchanged M23 gate |
| [`tests/test_infra_validation.py`](../../tests/test_infra_validation.py) | Positive checks and fail-closed security mutations |

## Resources (all behind the hard gate)

| Resource | Secure configuration |
| --- | --- |
| Network security group | Deny inbound from the Internet; deny Internet egress; no inbound allow rules |
| Virtual network | One delegated subnet; no public IPs |
| User-assigned managed identity | No role assignments, federated credentials or secrets |
| Key Vault | RBAC only, no access policies, no secrets, public network access disabled, default-deny ACLs; purge protection **not** enabled and 7-day soft-delete so teardown completes |
| Log Analytics workspace | Approved daily cap, 30-day retention, local auth disabled, public ingestion and query disabled |
| Key Vault diagnostic setting | Audit logs to the workspace |
| Container Apps environment (**optional, off by default**) | Internal only, public access disabled, **no container apps or images** |
| Budget | Resource-group scope; notifications at 50/80/100% actual spend |

Excluded: API Management, container registry, PostgreSQL, Service Bus, storage, private
endpoints, container apps, Document Intelligence, AI Search, model services, role assignments.

## Parameters requiring owner approval (no defaults)

`location` (`uksouth` or `westeurope`), `owner`, `expiresAt`, `budgetAmount`,
`budgetContactEmails`, `budgetStartDate`, `budgetEndDate` and `logDailyQuotaGb` (1–5). The
optional `includeContainerEnvironment` defaults to `false`. Enabling it needs an approved
review of the environment's platform egress, because the subnet denies Internet egress. The
contract proposes a **maximum 72-hour lifetime** as an upper bound; it isn't an approved value.

## Offline validation (available now)

```sh
python3 -I -B deployment/infra_validation.py --root .                       # PASS, cloud_calls 0
python3 -I -B deployment/infra_validation.py --root . --check-provisioning  # always refused (exit 78)
.venv/bin/python -m pytest tests/test_infra_validation.py
```

## Approval checklist (each separate, recorded in the contract)

| # | Approval | Evidence required |
| --- | --- | --- |
| 1 | **Scope:** this exact resource list; no workload, data or ingress; quality stays NOT_TESTED | Signed scope record |
| 2 | **Region and capacity:** subscription, region, SKU support and quota | Owner-recorded subscription and region |
| 3 | **Budget:** amount, contacts, start/end dates, stop threshold, expiry (≤72 h proposed), expiry owner | Dated price quote for this resource list in the billing currency |
| 4 | **Identity and RBAC:** owner pre-creates the resource group; deployer gets Contributor on that group only; GitHub OIDC tied to a protected environment and branch, or a named operator; no client secrets | Identity matrix |
| 5 | **Network:** no ingress or public IPs; decision on the optional Container Apps environment and its egress | Reviewed network plan |
| 6 | **Template gate change:** a reviewed edit allowing `true` in this template only (never in `infra/azure/main.bicep`) | Reviewed diff |
| 7 | **Cloud validation:** ARM validate and what-if only | Retained what-if output matching the resource list |
| 8 | **Provisioning** within a bounded time window | Approval naming the what-if hash and window |
| 9 | **Teardown and retention:** deletion plan and retained evidence | Signed teardown plan |

Approval of one step never implies the next. Any change to resources, region, SKU,
permissions, budget or lifetime invalidates the affected approvals.

## Controlled teardown

1. **Trigger:** at the approved expiry, when the budget stop threshold is reached, on any stop
   condition, or when validation completes, whichever comes first.
2. **Export evidence:** the activity log for the resource group, the deployment record and
   the budget notification history, to approved local storage.
3. **Delete the whole resource group.** Don't delete resources individually.
4. **Key Vault:** the vault moves to soft-deleted state for 7 days. The owner either purges it
   (allowed, since purge protection isn't enabled) or records the retained name and its
   expiry. No secrets ever existed in it.
5. **Verify:** no resources remain in the group or carry the validation tag; no remaining
   deployments; cost analysis shows no new charges after deletion, re-checked after billing
   latency (24–48 h).
6. **Revoke:** remove the deployer's role assignment and OIDC federated credential, or the
   operator's access, and the resource group if pre-created.
7. **Record:** teardown receipts and final cost, without changing existing gates or evidence.

## Stop conditions

Stop and tear down, or don't start, if any of these occur:

- the what-if lists anything outside the allow-list, a public IP, ingress or an excluded SKU;
- any approved value is missing, or there's no dated quote (deny when the budget is missing);
- spend reaches the approved stop threshold, or the expiry passes;
- the deployer needs permissions beyond the resource group, or any client secret;
- any step needs a container image, application code, claims data, AI services or a change to
  `infra/azure/main.bicep`;
- resources or charges remain after teardown;
- anything would imply application, quality or production readiness.

## Limitations

- **Local compilation passes; Azure-side checks are NOT_TESTED.** On 2026-11-19 the template
  compiled with **zero diagnostics** using the pinned Bicep CLI **0.48.1 (`cec7951cf6`)**,
  SHA-256 `62cd5958c62fa1b738e9b69f24799fabddb90ed83fdb7d6d2563dde376ce479d`. That's the
  official `bicep-osx-arm64` release asset, whose release digest matches the M23 Stage A pin,
  signed by Apple Team ID `UBF8T346G9` and kept in git-ignored `artifacts/tools/`. As a
  control, all 12 M23 compilations reproduced their recorded outputs byte for byte. The
  compiled ARM template keeps `provisioningApproved` restricted to `false`, with every
  resource conditioned on it. Local compilation checks the compiler's type and schema model
  only; ARM validation and what-if (provider acceptance, quota, policy) remain approval 7.
- **The budget API version (`Microsoft.Consumption/budgets@2021-10-01`) is new to this
  repository.** The other API versions reuse the reviewed M23 modules.
- **Workspace query access is disabled** (no private link scope), so logs can't be queried
  from outside Azure's private network. Enabling query access is a separate approval.
- **Budgets only notify.** Stopping spend relies on the operator and the teardown procedure.
