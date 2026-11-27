# Rubrica make targets (01-interfaces.md §1). Needs only Docker and make for `up`.
COMPOSE := docker compose -f deploy/docker-compose.yml
UV      := uv run --project backend --frozen

.PHONY: help secrets up down logs ps seed test lint verify verify-live sbom scan pins frontend-lint frontend-test e2e

# Front end (A1). Runs only once `npm ci` has been run in frontend/, so members
# without Node can still use `make lint` and `make test` for the Python side.
FRONTEND_READY := $(wildcard frontend/node_modules/.package-lock.json)

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

CANARIES ?= 0

seed: ## Load synthetic demo data; set CANARIES=1 for security fixtures
	$(COMPOSE) run --rm -T -e CANARIES=$(CANARIES) migrate python -m seed.generate

test: frontend-test ## Unit, authz and deterministic verification tests (+ front end)
	LLM_PROVIDER=fake $(UV) pytest tests

lint: frontend-lint ## Ruff over Python code (+ ESLint and tsc for the front end)
	$(UV) ruff check backend scripts seed tests
	$(UV) ruff format --check backend scripts seed tests

frontend-lint: ## ESLint and type check for frontend/ (needs `npm ci` in frontend/)
ifneq ($(FRONTEND_READY),)
	cd frontend && npm run -s lint && npm run -s typecheck
else
	@echo "frontend-lint: skipped (run 'npm ci' in frontend/ first)"
endif

e2e: ## Browser tests on the mocked front end (Playwright; needs a browser, see frontend/playwright.config.ts)
	cd frontend && npm run -s e2e

frontend-test: ## Vitest for frontend/ (needs `npm ci` in frontend/)
ifneq ($(FRONTEND_READY),)
	cd frontend && npm test -s
else
	@echo "frontend-test: skipped (run 'npm ci' in frontend/ first)"
endif

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
