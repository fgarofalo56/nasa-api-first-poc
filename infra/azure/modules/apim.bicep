// Azure API Management — the managed analogue of Kong. The same governance pattern
// (validate JWT, rate-limit, emit metrics) maps to APIM policies; APIM's AI-gateway
// policies (llm-token-limit / llm-emit-token-metric) extend the metering story to LLMs.
param namePrefix string
param location string
param publisherEmail string
param dabBackendUrl string

@description('Entra tenant id (used by the validate-azure-ad-token policy).')
param tenantId string = subscription().tenantId

resource apim 'Microsoft.ApiManagement/service@2023-05-01-preview' = {
  name: '${namePrefix}-apim'
  location: location
  sku: {
    // Developer for a POC; Standard/Premium (or v2 tiers) for production.
    name: 'Developer'
    capacity: 1
  }
  properties: {
    publisherName: 'NASA OCIO Data Platform (synthetic POC)'
    publisherEmail: publisherEmail
  }
}

resource api 'Microsoft.ApiManagement/service/apis@2023-05-01-preview' = {
  parent: apim
  name: 'artemis-procurement'
  properties: {
    displayName: 'Artemis Supply-Chain Risk API'
    path: 'api'
    protocols: ['https']
    serviceUrl: dabBackendUrl
    subscriptionRequired: false
  }
}

// Policy parity with the Kong config: validate Entra JWT, then rate-limit per caller.
// (Bicep multi-line strings are verbatim, so the tenant id is injected via replace().)
var policyXml = '''
<policies>
  <inbound>
    <base />
    <validate-azure-ad-token tenant-id="__TENANT_ID__">
      <audiences>
        <audience>api://artemis-api</audience>
      </audiences>
    </validate-azure-ad-token>
    <rate-limit-by-key calls="60" renewal-period="60" counter-key="@(context.Subscription?.Id ?? context.Request.IpAddress)" />
    <set-header name="X-Correlation-ID" exists-action="skip">
      <value>@(context.RequestId.ToString())</value>
    </set-header>
  </inbound>
  <backend><base /></backend>
  <outbound><base /></outbound>
  <on-error><base /></on-error>
</policies>
'''

resource policy 'Microsoft.ApiManagement/service/apis/policies@2023-05-01-preview' = {
  parent: api
  name: 'policy'
  properties: {
    format: 'xml'
    value: replace(policyXml, '__TENANT_ID__', tenantId)
  }
}

output gatewayUrl string = apim.properties.gatewayUrl
output apimName string = apim.name
