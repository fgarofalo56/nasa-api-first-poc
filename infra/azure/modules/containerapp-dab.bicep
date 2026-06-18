// Data API Builder on Azure Container Apps — the managed analogue of the local DAB
// container. Internal ingress only (reachable by APIM, not by clients) preserves
// zero-move; the connection string is a secret.
param namePrefix string
param location string
param image string
param logAnalyticsCustomerId string
@secure()
param logAnalyticsSharedKey string
@secure()
param dabConnectionString string

resource env 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: '${namePrefix}-cae'
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalyticsCustomerId
        sharedKey: logAnalyticsSharedKey
      }
    }
  }
}

resource dab 'Microsoft.App/containerApps@2024-03-01' = {
  name: '${namePrefix}-dab'
  location: location
  properties: {
    managedEnvironmentId: env.id
    configuration: {
      // Internal ingress: only APIM (in the same environment / VNet) can reach DAB.
      ingress: {
        external: false
        targetPort: 5000
        transport: 'http'
      }
      secrets: [
        {
          name: 'dab-connection-string'
          value: dabConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'dab'
          image: image
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'DAB_CONNECTION_STRING'
              secretRef: 'dab-connection-string'
            }
            {
              name: 'ASPNETCORE_URLS'
              value: 'http://0.0.0.0:5000'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

output fqdn string = 'https://${dab.properties.configuration.ingress.fqdn}'
