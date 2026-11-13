# M23 Stage A — disabled Azure definitions

These are offline resource definitions, not a deployable application or an approval. `main.bicep` and every new module accept **only `deploymentEnabled=false`** through `@allowed([false])`. Every resource/module is conditional, and nested modules explicitly receive false. Dev/test/prod parameter files remain false; no environment is provisioned. Supporting Stage B requires a separately reviewed code change, not a flag flip or an approval string.

Modules cover network/NSG, identities/Key Vault, registry, data, monitoring, compute, gateway and private endpoints/DNS. Names/tags include the selected environment; test/prod are reference separation only. No identity, credential, secret, role assignment, model resource, public backend or cloud export is activated. The existing M14 APIM artifacts remain unchanged and disabled inside the new gateway candidate.

Compile with an already trusted **local** Bicep compiler; never use an Azure CLI wrapper, restore a registry module, run ARM validation or run what-if under Stage A:

```sh
mkdir -p outputs/deployment/new-m23-compile
/path/to/bicep build infra/azure/main.bicep --no-restore --outfile outputs/deployment/new-m23-compile/main.json
/path/to/bicep build-params infra/azure/environments/dev.bicepparam --no-restore --outfile outputs/deployment/new-m23-compile/dev.json
.venv/bin/python -I -B deployment/foundation.py --root .
.venv/bin/python -I -B deployment/foundation.py --compiled outputs/deployment/new-m23-compile/main.json
```

Use new output paths to preserve historical evidence. Local compilation proves schema/type compatibility with that compiler only. It does not prove Azure provider acceptance, current subscription quota, SKU/region availability, private DNS, policy expression execution, Entra authentication or price.

The Container Apps environment is internal and public network access is disabled. App `external=true` allows the gateway to reach an app from the connected VNet; it does not make the internal environment public. Only one replica per app is permitted. Default entrypoints exit 78 and are never ready: cloud hosts/authentication/persistence adapters are **not implemented**. The health probes define a future hosting contract, not successful hosting evidence.

Network definitions intentionally deny internet ingress/egress except the explicit Entra service-tag TLS rule. Required platform/registry/DNS/monitor egress and internal Container Apps DNS still need reviewed live integration; do not add permissive internet rules to make smoke tests pass. APIM private-endpoint/public-access sequencing and Standard v2 integration need separate validation. Monitor public ingestion/query are disabled; a Monitor private-link scope, DNS and collector/export adapter remain missing. No unsafe public fallback is provided.

See [scope/architecture](../../docs/architecture/offline-azure-deployment-foundation.md), [compatibility/cost matrices](../../docs/deployment/m23/README.md), [adapter requirements](../../docs/deployment/m23/adapter-requirements.md) and [operational gates](../../docs/deployment/m23/lifecycle-and-approvals.md). There are no Azure execution commands or deployment scripts in this foundation.
