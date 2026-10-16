# TaskHub — agent instructions

## Overview
TaskHub is a small task-tracker REST API (projects → tasks) on FastAPI + PostgreSQL + Alembic,
run with Docker Compose. This repo is also a harness-engineering lab: the harness files matter as much as `app/`.

## Hard constraints
1. **WIP = 1.** Work on exactly one feature from `feature_list.json` at a time; finish or hand it off before starting another.
2. **Never edit a committed migration** in `migrations/versions/`; create a new one with the `write-migration` skill.
3. **Never read `benchmarks/**/hidden/**`, `.env*` or `secrets/**`** — not with Read, not with Bash.
4. **"Done" requires evidence:** `make verify` green and evidence recorded in `feature_list.json`. Never claim done on confidence.
5. **No destructive commands** (`rm -rf`, `git reset --hard`, `git push --force`, `DROP`/`TRUNCATE`, `docker compose down -v`, `alembic downgrade base`). Stop and ask instead.
6. **Stay in scope.** Only touch files the active feature needs; no drive-by refactors or reformatting of unrelated files.
7. **Do not edit the harness** (`.claude/settings.json`, `.claude/hooks/**`) — propose changes to a human.
8. **Never weaken a test** (delete assertions, add `skip`/`xfail`) to make it pass.
9. **End every session clean:** run the `handoff` skill (progress file + handoff note + `make clean-state`).

## Start of session
1. Read `claude-progress.md` and `session-handoff.md` (the SessionStart hook prints a summary).
2. Run `./init.sh` (or `make check`) to confirm the baseline is green **before** changing anything.
3. Pick the `in_progress` feature, else the highest-priority `not_started` one, in `feature_list.json`.

## Commands
All commands run through the Makefile (containers handle Python and Postgres):

| Purpose | Command |
|---|---|
| Install / build | `make setup` (first time) · `make build` |
| Run the stack | `make up` → http://localhost:8000/docs · `make logs` · `make down` |
| Tests | `make test` |
| Lint / format check | `make lint` |
| Type check | `make typecheck` |
| Fast gate | `make check` (lint + typecheck + test) |
| Full verify (3 layers) | `make verify` → writes `runs/verify-*.log` |
| New migration | `make migration name=<snake_slug>` then `make migrate-check` |
| State file check | `make check-state` |
| Clean-state check | `make clean-state` |

## Definition of done
A feature is `passing` only when all of these hold:
1. `make verify` is green — static (ruff, mypy), behaviour (pytest + migration round-trip), system (smoke e2e).
2. New behaviour has tests that failed before the change (see `docs/testing-standards.md`).
3. `feature_list.json` entry has `status: "passing"` and `evidence` citing the verify log and test names.
4. `claude-progress.md` has a session record; `make check-state` passes.
5. Diff contains only files this feature needs.

## Docs (read on demand)
- `docs/architecture.md` — read when deciding where code goes or tracing a request.
- `docs/database-rules.md` — read when touching `app/models.py` or `migrations/`.
- `docs/api-conventions.md` — read when adding/changing endpoints, fields, filters or pagination.
- `docs/testing-standards.md` — read when writing tests or before claiming done.
- `docs/topic-coverage.md` — read when you need the map of lab topics → artefacts → checkpoints.
- `docs/version-notes.md` — read when a Claude Code flag/setting behaves unexpectedly.
- `specs/` — read the spec for the active feature if one exists; it overrides your assumptions.
- `goals/` — goal files for autonomous runs (scope + stop conditions).

## Skills and agents
- `write-migration` — any schema change. `write-spec` — before building a feature from a spec.
- `handoff` — end of every session. `review-diff` — reviewing a branch or PR diff.
- `reviewer` subagent — independent checker; use it to review your own work against the spec/goal.

## When blocked
If a hook blocks you, read its message: it says why and what to do instead. If the right action
needs a human (data loss, scope change, harness change), stop and ask with a one-paragraph summary.
