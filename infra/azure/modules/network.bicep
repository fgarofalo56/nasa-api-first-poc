// Network isolation for TRUE zero-move in Azure — reference IaC (documentation-grade).
//
// In the functional ACA demo every app uses public ingress and the gateway governs each
// call. The production-hardened posture removes the public path to the system of record
// entirely: the Container Apps environment is VNet-injected, and PostgreSQL is reachable
// ONLY over a private endpoint resolved through a private DNS zone. The SoR then has no
// internet-facing surface — the data cannot move because there is nowhere off-VNet to move
// it to, and the ONLY route to it is APIM -> DAB inside the VNet.
//
// CI does NOT deploy this; it requires no subscription. Wire it in by passing the SoR's
// resource id and using the subnet outputs for the Container Apps environment + the PG
// server's `delegatedSubnetResourceId` / private-endpoint association.

@description('Short prefix for resource names.')
param namePrefix string

@description('Deployment location.')
param location string = resourceGroup().location

@description('Resource id of the PostgreSQL Flexible Server to expose via a private endpoint.')
param postgresResourceId string

@description('Address space for the spoke VNet.')
param vnetAddressPrefix string = '10.20.0.0/16'

var caeSubnetPrefix = '10.20.0.0/23' // Container Apps env needs a /23 (or larger) subnet
var peSubnetPrefix = '10.20.2.0/24' // private endpoints
var pgDnsZoneName = 'privatelink.postgres.database.azure.com'

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${namePrefix}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [vnetAddressPrefix]
    }
    subnets: [
      {
        // Dedicated, delegated subnet for the VNet-injected Container Apps environment.
        name: 'snet-cae'
        properties: {
          addressPrefix: caeSubnetPrefix
          delegations: [
            {
              name: 'aca'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        // Subnet that holds the private endpoint NICs (PG, Key Vault, ACR, ...).
        name: 'snet-pe'
        properties: {
          addressPrefix: peSubnetPrefix
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
    ]
  }
}

// Private DNS zone so `*.postgres.database.azure.com` resolves to the private endpoint
// IP from inside the VNet (the Container Apps env / DAB).
resource pgDnsZone 'Microsoft.Network/privateDnsZones@2020-06-01' = {
  name: pgDnsZoneName
  location: 'global'
}

resource pgDnsLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = {
  parent: pgDnsZone
  name: '${namePrefix}-pg-link'
  location: 'global'
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

// Private endpoint for the system-of-record Postgres server — no public path.
resource pgPrivateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${namePrefix}-pg-pe'
  location: location
  properties: {
    subnet: {
      id: '${vnet.id}/subnets/snet-pe'
    }
    privateLinkServiceConnections: [
      {
        name: 'pg'
        properties: {
          privateLinkServiceId: postgresResourceId
          groupIds: ['postgresqlServer']
        }
      }
    ]
  }
}

resource pgPeDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: pgPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'pg'
        properties: {
          privateDnsZoneId: pgDnsZone.id
        }
      }
    ]
  }
}

@description('Subnet id for the VNet-injected Container Apps environment.')
output caeSubnetId string = '${vnet.id}/subnets/snet-cae'

@description('Subnet id that hosts the private endpoints.')
output peSubnetId string = '${vnet.id}/subnets/snet-pe'

output vnetId string = vnet.id
