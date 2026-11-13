// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
param name string
param location string
param tags object

param tenantId string
resource identities 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = [
  for service in ['api-ui', 'mcp']: if (deploymentEnabled) {
    name: '${name}-${service}'
    location: location
    tags: tags
  }
]
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = if (deploymentEnabled) {
  name: take(replace('${name}kv', '-', ''), 24)
  location: location
  tags: tags
  properties: {
    tenantId: tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    accessPolicies: []
  }
}
// No Entra apps, federated credentials, role assignments, secrets or grants are created.
output status string = 'DISABLED_NO_AUTHORITY_OR_RBAC_ASSIGNED'
