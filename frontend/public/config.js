// Runtime config for the SPA (browser-side URLs to the gateway / issuer / catalog).
// Override by mounting a different config.js into the container's web root, or edit
// before `npm run build`. Defaults match the docker-compose published ports.
window.APP_CONFIG = {
  kong: "http://localhost:8000",
  identity: "http://localhost:8081",
  catalog: "http://localhost:8080",
  registry: "http://localhost:8095",
  agent: "http://localhost:8110",
  // Optional: URL of the published Power BI report (the same governed Gold mart, in BI).
  // Set by the Azure deploy to surface a "Power BI report" link in the UI; "" hides it.
  powerbi: "",
  // Local dev has the registry's shared base config + Kong's admin port, so the live
  // "add/remove a source" wizard works. The Azure deploy sets this false (pre-registered).
  liveOnboarding: true,
  // No Entra EasyAuth locally; the Azure deploy sets this true so the landing page shows
  // the "Sign in with Microsoft" button.
  authEnabled: false,
};
