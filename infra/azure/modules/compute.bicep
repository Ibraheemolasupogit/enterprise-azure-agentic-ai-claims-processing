// M23 STAGE A: offline definition only. This parameter cannot be enabled.
targetScope = 'resourceGroup'
@allowed([false])
param deploymentEnabled bool = false
param name string
param location string
param tags object

param subnetId string
param registryHost string
param apiUiImage string
param mcpImage string
param apiUiIdentityId string
param mcpIdentityId string
@minValue(0)
@maxValue(1)
param maxReplicas int = 1
resource environment 'Microsoft.App/managedEnvironments@2025-07-01' = if (deploymentEnabled) {
  name: '${name}-cae'
  location: location
  tags: tags
  properties: {
    vnetConfiguration: { infrastructureSubnetId: subnetId, internal: true }
    workloadProfiles: [{ name: 'Consumption', workloadProfileType: 'Consumption' }]
    appLogsConfiguration: { destination: 'none' }
    publicNetworkAccess: 'Disabled'
  }
}
var services = [
  { name: 'api-ui', image: apiUiImage, identityId: apiUiIdentityId }
  { name: 'mcp', image: mcpImage, identityId: mcpIdentityId }
]
resource apps 'Microsoft.App/containerApps@2025-01-01' = [
  for service in services: if (deploymentEnabled) {
    name: '${name}-${service.name}'
    location: location
    tags: tags
    identity: { type: 'UserAssigned', userAssignedIdentities: { '${service.identityId}': {} } }
    properties: {
      managedEnvironmentId: environment.id
      workloadProfileName: 'Consumption'
      configuration: {
        activeRevisionsMode: 'Single'
        ingress: { external: true, targetPort: 8080, transport: 'http', allowInsecure: false }
        registries: [{ server: registryHost, identity: service.identityId }]
      }
      template: {
        scale: { minReplicas: 0, maxReplicas: maxReplicas }
        containers: [
          {
            name: service.name
            image: service.image
            command: ['/opt/venv/bin/python', '-I', '-B', '/app/entrypoint.py']
            args: ['--service', service.name]
            env: [
              { name: 'M23_STAGE', value: 'A' }
              { name: 'M23_CLOUD_EXECUTION', value: 'disabled' }
              { name: 'M23_CLOUD_EXPORT', value: 'disabled' }
              { name: 'M23_LIVE_MODELS', value: 'disabled' }
            ]
            resources: { cpu: json('0.5'), memory: '1Gi' }
            probes: [
              {
                type: 'Startup'
                httpGet: { path: '/health/live', port: 8080, scheme: 'HTTP' }
                initialDelaySeconds: 5
                periodSeconds: 10
                timeoutSeconds: 2
                failureThreshold: 3
              }
              {
                type: 'Readiness'
                httpGet: { path: '/health/ready', port: 8080, scheme: 'HTTP' }
                periodSeconds: 10
                timeoutSeconds: 2
                failureThreshold: 3
              }
              {
                type: 'Liveness'
                httpGet: { path: '/health/live', port: 8080, scheme: 'HTTP' }
                periodSeconds: 30
                timeoutSeconds: 2
                failureThreshold: 3
              }
            ]
          }
        ]
      }
    }
  }
]
// external=true means VNet-reachable within the INTERNAL environment, not public ingress.
// Stage A entrypoint refuses hosting. Probes are future contracts, never claimed healthy.
output status string = 'DISABLED_CLOUD_HOSTS_NOT_IMPLEMENTED'
