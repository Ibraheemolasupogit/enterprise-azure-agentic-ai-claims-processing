// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
param name string
param location string
param tags object

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = if (deploymentEnabled) {
  name: '${name}-nsg'
  location: location
  tags: tags
  properties: {
    securityRules: [
      {
        name: 'DenyInboundInternet'
        properties: {
          priority: 100
          direction: 'Inbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: 'Internet'
          destinationAddressPrefix: '*'
        }
      }
      {
        name: 'AllowEntraTLS'
        properties: {
          priority: 100
          direction: 'Outbound'
          access: 'Allow'
          protocol: 'Tcp'
          sourcePortRange: '*'
          destinationPortRange: '443'
          sourceAddressPrefix: 'VirtualNetwork'
          destinationAddressPrefix: 'AzureActiveDirectory'
        }
      }
      {
        name: 'DenyInternetEgress'
        properties: {
          priority: 4096
          direction: 'Outbound'
          access: 'Deny'
          protocol: '*'
          sourcePortRange: '*'
          destinationPortRange: '*'
          sourceAddressPrefix: '*'
          destinationAddressPrefix: 'Internet'
        }
      }
    ]
  }
}
resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = if (deploymentEnabled) {
  name: '${name}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.70.0.0/16'] }
    subnets: [
      {
        name: 'containers'
        properties: {
          addressPrefix: '10.70.0.0/23'
          networkSecurityGroup: { id: nsg.id }
          delegations: [{ name: 'containers', properties: { serviceName: 'Microsoft.App/environments' } }]
        }
      }
      {
        name: 'gateway'
        properties: {
          addressPrefix: '10.70.2.0/27'
          networkSecurityGroup: { id: nsg.id }
          delegations: [{ name: 'gateway', properties: { serviceName: 'Microsoft.Web/serverFarms' } }]
        }
      }
      {
        name: 'endpoints'
        properties: {
          addressPrefix: '10.70.3.0/24'
          networkSecurityGroup: { id: nsg.id }
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}
// Azure platform DNS/registry/monitor required egress still needs a reviewed live allowlist.
output status string = 'DISABLED_STAGE_A_NETWORK_CANDIDATE'
