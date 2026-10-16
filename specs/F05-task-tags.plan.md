# F05 — Task tags: implementation plan

Approved by: facilitator (reference build). Each step lists files, the ACs it serves, and its check.

| # | Step | Files | ACs | Verify with |
|---|---|---|---|---|
| 1 | `Tag` model + `task_tags` association; `Task.tags` relationship (`selectinload`) | `app/models.py` | AC11, AC12 | `make typecheck` |
| 2 | Migration `0003_add_tags` via `write-migration` skill | `migrations/versions/0003_add_tags.py` | AC11, AC12 | `make migrate-check` |
| 3 | `TagName` constrained type (strip, lower, regex, ≤32) and `tags` field on Create/Update/Read (≤10, dedupe, sorted output) | `app/schemas.py` | AC1–AC5 | `make typecheck` |
| 4 | Service: get-or-create tags, set on create, replace on patch only if `tags` was sent | `app/services/tasks.py` | AC1, AC6, AC7, AC11 | unit via API tests |
| 5 | `?tag=` filter (normalised, scoped by project, AND with others) | `app/services/tasks.py`, `app/api/tasks.py` | AC8–AC10 | API tests |
| 6 | Tests `test_ac1_…` … `test_ac12_…` | `tests/test_tags.py` | all | `make test`, `make lab-spec` |
| 7 | Verify + review | — | all | `EVIDENCE=F05 make verify`; `reviewer` subagent against this spec |
| 8 | State | `feature_list.json`, `claude-progress.md` | — | `make check-state` |

Out of scope (from spec non-goals): `/tags` endpoints, multi-tag filter, per-project tags.
