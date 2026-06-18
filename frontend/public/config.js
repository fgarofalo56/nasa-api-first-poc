// Runtime config for the SPA (browser-side URLs to the gateway / issuer / catalog).
// Override by mounting a different config.js into the container's web root, or edit
// before `npm run build`. Defaults match the docker-compose published ports.
window.APP_CONFIG = {
  kong: "http://localhost:8000",
  identity: "http://localhost:8081",
  catalog: "http://localhost:8080",
};
