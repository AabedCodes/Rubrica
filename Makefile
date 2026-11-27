# Rubrica make targets (01-interfaces.md §1). Needs only Docker and make for `up`.
COMPOSE := docker compose -f deploy/docker-compose.yml
UV      := uv run --project backend --frozen

.PHONY: help secrets up down logs ps seed test lint verify verify-live test-db-up test-db-down sbom scan pins frontend-lint frontend-test

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

frontend-test: ## Vitest for frontend/ (needs `npm ci` in frontend/)
ifneq ($(FRONTEND_READY),)
	cd frontend && npm test -s
else
	@echo "frontend-test: skipped (run 'npm ci' in frontend/ first)"
endif

pins: ## Check that actions, images and lockfiles are pinned
	python3 scripts/check_pins.py . || python scripts/check_pins.py .

# Throwaway PostgreSQL for RLS and verification tests (B1, B4). Same pinned
# image as deploy/docker-compose.yml; trust auth, loopback only, no volume.
TESTDB_PORT  ?= 55432
TESTDB_IMAGE := pgvector/pgvector@sha256:508c5290cda481d4f5f846446a26e9c1b804766828a394a5861de1b348a18b4c
VERIFY_OUT   := build/verification
RUNS         ?= 10

test-db-up: ## Start a disposable test database on 127.0.0.1:$(TESTDB_PORT)
	-@docker rm -f rubrica-testdb >/dev/null 2>&1
	docker run -d --rm --name rubrica-testdb -p 127.0.0.1:$(TESTDB_PORT):5432 \
	  -e POSTGRES_HOST_AUTH_METHOD=trust -e POSTGRES_USER=rubrica_owner -e POSTGRES_DB=rubrica \
	  $(TESTDB_IMAGE) >/dev/null
	@until docker exec rubrica-testdb pg_isready -h 127.0.0.1 -U rubrica_owner -d rubrica >/dev/null 2>&1; do sleep 1; done
	@echo "test database ready: RUBRICA_D1_TEST_PORT=$(TESTDB_PORT)"

test-db-down: ## Remove the disposable test database
	-docker rm -f rubrica-testdb >/dev/null 2>&1

verify: test-db-up ## Verification + RLS suites, then docs/verification/report.md (owner B)
	RUBRICA_D1_TEST_PORT=$(TESTDB_PORT) LLM_PROVIDER=fake $(UV) pytest tests/verification tests/authz \
	  --verification-results=$(VERIFY_OUT)/results.json; status=$$?; \
	  $(MAKE) -s test-db-down; \
	  $(UV) python scripts/verify_report.py $(VERIFY_OUT)/results.json --out docs/verification || status=1; \
	  exit $$status

verify-live: test-db-up ## Probabilistic tests RUNS times on the real provider (costs money)
	@test -n "$$LLM_PROVIDER" -a "$$LLM_PROVIDER" != fake || { echo "set LLM_PROVIDER to the real provider"; $(MAKE) -s test-db-down; exit 1; }
	rm -f $(VERIFY_OUT)/live-*.json; \
	for i in $$(seq 1 $(RUNS)); do \
	  RUBRICA_D1_TEST_PORT=$(TESTDB_PORT) $(UV) pytest tests/verification -m probabilistic -q \
	    --verification-run=$$i --verification-results=$(VERIFY_OUT)/live-$$i.json || true; \
	done; \
	$(MAKE) -s test-db-down; \
	$(UV) python scripts/verify_report.py $(VERIFY_OUT)/live-*.json --out docs/verification/live

sbom: ## Merged CycloneDX SBOM + AI-BOM (task E8)
	@echo "make sbom: not implemented yet (owner: E, task E8)"; exit 1

scan: ## All scanners (task E8)
	@echo "make scan: not implemented yet (owner: E, task E8)"; exit 1
