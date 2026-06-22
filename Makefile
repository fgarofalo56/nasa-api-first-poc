# nasa-api-first-poc — developer targets
# Most targets are scaffolding: the build (see PRP.md) implements the services these
# call. Targets are defined up front so the demo flow
# and CI are stable as the implementation lands.

COMPOSE ?= docker compose
PY ?= python

.DEFAULT_GOAL := help
.PHONY: help up down seed demo test lint diagram pricing logs clean obs ui

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

up: ## Start the core stack (postgres, dab, identity, kong, catalog, mcp)
	$(COMPOSE) --profile core up -d
	./scripts/wait-for-healthy.sh

down: ## Stop and remove the stack
	$(COMPOSE) down -v

seed: ## Generate + load the synthetic Artemis data into Postgres
	$(COMPOSE) run --rm seeder

demo: up seed ## Full end-to-end demo: up -> seed -> query through the gateway -> print the answer
	./scripts/demo.sh

obs: ## Start Prometheus + Grafana (per-consumer metrics dashboard at :3000)
	$(COMPOSE) --profile observability up -d
	@echo "Grafana:    http://localhost:$${GRAFANA_PORT:-3000}  (anonymous viewer enabled)"
	@echo "Prometheus: http://localhost:$${PROMETHEUS_PORT:-9090}"

ui: ## Start the catalog UI (browser SPA at :5173)
	$(COMPOSE) --profile frontend up -d --build
	@echo "Catalog UI: http://localhost:$${FRONTEND_PORT:-5173}"

test: ## Run the test suite (zero-move / auth / discovery / supply-risk / no-fabric)
	$(PY) -m pytest -q

lint: ## Ruff format-check + lint
	ruff format --check .
	ruff check .

diagram: ## Rebuild docs/architecture.excalidraw (export the PNG from Excalidraw)
	$(PY) scripts/gen-architecture-diagram.py

pricing: ## Print live, dated Azure infrastructure prices (Azure Retail Prices API)
	$(PY) tools/azure_pricing.py

logs: ## Tail all service logs
	$(COMPOSE) logs -f

clean: ## Remove generated runtime artifacts
	rm -rf data/out output
