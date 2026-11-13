// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
param name string
param location string
param tags object

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = if (deploymentEnabled) {
  name: '${name}-logs'
  location: location
  tags: tags
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
    workspaceCapping: { dailyQuotaGb: 1 }
    features: { disableLocalAuth: true }
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}
resource insights 'Microsoft.Insights/components@2020-02-02' = if (deploymentEnabled) {
  name: '${name}-insights'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id
    DisableLocalAuth: true
    publicNetworkAccessForIngestion: 'Disabled'
    publicNetworkAccessForQuery: 'Disabled'
  }
}
// Azure Monitor Private Link Scope, collection/export adapter, action recipients and alerts
// require separate approved integration. Public ingestion cannot be used as a fallback.
output status string = 'DISABLED_NO_CLOUD_EXPORT_OR_NOTIFICATIONS'
