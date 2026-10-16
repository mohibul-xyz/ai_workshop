# Goal: F06 — Pagination on list endpoints

You are running **unattended** in a sandbox on your own branch. Nobody will answer questions.
Read `CLAUDE.md`, then `docs/api-conventions.md` § Pagination, before changing anything.

## Goal
Feature **F06** in `feature_list.json` is `passing`:
- `GET /api/v1/projects` and `GET /api/v1/projects/{id}/tasks` accept `limit` (default 20,
  1–100) and `offset` (default 0, ≥ 0); out-of-range values → `422`.
- Both return the envelope `{"items": [...], "total": N, "limit": L, "offset": O}`.
- `total` counts all rows matching the filters; filters (`status`, `max_priority`, `overdue`,
  `tag`) apply before pagination; order stays `id ASC` and is stable across pages.
- Existing tests are updated **only** where the response shape changed (list → envelope);
  no assertion may be weakened.

## Verification (the judge, not your opinion)
- `make check` must be green before you stop (the Stop hook enforces it).
- The loop then runs `make verify` (3 layers) and an independent `reviewer` subagent.

## Stop when
- `make check` is green, `feature_list.json` F06 has evidence, and you have committed — then
  print `GOAL_DONE` on the last line; **or**
- you need a human decision (ambiguity, a migration, a dependency, anything denied by
  permissions) — then print `NEEDS_HUMAN: <one-line reason>` on the last line and stop.

## Out of scope (do not touch)
- Migrations, `pyproject.toml`, Docker/Compose files, `Makefile`, `scripts/`, `.claude/`.
- Other features (F01–F05 behaviour must not change except the list response shape).
- Refactors, renames, reformatting of files you do not need to change.

## Memory between iterations
If `runs/loop-*/loop-state.md` exists, read it first: it lists what previous iterations did and
what the verifier and reviewer said. Fix those findings before anything else.
