// REFERENCE ONLY. No APIM service, identity, network, logger or backend is provisioned here.
targetScope = 'resourceGroup'

@description('Explicit future deployment switch. Compilation is not deployment authorization.')
param deploymentEnabled bool = false
@description('Future operator assertion: private networking, identity, residency and budget reviewed.')
param prerequisitesVerified bool = false
@allowed(['dev', 'test', 'prod'])
param environment string = 'dev'
param serviceName string = 'apim-not-configured'
@allowed(['uksouth', 'westeurope'])
param candidateRegion string = 'uksouth'
@allowed(['Developer', 'StandardV2', 'PremiumV2'])
param candidateTier string = 'StandardV2'
@description('Future privately reachable TLS backend hostname. Reserved invalid domain by default.')
param backendHost string = 'claims-backend.invalid'
param clientTenantId string = '00000000-0000-0000-0000-000000000000'
param clientApplicationId string = '00000000-0000-0000-0000-000000000000'
param clientAudience string = 'api://northstar-client-gateway.invalid'
param backendAudience string = 'api://northstar-backend-service.invalid'
param existingLoggerName string = 'applicationinsights-not-configured'

var enabled = deploymentEnabled && prerequisitesVerified
var apiName = 'northstar-claims-${environment}'
var namedValues = [
  { name: 'client-tenant-id', value: clientTenantId }
  { name: 'client-application-id', value: clientApplicationId }
  { name: 'client-audience', value: clientAudience }
  { name: 'backend-audience', value: backendAudience }
]

resource apim 'Microsoft.ApiManagement/service@2025-09-01-preview' existing = {
  name: serviceName
}
resource settings 'Microsoft.ApiManagement/service/namedValues@2024-05-01' = [for item in namedValues: if (enabled) {
  parent: apim
  name: item.name
  properties: {
    displayName: item.name
    value: item.value
    secret: false // identifiers/audiences only; no credentials or tokens.
  }
}]
resource mcp 'Microsoft.ApiManagement/service/apis@2025-09-01-preview' = if (enabled) {
  parent: apim
  name: apiName
  properties: {
    type: 'mcp'
    displayName: 'Northstar ${environment} governed MCP reference'
    description: 'Candidate ${candidateTier}/${candidateRegion}; actual capacity and network approval required.'
    path: apiName
    protocols: ['https']
    serviceUrl: 'https://${backendHost}'
    subscriptionRequired: true
    mcpProperties: {
      transportType: 'streamable'
      endpoints: [{ name: 'message', uriTemplate: '/mcp' }]
    }
  }
}
resource policy 'Microsoft.ApiManagement/service/apis/policies@2025-09-01-preview' = if (enabled) {
  parent: mcp
  name: 'policy'
  properties: {
    format: 'rawxml'
    value: loadTextContent('mcp-policy.xml')
  }
  dependsOn: [settings]
}
resource diagnostics 'Microsoft.ApiManagement/service/apis/diagnostics@2024-05-01' = if (enabled) {
  parent: mcp
  name: 'applicationinsights'
  properties: {
    loggerId: resourceId('Microsoft.ApiManagement/service/loggers', serviceName, existingLoggerName)
    alwaysLog: 'allErrors'
    logClientIp: false
    sampling: { samplingType: 'fixed', percentage: 5 }
    verbosity: 'error'
    httpCorrelationProtocol: 'W3C'
    frontend: {
      request: { headers: [], body: { bytes: 0 } }
      response: { headers: [], body: { bytes: 0 } }
    }
    backend: {
      request: { headers: [], body: { bytes: 0 } }
      response: { headers: [], body: { bytes: 0 } }
    }
  }
}

output referenceStatus string = enabled ? 'REQUIRES_FUTURE_AUTHORIZED_VALIDATION' : 'DISABLED_REFERENCE_ONLY'
output prerequisites object = {
  candidateRegion: candidateRegion
  candidateTier: candidateTier
  privateGatewayAndBackendRequired: true
  systemAssignedGatewayIdentityRequired: true
  backendEntraVerifierRequired: true
  trustedCaseGrantIssuerRequired: true
  policyRuntimeValidationRequired: true
  budgetApprovalRequired: true
}
