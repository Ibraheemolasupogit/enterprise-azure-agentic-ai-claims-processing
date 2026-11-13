# M23 approval, migration and operational lifecycle

Stage A is offline only. The versioned [contract](../../../deployment/contract.json) records empty approvals and 14 mandatory gates. No person/owner/tenant/subscription/spending ceiling is invented. Its check-deployment operation always refuses. These gates specify future review requirements; they are not implemented cloud permissions or an authenticated approval service.

## Gates and sequence

| Gate | Required actual evidence before proceeding |
| --- | --- |
| Scope | Owner approves the exact synthetic dev slice, resources/endpoints/data and exclusions; test/prod remain references |
| Region/residency/capacity | Actual tenant/subscription, service/SKU/API support, allocated quota and capacity, network/backup/log geography; no automatic fallback |
| Budget | Dated full fixed/variable cost quote, approved experiment/monthly ceilings, billing currency, maximum lifetime, stop threshold and expiry owner |
| Identity/RBAC | Security-reviewed human/workload/deployer/bootstrap matrix; real Entra registrations/consent and independent case authority design |
| Private network/DNS | Reviewed subnets/routes/egress, private client/runner access, DNS, certificate/hostnames and direct-backend denial plan |
| Linux artifacts | Actual pinned cached base, 39 Linux wheel hashes/licences, source-matching project wheel, image/SBOM/vulnerability and local smoke evidence |
| Cloud adapters | Implemented/tested approved hosts, real identity/session, PostgreSQL/Blob/Service Bus and cloud telemetry adapters; no fabricated completion |
| Migration/restore/rollback | Reviewed schema/runtime compatibility, protected backup/current anchors, restore and rollback tests with explicit failure behaviour |
| Quality scope | Genuine independent release evidence or an explicit narrow infrastructure-test scope decision retaining unavailable quality as NOT_TESTED |
| GitHub protection | Actual environment approvals/branch restrictions/prevent-self-review, exact OIDC subject/issuer/audience and scoped identity; no broad secret-based login |
| Cloud validation | Separate explicit permission for subscription/quota queries, provider registration if needed, ARM validation and what-if; retain reviewed result/diff |
| Provisioning | Owner approves the concrete plan/resource list/cost and a bounded execution window; no approval inferred from successful validation |
| Deployment | Owner approves exact image digests/config/schema, private health/identity/security smoke and rollback/stop plan |
| Teardown | Separate exact resource deletion/retention plan; approve preservation of audit/backup/keys/anchors and verify residual charges/resources |

Any change to resource list, region/SKU, trust boundary, permission, data scope, image/dependency, budget or schema invalidates the affected approval and needs a new reviewed plan. Do not mark a gate approved by editing this preparation record. A future independently authenticated approval implementation and its own security tests are required before any automation consumes approvals.

Actual Azure permission acquisition, federated credential/app/role creation, subscription queries, ARM validation, what-if, provisioning, image push, export, deployment, rollback and deletion all require separate authorisation. None occurs in Stage A, including nominally free/read-only cloud calls.

## Identity and CI administration

Use distinct environment-bound identities for build/push, deployment, privileged RBAC/bootstrap, API/UI, MCP, gateway and future worker/relay. Build may push only to its approved registry when separately authorised; runtime may pull only approved images and access its narrowly scoped data/queue/monitoring resources. No runtime identity receives IAM write, subscription Owner or human review/supervisor/publication authority. Database historical roles never become current assignments.

Human Entra applications, gateway client app, backend audience/permission, OIDC deploy federation and Key Vault custody need real separately approved administrators. The intended OIDC trust pins GitHub issuer, Azure token-exchange audience and exact repository/protected-environment subject. No wildcard branch/fork trust, untrusted pull_request_target, reusable long-lived deployment secret or automatic cloud job is permitted. Runtime managed identity is separate from the GitHub deployment identity. These permissions/subjects are requirements, not configured facts.

Policy editors can exercise gateway identity; restrict/review that publishing role. APIM subscriptions are supplementary, not case authorisation. Enforce canonical current assignment/session/grant checks and separation of source author, publisher and human outcome reviewer even when cloud token verification succeeds.

## Migration and compatibility

No cloud schema/adapter/migration is implemented. Do not mount a historical SQLite store on a container filesystem or Azure Files and call it cloud persistence. Preserve every old database/source/report under its original runtime. No in-place repair, rehash, default grant initialization, stale-anchor adoption or role restoration is authorised.

Before any migration, retain the original immutable source evidence, exact application/dependency/Python/runtime and schema identifiers, approved source/principal context, key versions and independently retained latest audit/revocation anchors. Rehearse on disposable synthetic copies under a reviewed migration version. A candidate must preserve decisions/reasons, source/version binding, receipts, retry history, audit order and current revocation semantics; failed or unknown compatibility blocks opening/acknowledgement.

M12/M20 whole-package fingerprints intentionally reject incompatible runtime state. Stage A edits no application source, but Linux/Python/native dependencies and any future cloud adapter/schema still need compatibility evidence. Code/revision rollback cannot silently reinterpret a closed case or reset consumed retry/revocation history. An old signing key's validity is not proof that an old ledger is current.

## Backup and restore

Approve RPO/RTO, backup schedule/retention, protected custody and restore test criteria before claiming them; no values are measured yet. Back up PostgreSQL state, exact immutable Blob versions, outbox/delivery state and independently protected current authority/anchor/key/source context. Record database/log/Blob retention and deletion interactions, including private networking and identity availability during restore.

An actual authorised restore exercise must recover a fresh isolated environment with matching approved runtime/schema, verify full semantic/source/audit integrity and reconcile acknowledgement/receipt/outbox counts. Reacquire current real identity and canonical assignments; copied tokens/sessions/stored roles cannot regain authority. Compare against independent current revocation/rollback anchors, not only restored data. Test missing keys, corrupt projections, wrong runtime, unavailable Blob versions and stale anchors: remain unready and deny rather than initialize empty state.

## Rollback and incident response

Stop new admissions/traffic and bounded workers when safety/identity/storage compatibility is uncertain. Retain safe correlation/failure counters and required audit; do not log raw payloads/claims/credentials. Switch to a previous Container Apps image/revision only when it can read the current schema/source/authority protocol. Otherwise retain stopped traffic until an approved matching restore or forward fix is verified. Never automatically restore an older revocation ledger to make an old image work.

Re-run authorised positive/negative identity, case-isolation, duplicate/replay, audit/outbox, private ingress and telemetry-leak smoke checks before traffic resumes. Uncertain acknowledgements require authorised state/receipt reconciliation, not blind resubmission. Database/cloud outage, telemetry failure, queue redelivery and current-authority loss remain distinct failure classes. Neither tracing failure nor a model explanation may override mandatory audit or human authority.

## Teardown and cost stop

An operator stop switch first suspends new work/export/model calls and scales supported compute down; fixed APIM/registry/database/queue/private-endpoint/storage/monitoring charges may continue. Before deletion, approve an exact environment/resource list, retained source/audit/backup/keys/anchors and retention/deletion obligations. Never delete shared/prod resources or the only current trust anchor as part of a generic resource-group cleanup.

Retain required evidence under independent approved custody, then perform only the separately approved cleanup. Inventory residual billable resources including disks/storage versions/backups, images, private endpoints/DNS and logs. Key Vault purge protection, backup retention and billing delay can preserve both resources and cost. Reconcile later actual usage/cost records; a successful delete command is not evidence that billing stopped immediately.

Stage A provides plans only, not executed migration, restore, rollback, teardown, human notifications or cost savings. No M24 implementation or production acceptance is included.
