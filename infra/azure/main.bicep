// Reference IaC for the managed Azure(-Gov) target of the POC. This is documentation-
// grade: it maps the local OSS stack to managed services. CI does NOT deploy this and
// does NOT require an Azure subscription. See docs/AZURE-DEPLOYMENT.md.
//
//   Kong (OSS)        -> Azure API Management (enterprise + AI gateway)
//   local JWT issuer  -> Microsoft Entra ID (referenced; app reg is a separate step)
//   Data API Builder  -> DAB on Azure Container Apps  (or Dataverse Web API)
//   PostgreSQL        -> Azure Database for PostgreSQL Flexible Server
//   Prometheus/Grafana-> Azure Monitor / Log Analytics
//   classification.yml-> Microsoft Purview (governance; referenced in docs)

targetScope = 'resourceGroup'

@description('Deployment location. For ITAR/strict-CUI use a US Gov region (usgovvirginia/usgovarizona).')
param location string = resourceGroup().location

@description('Short prefix for resource names.')
param namePrefix string = 'artemis'

@description('PostgreSQL administrator login.')
param pgAdminUser string = 'artemis'

@description('PostgreSQL administrator password.')
@secure()
param pgAdminPassword string

@description('Publisher email for API Management.')
param apimPublisherEmail string = 'ocio-data-platform@example.gov'

@description('Container image for Data API Builder.')
param dabImage string = 'mcr.microsoft.com/azure-databases/data-api-builder:latest'

module monitor 'modules/monitor.bicep' = {
  name: 'monitor'
  params: {
    namePrefix: namePrefix
    location: location
  }
}

module postgres 'modules/postgres.bicep' = {
  name: 'postgres'
  params: {
    namePrefix: namePrefix
    location: location
    adminUser: pgAdminUser
    adminPassword: pgAdminPassword
  }
}

module dab 'modules/containerapp-dab.bicep' = {
  name: 'dab'
  params: {
    namePrefix: namePrefix
    location: location
    image: dabImage
    logAnalyticsCustomerId: monitor.outputs.workspaceCustomerId
    logAnalyticsSharedKey: monitor.outputs.workspacePrimaryKey
    // The SoR connection string is supplied as a secret in a real deployment.
    dabConnectionString: 'Host=${postgres.outputs.fqdn};Database=procurement;Username=${pgAdminUser};Password=${pgAdminPassword};SslMode=Require'
  }
}

module apim 'modules/apim.bicep' = {
  name: 'apim'
  params: {
    namePrefix: namePrefix
    location: location
    publisherEmail: apimPublisherEmail
    dabBackendUrl: dab.outputs.fqdn
  }
}

output apimGatewayUrl string = apim.outputs.gatewayUrl
output dabUrl string = dab.outputs.fqdn
output postgresFqdn string = postgres.outputs.fqdn
