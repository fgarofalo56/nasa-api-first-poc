using './main.bicep'

param namePrefix = 'artemis'
param pgAdminUser = 'artemis'
// Never commit secrets: supply at deploy time, e.g. PG_ADMIN_PASSWORD env var.
param pgAdminPassword = readEnvironmentVariable('PG_ADMIN_PASSWORD', '')
param apimPublisherEmail = 'ocio-data-platform@example.gov'
