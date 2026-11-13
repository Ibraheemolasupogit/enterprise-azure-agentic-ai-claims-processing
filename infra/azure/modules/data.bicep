// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
@minLength(5)
param name string
param location string
param tags object

param tenantId string
// Required same-environment destination; no connection string or public fallback.
param diagnosticWorkspaceId string
resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = if (deploymentEnabled) {
  name: 'stg${take(replace(name, '-', ''), 21)}'
  location: location
  tags: tags
  kind: 'StorageV2'
  sku: { name: 'Standard_LRS' }
  properties: {
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
    publicNetworkAccess: 'Disabled'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    allowCrossTenantReplication: false
    defaultToOAuthAuthentication: true
    networkAcls: { bypass: 'None', defaultAction: 'Deny', ipRules: [], virtualNetworkRules: [] }
    encryption: {
      keySource: 'Microsoft.Storage'
      requireInfrastructureEncryption: true
      services: { blob: { enabled: true } }
    }
  }
}
resource blobs 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = if (deploymentEnabled) {
  parent: storage
  name: 'default'
  properties: {
    isVersioningEnabled: true
    deleteRetentionPolicy: { enabled: true, days: 30 }
    containerDeleteRetentionPolicy: { enabled: true, days: 30 }
  }
}
// Definition only: private Monitor routing and log privacy review remain deployment gates.
resource blobDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = if (deploymentEnabled) {
  scope: blobs
  name: 'blob-audit'
  properties: {
    workspaceId: diagnosticWorkspaceId
    logAnalyticsDestinationType: 'Dedicated'
    logs: [
      { category: 'StorageRead', enabled: true }
      { category: 'StorageWrite', enabled: true }
      { category: 'StorageDelete', enabled: true }
    ]
  }
}
resource containers 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = [
  for container in ['quarantine', 'accepted', 'policy', 'audit-export']: if (deploymentEnabled) {
    parent: blobs
    name: container
    properties: { publicAccess: 'None' }
  }
]
resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = if (deploymentEnabled) {
  name: '${name}-pg'
  location: location
  tags: tags
  sku: { name: 'Standard_B1ms', tier: 'Burstable' }
  properties: {
    version: '16'
    createMode: 'Default'
    authConfig: { activeDirectoryAuth: 'Enabled', passwordAuth: 'Disabled', tenantId: tenantId }
    storage: { storageSizeGB: 32 }
    backup: { backupRetentionDays: 7, geoRedundantBackup: 'Disabled' }
    network: { publicNetworkAccess: 'Disabled' }
    highAvailability: { mode: 'Disabled' }
  }
}
resource bus 'Microsoft.ServiceBus/namespaces@2024-01-01' = if (deploymentEnabled) {
  name: '${name}-bus'
  location: location
  tags: tags
  sku: { name: 'Premium', tier: 'Premium', capacity: 1 }
  properties: { disableLocalAuth: true, minimumTlsVersion: '1.2', publicNetworkAccess: 'Disabled' }
}
resource queue 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = if (deploymentEnabled) {
  parent: bus
  name: 'synthetic-work'
  properties: {
    requiresDuplicateDetection: true
    duplicateDetectionHistoryTimeWindow: 'PT10M'
    maxDeliveryCount: 3
    lockDuration: 'PT1M'
    maxSizeInMegabytes: 1024
    deadLetteringOnMessageExpiration: true
  }
}
// No application schema, Entra database administrator, adapter or data-plane role is supplied.
output status string = 'DISABLED_ADAPTERS_NOT_IMPLEMENTED'
