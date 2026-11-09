using './reference.bicep'

// Safe reference only; no deployment or prerequisite approval is granted.
param deploymentEnabled = false
param prerequisitesVerified = false
param environment = 'dev'
param candidateRegion = 'uksouth'
param candidateTier = 'StandardV2'
