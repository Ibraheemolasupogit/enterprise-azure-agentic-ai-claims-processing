// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
param name string
param location string
param tags object

param subnetId string
param backendHost string
param tenantId string
param clientApplicationId string
param publisherEmail string
param publisherName string
resource gateway 'Microsoft.ApiManagement/service@2024-05-01' = if (deploymentEnabled) {
  name: '${name}-apim'
  location: location
  tags: tags
  sku: { name: 'StandardV2', capacity: 1 }
  identity: { type: 'SystemAssigned' }
  properties: {
    publisherEmail: publisherEmail
    publisherName: publisherName
    publicNetworkAccess: 'Disabled'
    virtualNetworkType: 'External'
    virtualNetworkConfiguration: { subnetResourceId: subnetId }
  }
}
module m14 '../../apim/reference.bicep' = if (deploymentEnabled) {
  name: '${name}-m14-reference'
  params: {
    deploymentEnabled: false
    prerequisitesVerified: false
    serviceName: '${name}-apim'
    environment: tags.environment
    candidateRegion: location
    candidateTier: 'StandardV2'
    backendHost: backendHost
    clientTenantId: tenantId
    clientApplicationId: clientApplicationId
  }
  dependsOn: [gateway]
}
// APIM private endpoint sequencing, inherited policies, OIDC/delegated human flow and
// separate backend app permission remain UNVERIFIED. The M14 app-only policy is not UI SSO.
output status string = 'DISABLED_M14_POLICY_RUNTIME_NOT_VALIDATED'
