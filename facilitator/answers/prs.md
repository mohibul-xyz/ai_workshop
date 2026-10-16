# Answer key — seeded PRs (topic 9)

Base: the commit "F05: passing — make verify green, 12/12 ACs covered". Checked by `make lab-diffs`.
**S** = the scanner flags it; **H** = only a careful human read finds it.

## PR-101 "Add task search" → verdict: **block** (security)

| # | Where | Category | Defect | S/H | Fix |
|---|---|---|---|---|---|
| 1 | `app/services/tasks.py` `search_tasks` | Security | `text(f"... ILIKE '%{q}%' ...")` — user input interpolated into SQL → injection (`q = "x' OR 1=1 --"`) | S | `select(Task).where(Task.title.ilike(f"%{escape(q)}%"))` or `text(... :q)` with bound params |
| 2 | `tests/test_tasks.py` `test_get_update_delete_task` | Tests | `assert resp.json()["priority"] == 1` removed — PATCH priority is no longer verified | S | Restore the assertion |
| 3 | `app/config.py` | Scope | Unrelated reformat + `# noqa` that silences lint | S | Drop the file from the PR |
| 4 | `tests/test_tasks.py` `test_search_finds_title` | Tests | New test checks only the status code, not that the task was found | H | Assert the returned titles |
| 5 | whole PR | Scope | Search is not in `feature_list.json`; an autonomous run added an unrequested endpoint | H | Spec it as a feature first |

## PR-102 "Refactor list_tasks filters" → verdict: **block** (silent behaviour change)

| # | Where | Category | Defect | S/H | Fix |
|---|---|---|---|---|---|
| 1 | `list_tasks` | Behaviour | `order_by(Task.id.desc())` flips the default order (contract: `id ASC`) | S (line) / H (meaning) | Keep `Task.id` ascending |
| 2 | `MAX_TASKS = 99` | Behaviour | Comment says "never more than 100" — off by one, **and** lists are silently truncated (no pagination yet) | S (constant) / H | Remove the cap; F06 adds proper pagination |
| 3 | `tests/test_tasks.py:62`, `tests/test_due_dates.py:59,75` | Tests | Assertions wrapped in `sorted()` so they no longer check order — they were *catching* defect 1 | S | Revert the test changes |
| 4 | PR description | Honesty | "Pure refactor", "two assertions", "flaky" — all false (three assertions, deterministic) | H | — |

Teaching moment: "tests still pass" was true *because the tests were changed in the same PR*.

## PR-103 "Clean up migrations" → verdict: **block** (data loss)

| # | Where | Category | Defect | S/H | Fix |
|---|---|---|---|---|---|
| 1 | `migrations/versions/0001_initial.py` | Migrations | Committed migration edited (column removed, index renamed) → fresh DBs differ from existing ones | S | Never edit; new revision only |
| 2 | `0004_cleanup_unused_columns.py` `upgrade` | Data | `op.drop_column("projects", "description")` — irreversible data loss, no approval | S | Ask a human; if approved, back up and add `# approved-by:` |
| 3 | `0004` `downgrade` | Reversibility | `pass` (+ TODO) — cannot roll back | S | `op.add_column("projects", sa.Column("description", sa.Text()))` |
| 4 | `tests/test_projects.py` | Tests | Description assertion removed to make tests pass | S | — |
| 5 | `app/schemas.py` `ProjectRead` | Behaviour | Removing `description` from responses is a breaking API change | H | Needs versioning / human approval |
| 6 | description | Honesty | "Runs fine on a fresh database" hides what happens to existing ones | H | — |

## Scanner limits to discuss
- It cannot tell a refactor from a behaviour change — it only sees that `order_by` changed.
- It flags `MAX_TASKS = 99` as a magic constant, not *why* it is wrong (the comment says 100).
- Negative control: the real F05 commit gives zero HIGH findings. A noisy scanner gets ignored.
