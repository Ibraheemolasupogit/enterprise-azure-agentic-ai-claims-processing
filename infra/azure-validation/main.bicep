// Infrastructure-only Azure validation (Option C). PREPARATION ONLY: false is the ONLY
// permitted gate value. No application, container image, claims data, AI service, public IP or
// public ingress is defined. Separate from, and does not change, the M23 infra/azure gate.
targetScope = 'resourceGroup'

@description('Hard gate. Enabling it requires a recorded owner approval and an edit to this allow-list.')
@allowed([false])
param provisioningApproved bool = false

@description('Owner-approved region. No default: an approved value must be supplied.')
@allowed(['uksouth', 'westeurope'])
param location string

@description('Accountable owner recorded in tags. No default.')
@minLength(3)
param owner string

@description('Approved expiry (UTC, ISO 8601). Resources must be deleted by this time. No default.')
@minLength(20)
param expiresAt string

@description('Owner-approved budget ceiling for the resource group (billing currency). No default.')
@minValue(1)
param budgetAmount int

@description('Approved budget notification recipients. No default.')
@minLength(1)
param budgetContactEmails array

@description('Budget start date (first day of a month, YYYY-MM-01). No default.')
param budgetStartDate string

@description('Budget end date, no later than the approved expiry. No default.')
param budgetEndDate string

@description('Approved Log Analytics daily ingestion cap in GB. No default.')
@minValue(1)
@maxValue(5)
param logDailyQuotaGb int

@description('Optional empty Container Apps environment. Needs an approved platform-egress review.')
param includeContainerEnvironment bool = false

var name = 'nsval-${uniqueString(subscription().id, resourceGroup().id)}'
var tags = {
  purpose: 'infrastructure-validation'
  application: 'none'
  dataClass: 'none'
  owner: owner
  expiresAt: expiresAt
  managedBy: 'bicep-infra-validation'
  deploymentStatus: 'PREPARATION_ONLY'
}

resource nsg 'Microsoft.Network/networkSecurityGroups@2024-05-01' = if (provisioningApproved) {
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

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = if (provisioningApproved) {
  name: '${name}-vnet'
  location: location
  tags: tags
  properties: {
    addressSpace: { addressPrefixes: ['10.71.0.0/16'] }
    subnets: [
      {
        name: 'containers'
        properties: {
          addressPrefix: '10.71.0.0/23'
          networkSecurityGroup: { id: nsg.id }
          delegations: [{ name: 'containers', properties: { serviceName: 'Microsoft.App/environments' } }]
        }
      }
    ]
  }
}

// Workload identity pattern only: no role assignments, federated credentials or secrets.
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = if (provisioningApproved) {
  name: '${name}-id'
  location: location
  tags: tags
}

// RBAC-only vault with no secrets and no public network access. Purge protection is omitted
// (not enabled) with the minimum 7-day soft-delete retention so teardown can complete.
resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = if (provisioningApproved) {
  name: take(replace('${name}kv', '-', ''), 24)
  location: location
  tags: tags
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 7
    publicNetworkAccess: 'Disabled'
    networkAcls: { bypass: 'None', defaultAction: 'Deny' }
    accessPolicies: []
  }
}

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = if (provisioningApproved) {
  name: '${name}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: logDailyQuotaGb }
    features: { disableLocalAuth: true }
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}

resource vaultDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (provisioningApproved) {
  name: 'vault-audit'
  scope: vault
  properties: {
    workspaceId: workspace.id
    logs: [{ categoryGroup: 'audit', enabled: true }]
  }
}

// Empty, internal-only environment: no container apps, images or ingress are defined.
resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = if (provisioningApproved && includeContainerEnvironment) {
  name: '${name}-cae'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: { infrastructureSubnetId: vnet.properties.subnets[0].id, internal: true }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: { destination: 'none' }
    publicNetworkAccess: 'Disabled'
  }
}

// Budgets notify; they do not stop spending. Operator stop and expiry teardown remain mandatory.
resource budget 'Microsoft.Consumption/budgets@2021-10-01' = if (provisioningApproved) {
  name: '${name}-budget'
  properties: {
    category: 'Cost'
    amount: budgetAmount
    timeGrain: 'Monthly'
    timePeriod: { startDate: budgetStartDate, endDate: budgetEndDate }
    notifications: {
      actual50: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 50, thresholdType: 'Actual', contactEmails: budgetContactEmails }
      actual80: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 80, thresholdType: 'Actual', contactEmails: budgetContactEmails }
      actual100: { enabled: true, operator: 'GreaterThanOrEqualTo', threshold: 100, thresholdType: 'Actual', contactEmails: budgetContactEmails }
    }
  }
}

output status string = 'PREPARATION_ONLY_PROVISIONING_DISABLED'
