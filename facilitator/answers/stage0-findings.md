# Answer key — Stage 0 findings sheet

Reference fixes: `stages/00-baseline-reading-ai-code/solutions/`. Checked by
`make stage0-check SOLUTION=1` (tests vs solutions + this sheet).

| # | Location (file:line) | Category | Evidence | Fix |
|---|---|---|---|---|
| 1 | export_tasks.py:10 | invented api | `from fastapi.responses import CSVResponse` → ImportError; FastAPI has no CSVResponse (test_module_imports) | `fastapi.Response(content=..., media_type="text/csv")` |
| 2 | export_tasks.py:30 | invented api | `.paginate(page=, per_page=)` exists only in Flask-SQLAlchemy → AttributeError on SQLAlchemy 2 (test_paginates_with_sqlalchemy_2) | `select(Task)...limit(per_page).offset((page-1)*per_page)` |
| 3 | export_tasks.py:37 | hidden bug | `.dict()` is Pydantic v1; on v2 it is deprecated (warning today, removal later) and serialises datetimes as objects (test_uses_pydantic_v2_api) | `.model_dump(mode="json")` |
| 4 | overdue.py:18 | weak logic | Done tasks with a past due date are reported overdue (test_done_tasks_are_not_overdue) | add `task.status != TaskStatus.done` |
| 5 | overdue.py:18 | weak logic | `<=`: a task due exactly now counts as late — off by one at the boundary (test_due_exactly_now_is_not_yet_overdue) | strict `<` |
| 6 | overdue.py:17 | hidden bug | `datetime.utcnow()` is naive; Postgres timestamptz values are aware → `TypeError: can't compare offset-naive and offset-aware` only when `now` is not injected — i.e. in production, never in the tests the agent wrote (test_default_now_works_with_aware_due_dates) | `datetime.now(UTC)` |
| 7 | retry.py:31 | weak logic | Never sleeps: `continue` immediately, so all retries fire within microseconds (test_sleeps_between_attempts) | `time.sleep(delay)` between attempts |
| 8 | retry.py:28 | weak logic | `base_delay * attempt**2` gives 0, 0.5, 2.0 — not exponential, and 0 on the first retry (test_backoff_doubles_each_time) | `base_delay * 2**attempt` |
| 9 | retry.py:17 | hidden bug | `history: list[float] = []` — mutable default shared by every call; grows forever across requests (test_no_mutable_default_arguments) | `history: list[float] \| None = None` |
| 10 | retry.py:27 | hidden bug | bare `except:` swallows everything (ValueError, KeyboardInterrupt) and the function returns `None` after the last failure — callers think it succeeded (test_errors_are_not_swallowed) | `except retry_on:` and re-raise on the last attempt |
| 11 | search.py:19 | hidden bug | f-string inside `text()` → SQL injection: `q="') OR 1=1 OR lower(title) LIKE ('"` returns other projects' tasks; `q="o'brien"` crashes (test_cannot_read_other_projects_via_injection, test_quotes_in_query_are_data_not_sql) | ORM `.contains(q, autoescape=True)` / bound parameters |

## Talking points
- Every file has a confident docstring that describes what the code *should* do. Rows 2, 3, 7,
  8 contradict their own docstring — read the code, not the comment.
- Rows 6 and 10 pass every test the generating agent would plausibly write (it injects `now`;
  it tests the success path). Only real data or adversarial tests expose them.
- Harness responses later in the day: `post_edit_lint` (ruff B006 mutable default, E722 bare
  except, S608 SQL), `docs/database-rules.md` (no f-string SQL), `docs/api-conventions.md`
  (aware timestamps), the reviewer subagent, and `review_diff.py`.
