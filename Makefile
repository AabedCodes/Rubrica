# Rubrica make targets (01-interfaces.md §1). Needs only Docker and make for `up`.
COMPOSE := docker compose --project-directory . -f deploy/docker-compose.yml
UV      := uv run --project backend --frozen

.PHONY: help secrets up down logs ps seed test lint verify verify-live sbom scan pins

help:
	@grep -E '^[a-z-]+:.*?## ' $(MAKEFILE_LIST) | awk -F':.*?## ' '{printf "  %-12s %s\n", $$1, $$2}'

secrets: ## Create random Docker secrets in secrets/ (never overwrites)
	python3 scripts/make_secrets.py || python scripts/make_secrets.py

up: ## Build and start every service, wait for healthchecks
	@test -d secrets || { echo "secrets/ missing: run 'make secrets' first"; exit 1; }
	$(COMPOSE) up --build --detach --wait

down: ## Stop the stack (keeps volumes)
	$(COMPOSE) down

logs: ## Follow logs of all services
	$(COMPOSE) logs -f

ps: ## Show service status
	$(COMPOSE) ps

seed: ## Load synthetic seed data (owner D, task D-seed)
	@echo "make seed: not implemented yet (owner: D)"; exit 1

test: ## Unit, authz and deterministic verification tests
	LLM_PROVIDER=fake $(UV) pytest tests

lint: ## Ruff over Python code
	$(UV) ruff check backend scripts tests
	$(UV) ruff format --check backend scripts tests

pins: ## Check that actions, images and lockfiles are pinned
	python3 scripts/check_pins.py . || python scripts/check_pins.py .

verify: ## Verification suite + evidence report (owner B)
	@echo "make verify: framework not merged yet (owner: B)"; exit 1

verify-live: ## Probabilistic tests against the real provider (costs money)
	@echo "make verify-live: not implemented yet (owners: B, C)"; exit 1

sbom: ## Merged CycloneDX SBOM + AI-BOM (task E8)
	@echo "make sbom: not implemented yet (owner: E, task E8)"; exit 1

scan: ## All scanners (task E8)
	@echo "make scan: not implemented yet (owner: E, task E8)"; exit 1
