// Log Analytics workspace — the Azure Monitor analogue of Prometheus/Grafana.
param namePrefix string
param location string

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: '${namePrefix}-logs'
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

output workspaceId string = workspace.id
output workspaceCustomerId string = workspace.properties.customerId
@secure()
output workspacePrimaryKey string = workspace.listKeys().primarySharedKey
