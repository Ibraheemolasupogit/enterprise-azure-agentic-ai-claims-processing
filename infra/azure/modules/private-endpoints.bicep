// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
param name string
param location string
param tags object

param subnetId string
param vnetId string
param targets array
resource zones 'Microsoft.Network/privateDnsZones@2024-06-01' = [
  for target in targets: if (deploymentEnabled) {
    name: target.zone
    location: 'global'
    tags: tags
  }
]
resource links 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [
  for (target, i) in targets: if (deploymentEnabled) {
    parent: zones[i]
    name: '${name}-link'
    location: 'global'
    properties: { registrationEnabled: false, virtualNetwork: { id: vnetId } }
  }
]
resource endpoints 'Microsoft.Network/privateEndpoints@2024-05-01' = [
  for target in targets: if (deploymentEnabled) {
    name: '${name}-${target.suffix}-pe'
    location: location
    tags: tags
    properties: {
      subnet: { id: subnetId }
      privateLinkServiceConnections: [
        { name: target.suffix, properties: { privateLinkServiceId: target.id, groupIds: [target.groupId] } }
      ]
    }
  }
]
resource groups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = [
  for (target, i) in targets: if (deploymentEnabled) {
    parent: endpoints[i]
    name: 'default'
    properties: { privateDnsZoneConfigs: [{ name: target.suffix, properties: { privateDnsZoneId: zones[i].id } }] }
  }
]
// Internal Container Apps wildcard/A-record DNS and Monitor private link require live
// assigned endpoints and explicit reviewed configuration, never guessed addresses.
output status string = 'DISABLED_DNS_AND_REACHABILITY_NOT_PROBED'
