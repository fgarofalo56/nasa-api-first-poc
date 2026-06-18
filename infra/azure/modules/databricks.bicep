// Reference IaC for the data-platform layer: Azure Databricks (premium, for Unity
// Catalog) + ADLS Gen2 + an access connector. Reference only — CI does not deploy this.
// Posture: the managed platform (managed Unity Catalog + Databricks SQL + Delta Lake +
// Delta Sharing) runs in commercial Azure at FedRAMP High. (Fabric/OneLake are excluded —
// not available in Azure Government / GCC; use Databricks/ADLS/Delta instead.)
param namePrefix string
param location string

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: '${namePrefix}lake${uniqueString(resourceGroup().id)}'
  location: location
  sku: { name: 'Standard_LRS' }
  kind: 'StorageV2'
  properties: {
    isHnsEnabled: true   // ADLS Gen2 (hierarchical namespace) for Delta
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
  }
}

resource workspace 'Microsoft.Databricks/workspaces@2024-05-01' = {
  name: '${namePrefix}-dbx'
  location: location
  sku: { name: 'premium' }   // premium tier is required for Unity Catalog
  properties: {
    managedResourceGroupId: subscriptionResourceId(
      'Microsoft.Resources/resourceGroups', '${namePrefix}-dbx-managed'
    )
  }
}

resource connector 'Microsoft.Databricks/accessConnectors@2024-05-01' = {
  name: '${namePrefix}-dbx-connector'
  location: location
  identity: { type: 'SystemAssigned' }
}

output workspaceUrl string = 'https://${workspace.properties.workspaceUrl}'
output storageAccount string = storage.name
output accessConnectorId string = connector.id
