# Quality document

A living, per-module grade (course template). Update when a module changes grade; the
reviewer and the `handoff` skill read it. Grades: **A** solid · **B** good, minor gaps ·
**C** works, known debt · **D** fragile, fix before building on it.

| Module | Grade | Tests | Known gaps / debt | Last reviewed |
|---|---|---|---|---|
| `app/api/projects.py` | A | `tests/test_projects.py` | — | 2026-10-17 |
| `app/api/tasks.py` | B | `tests/test_tasks.py`, `test_due_dates.py`, `test_tags.py` | List endpoints unbounded until F06 | 2026-10-17 |
| `app/services/tasks.py` | A | via API tests + direct `list_tasks` tests | — | 2026-10-17 |
| `app/schemas.py` | A | via API tests | — | 2026-10-17 |
| `app/models.py` | A | migration round-trip | — | 2026-10-17 |
| `app/observability.py` | B | smoke e2e checks `X-Request-ID` | No unit tests for the JSON formatter | 2026-10-17 |
| `migrations/` | A | `make migrate-check` round-trip | — | 2026-10-17 |
| `.claude/hooks/` | A | `make hooks-test` (25 tests) | Regex guards can be bypassed by obfuscation; permissions + sandbox are the backstop | 2026-10-17 |
| `scripts/verify.sh` | A | used by every feature | Layer 3 needs Docker; no offline fallback | 2026-10-17 |
| `scripts/review_diff.py` | B | `make lab-diffs` (3 PRs + negative control) | Heuristic; cannot judge intent | 2026-10-17 |

## Harness audit (five subsystems, 1–5)

| Subsystem | Score | Evidence |
|---|---|---|
| Instructions | | `make lab-claude-md` |
| Tools | | `make lab-permissions`, `make hooks-test` |
| Environment | | `./init.sh` from a fresh clone |
| State | | `make check-state`, fresh-session "continue" test |
| Feedback | | `make verify`, reviewer subagent, `make lab-diffs` |
