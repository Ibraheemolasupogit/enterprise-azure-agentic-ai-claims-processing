// M23 Stage A cannot deploy: false is the ONLY permitted parameter value.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
@allowed(['dev', 'test', 'prod'])
param environment string = 'dev'
@allowed(['uksouth', 'westeurope'])
param location string = 'uksouth'
param owner string = 'UNASSIGNED'
param expiresAt string = 'UNAPPROVED'
param tenantId string = '00000000-0000-0000-0000-000000000000'
param clientApplicationId string = '00000000-0000-0000-0000-000000000000'
param apiUiImage string = 'unconfigured.invalid/claims@sha256:0000000000000000000000000000000000000000000000000000000000000000'
param mcpImage string = 'unconfigured.invalid/claims@sha256:0000000000000000000000000000000000000000000000000000000000000000'
param publisherEmail string = 'unassigned@example.invalid'
param publisherName string = 'UNASSIGNED'

var name = 'nsclaims-${environment}-${uniqueString(subscription().id, resourceGroup().id, environment)}'
var tags = {
  environment: environment
  owner: owner
  expiresAt: expiresAt
  milestone: 'M23-Stage-A'
  dataClass: 'synthetic-only'
  deploymentStatus: 'DISABLED'
}
var vnetId = resourceId('Microsoft.Network/virtualNetworks', '${name}-vnet')
var registryName = 'acrxx${take(replace(name, '-', ''), 45)}'
var vaultName = take(replace('${name}kv', '-', ''), 24)
var storageName = 'stg${take(replace(name, '-', ''), 21)}'

module network 'modules/network.bicep' = if (deploymentEnabled) {
  name: '${name}-network'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
  }
}

module identity 'modules/identity.bicep' = if (deploymentEnabled) {
  name: '${name}-identity'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
    tenantId: tenantId
  }
}

module registry 'modules/registry.bicep' = if (deploymentEnabled) {
  name: '${name}-registry'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
  }
}

module data 'modules/data.bicep' = if (deploymentEnabled) {
  name: '${name}-data'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
    tenantId: tenantId
    diagnosticWorkspaceId: resourceId('Microsoft.OperationalInsights/workspaces', '${name}-logs')
  }
  dependsOn: [monitoring]
}

module monitoring 'modules/monitoring.bicep' = if (deploymentEnabled) {
  name: '${name}-monitoring'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
  }
}

module compute 'modules/compute.bicep' = if (deploymentEnabled) {
  name: '${name}-compute'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
    subnetId: '${vnetId}/subnets/containers'
    registryHost: '${registryName}.azurecr.io'
    apiUiImage: apiUiImage
    mcpImage: mcpImage
    apiUiIdentityId: resourceId('Microsoft.ManagedIdentity/userAssignedIdentities', '${name}-api-ui')
    mcpIdentityId: resourceId('Microsoft.ManagedIdentity/userAssignedIdentities', '${name}-mcp')
  }
  dependsOn: [network, identity, registry]
}

module gateway 'modules/gateway.bicep' = if (deploymentEnabled) {
  name: '${name}-gateway'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
    subnetId: '${vnetId}/subnets/gateway'
    backendHost: 'unconfigured.invalid'
    tenantId: tenantId
    clientApplicationId: clientApplicationId
    publisherEmail: publisherEmail
    publisherName: publisherName
  }
  dependsOn: [network, identity, registry]
}

module endpoints 'modules/private-endpoints.bicep' = if (deploymentEnabled) {
  name: '${name}-endpoints'
  params: {
    deploymentEnabled: false
    name: name
    location: location
    tags: tags
    subnetId: '${vnetId}/subnets/endpoints'
    vnetId: vnetId
    targets: [
      {
        suffix: 'blob'
        id: resourceId('Microsoft.Storage/storageAccounts', storageName)
        groupId: 'blob'
        zone: 'privatelink.blob.${az.environment().suffixes.storage}'
      }
      {
        suffix: 'vault'
        id: resourceId('Microsoft.KeyVault/vaults', vaultName)
        groupId: 'vault'
        zone: 'privatelink.vaultcore.azure.net'
      }
      {
        suffix: 'acr'
        id: resourceId('Microsoft.ContainerRegistry/registries', registryName)
        groupId: 'registry'
        zone: 'privatelink.azurecr.io'
      }
      {
        suffix: 'bus'
        id: resourceId('Microsoft.ServiceBus/namespaces', '${name}-bus')
        groupId: 'namespace'
        zone: 'privatelink.servicebus.windows.net'
      }
      {
        suffix: 'pg'
        id: resourceId('Microsoft.DBforPostgreSQL/flexibleServers', '${name}-pg')
        groupId: 'postgresqlServer'
        zone: 'privatelink.postgres.database.azure.com'
      }
      {
        suffix: 'apim'
        id: resourceId('Microsoft.ApiManagement/service', '${name}-apim')
        groupId: 'Gateway'
        zone: 'privatelink.azure-api.net'
      }
    ]
  }
  dependsOn: [network, identity, registry, data, gateway]
}
output status string = 'OFFLINE_STAGE_A_NOT_DEPLOYABLE'
output selectedEnvironment string = environment
output liveModelsEnabled bool = false
output cloudExportEnabled bool = false
output missingCapabilities array = [
  'cloud_host'
  'entra'
  'canonical_sessions'
  'postgres'
  'blob'
  'service_bus'
  'cloud_telemetry'
  'private_dns_validation'
  'approvals'
]
