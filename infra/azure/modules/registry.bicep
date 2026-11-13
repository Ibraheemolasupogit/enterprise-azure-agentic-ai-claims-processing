// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
@minLength(5)
param name string
param location string
param tags object

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' = if (deploymentEnabled) {
  name: 'acrxx${take(replace(name, '-', ''), 45)}'
  location: location
  tags: tags
  sku: { name: 'Premium' } // Candidate required for private link; price unapproved.
  properties: {
    adminUserEnabled: false
    anonymousPullEnabled: false
    publicNetworkAccess: 'Disabled'
    networkRuleBypassOptions: 'None'
    networkRuleSet: { defaultAction: 'Deny' }
    dataEndpointEnabled: true
  }
}
output status string = 'DISABLED_NO_IMAGE_PUBLICATION'
