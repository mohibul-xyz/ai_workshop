# TaskHub Harness Lab — every command the agent and humans need. `make help` lists them.
SHELL := /bin/bash
.DEFAULT_GOAL := help

COMPOSE ?= docker compose
TOOLS   := $(COMPOSE) --profile tools run --rm -T tools
PY      ?= python3
VENV    := .venv

.PHONY: help
help: ## List targets
	@grep -hE '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-18s\033[0m %s\n",$$1,$$2}'

# ---------------------------------------------------------------- environment
.PHONY: setup build up down logs
setup: build ## Build images and create the host .venv (ruff/mypy for hooks)
	@test -f .env || cp .env.example .env
	@test -d $(VENV) || $(PY) -m venv $(VENV)
	@$(VENV)/bin/pip install -q "ruff>=0.6"

build: ## Build docker images
	$(COMPOSE) --profile tools build

up: ## Start db + migrate + api (http://localhost:8000/docs)
	$(COMPOSE) up -d --wait api

down: ## Stop the stack (keeps the database volume)
	$(COMPOSE) down

logs: ## Tail api logs
	$(COMPOSE) logs -f api

# ---------------------------------------------------------------- feedback
.PHONY: test lint typecheck check verify
test: ## Run pytest against the taskhub_test database
	$(TOOLS) pytest

lint: ## ruff check + format check
	$(TOOLS) sh -c "ruff check . && ruff format --check ."

typecheck: ## mypy --strict on app/
	$(TOOLS) mypy

check: lint typecheck test ## Fast gate: lint + typecheck + tests

# ---------------------------------------------------------------- database
.PHONY: migrate migration
migrate: ## Apply migrations to the dev database
	$(TOOLS) alembic upgrade head

migration: ## Create the next sequential migration: make migration name=add_due_at
	@test -n "$(name)" || (echo "usage: make migration name=<snake_slug>" && exit 1)
	$(TOOLS) sh -c 'n=$$(ls migrations/versions | grep -cE "^[0-9]{4}_"); \
	  rev=$$(printf "%04d" $$((n+1))); alembic revision --autogenerate --rev-id $$rev -m "$(name)"'
