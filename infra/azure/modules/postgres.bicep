// Azure Database for PostgreSQL Flexible Server — the managed system of record.
// Stays put: clients never touch it directly; APIM + DAB front it (zero-move).
param namePrefix string
param location string
param adminUser string
@secure()
param adminPassword string

@description('Compute tier SKU.')
param skuName string = 'Standard_D2ds_v5'

resource pg 'Microsoft.DBforPostgreSQL/flexibleServers@2024-08-01' = {
  name: '${namePrefix}-pg'
  location: location
  sku: {
    name: skuName
    tier: 'GeneralPurpose'
  }
  properties: {
    version: '16'
    administratorLogin: adminUser
    administratorLoginPassword: adminPassword
    storage: {
      storageSizeGB: 32
    }
    highAvailability: {
      mode: 'Disabled'
    }
    // Lock down public access in a real deployment; reach via private endpoint / VNet.
    network: {
      publicNetworkAccess: 'Disabled'
    }
  }
}

resource db 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2024-08-01' = {
  parent: pg
  name: 'procurement'
}

output fqdn string = pg.properties.fullyQualifiedDomainName
output name string = pg.name
output id string = pg.id
