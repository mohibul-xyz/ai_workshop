# F07 — Search tasks by title: implementation plan

Approved by: mohibul-dev (spec approved as proposed). Each step lists files, the ACs it serves, and its check.

| # | Step | Files | ACs | Verify with |
|---|---|---|---|---|
| 1 | Tests `test_ac1_…` … `test_ac13_…`, written first; the new-behaviour ones must fail on `main` | `tests/test_search.py` | all | `make test` (expect failures), `make lab-spec` |
| 2 | Service: `q` param on `tasks_query`/`list_tasks`; `Task.title.ilike(pattern, escape="\\")` with `\`, `%`, `_` escaped; bound parameter, no SQL formatting | `app/services/tasks.py` | AC1–AC8, AC13 | API tests |
| 3 | Route: `q: str \| None` query param; trim; 1–200 chars after trim else `422` (validated before the project lookup, like `tag`); pass to service | `app/api/tasks.py` | AC9–AC12 | API tests |
| 4 | Fast gate | — | all | `make check`, `make lab-spec` |
| 4a | System-layer smoke check for F07 (match, literal `_`, empty `q` → 422); runs once F07 is `passing` | `scripts/smoke_e2e.py` | AC1, AC4, AC10 | `make verify` (system layer) |
| 5 | Verify + review | — | all | `EVIDENCE=F07 make verify`; `reviewer` subagent against the spec |
| 6 | State | `feature_list.json`, `claude-progress.md` | — | `make check-state` |

No schema change, so no migration (spec §4, OQ5).
Out of scope (from spec non-goals): description/tag search, full-text, ranking, cross-project search, indexes.
