using '../main.bicep'

// No environment is authorised by Stage A. Test/prod are reference separation only.
param deploymentEnabled = false
param environment = 'test'
param location = 'uksouth'
param owner = 'UNASSIGNED'
param expiresAt = 'UNAPPROVED'
