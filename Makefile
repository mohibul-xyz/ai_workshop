# TaskHub Harness Lab — every command the agent and humans need. `make help` lists them.
SHELL := /bin/bash
.DEFAULT_GOAL := help

export HOST_UID := $(shell id -u)
export HOST_GID := $(shell id -g)
COMPOSE ?= docker compose
# Inside the sandboxed agent container (IN_CONTAINER=1) tools run directly, not via docker.
ifeq ($(IN_CONTAINER),1)
TOOLS   :=
else
TOOLS   := $(COMPOSE) --profile tools run --rm -T tools
endif
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

up: ## Start db, apply migrations, start api (http://localhost:8000/docs)
	$(COMPOSE) up -d --wait db
	$(COMPOSE) run --rm -T migrate
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

migrate-check: ## Static migration rules + upgrade→downgrade→upgrade round-trip (throwaway DB)
	$(PY) scripts/check_migrations.py --static
	$(TOOLS) python scripts/check_migrations.py --roundtrip

# ---------------------------------------------------------------- harness / state
.PHONY: check-state hooks-test lab-claude-md lab-permissions
check-state: ## Validate feature_list.json (schema, WIP=1, evidence)
	@$(PY) scripts/check_state.py

hooks-test: ## Unit-test every hook with fake tool calls
	@set -o pipefail; $(PY) -m unittest discover -s .claude/hooks/tests_hooks 2>&1 | tail -n 3

FILE ?= CLAUDE.md
lab-claude-md: ## Topic 2: lint CLAUDE.md as a router (+ AGENTS.md mirror)
	$(PY) scripts/lint_claude_md.py $(FILE) $(if $(filter CLAUDE.md,$(FILE)),--mirror AGENTS.md)

SETTINGS ?= .claude/settings.json
lab-permissions: ## Topic 5: permission simulator must score 25/25
	$(PY) stages/02-permissions-hooks-skills/permission_sim.py --settings $(SETTINGS)

verify: ## Topic 7/9 gate — 3-layer definition of done; EVIDENCE=F04 copies log to evidence/
	@bash scripts/verify.sh

lab-spec: ## Topic 7: every spec acceptance criterion has a test_ac<N>_<slug>
	@$(PY) scripts/check_spec_coverage.py

lab-diffs: ## Topic 9: seeded PRs apply, scanner finds every seeded defect, no false HIGHs
	@$(PY) stages/05-verification-specs-diffs/check_prs.py

clean-state: ## End-of-session gate: state, progress, debug leftovers, stray files, check, startup
	@$(PY) scripts/clean_state_check.py $(if $(FAST),--fast)

audit-report: ## Summarise .claude/audit.log (tools used, blocked commands, files touched)
	@$(PY) scripts/audit_report.py

lab-loop-dry: ## Topic 8: maker-checker loop replayed from fixtures; all stop conditions fire
	@bash stages/07-autonomous-loops/check_loop.sh

goal-loop: ## Topic 8 (costs money): run the F06 goal loop for real — GOAL=… BUDGET_USD=… RUNNER=docker|local
	@bash scripts/run_goal_loop.sh

STAGE0 := stages/00-baseline-reading-ai-code
stage0-check: ## Topic 1: bug-proving tests vs ai_written/ (SOLUTION=1: vs solutions/) + findings sheet
	@set -eo pipefail; target=$(if $(SOLUTION),solutions,ai_written); \
	sheet=$(if $(SOLUTION),facilitator/answers/stage0-findings.md,$(STAGE0)/findings-sheet.md); \
	echo "== tests_stage0 against $$target/"; \
	$(TOOLS) env STAGE0_TARGET=$$target pytest -p no:cacheprovider -o addopts="" -q $(STAGE0)/tests_stage0 | tail -n 3; \
	$(PY) scripts/check_findings.py $$sheet

lab-context: ## Topic 10: variants in sync, startup-token report, dry-run A/B/C table (E2E=1: real pipeline, fake agent)
	@bash stages/08-context-optimization/check_context.sh

benchmark: ## Topic 10 (costs money): VARIANT=bloated|router|hygiene or ABLATE=instructions|verification|state, RUNS=3
	@bash scripts/run_benchmark.sh $(if $(ABLATE),--ablate $(ABLATE),$(or $(VARIANT),router))

LAB_CHECKS := lab-claude-md lab-permissions hooks-test migrate-check check-state verify lab-spec \
              lab-diffs lab-loop-dry stage0-check-solution lab-context clean-state
.PHONY: lab-all stage0-check-solution $(LAB_CHECKS)
stage0-check-solution:
	@$(MAKE) -s stage0-check SOLUTION=1

lab-all: ## Run every topic checkpoint (docs/topic-coverage.md) in order and summarise
	@set -o pipefail; failed=""; \
	for t in $(LAB_CHECKS); do \
	  printf '\n\033[1m### make %s\033[0m\n' "$$t"; \
	  if $(MAKE) -s $$t 2>&1 | grep -vE '^ ?(Container|Network|Volume) '; then :; else failed="$$failed $$t"; fi; \
	done; \
	echo; if [ -z "$$failed" ]; then echo "lab-all: all $(words $(LAB_CHECKS)) checkpoints green"; \
	else echo "lab-all: FAILED:$$failed"; exit 1; fi
