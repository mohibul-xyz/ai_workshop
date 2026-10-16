# F07 — Search tasks by title

> Status: approved   ·   Owner: mohibul-dev   ·   Feature: `feature_list.json` → F07

## 1. Problem
Projects accumulate many tasks, and the only ways to narrow a list today are status, priority,
due date and tag. Someone who remembers a word from a task's title ("login", "invoice") has to
page through the whole list to find it.

## 2. User stories
- As a team member, I want to search a project's tasks by a word in the title, so that I can find a task without paging through the list.
- As a team lead, I want to combine a title search with the existing filters, so that I can answer questions like "open login tasks tagged urgent".

## 3. API contract

| Method | Path | Request | Success | Errors |
|---|---|---|---|---|
| `GET` | `/api/v1/projects/{id}/tasks?q=login` | `q` query param (string), optional | `200`, `Page[TaskRead]` envelope of tasks whose `title` contains `q`, case-insensitive | `404` project not found, `422` invalid `q` |

`q` rules:
- Matching is a **case-insensitive substring match on `title` only** (`ILIKE '%' || q || '%'`).
- `q` is matched **literally**: `%`, `_` and `\` in `q` are escaped and never act as wildcards.
  `q` is passed as a bound parameter, never formatted into SQL.
- Leading and trailing whitespace is trimmed before matching (OQ2).
- After trimming, `q` must be 1–200 characters (200 = max title length). An empty,
  whitespace-only or longer `q` → `422` (OQ1, OQ3).
- `q` combines with `status`, `max_priority`, `overdue` and `tag` using **AND**, and is applied
  **before** pagination, so `total` counts all matching tasks.
- Ordering stays `id ASC`. No relevance ranking.
- Omitting `q` leaves the endpoint's behaviour unchanged.

Response shape is the existing envelope; no new response fields:

```json
{"items": [{"id": 1, "title": "Fix login bug", "...": "..."}], "total": 1, "limit": 20, "offset": 0}
```

## 4. Data model
No change. No new columns, indexes or migration (OQ5). The filter is a `WHERE title ILIKE :pattern ESCAPE '\'`
on the existing `tasks.title` column, scoped by `project_id` (already indexed).

## 5. Acceptance criteria
Fixture for AC1–AC3 unless stated: one project with tasks titled `"Fix login bug"`,
`"Write docs"`, `"Login page redesign"`, created in that order.

- **AC1 — search_matches_title_substring**
  Given the fixture
  When I `GET .../tasks?q=login`
  Then the response is `200` and `items` are `"Fix login bug"` and `"Login page redesign"` in `id` order, with `total` `2`.

- **AC2 — search_is_case_insensitive**
  Given the fixture
  When I `GET .../tasks?q=LoGiN`
  Then the same two tasks as AC1 are returned.

- **AC3 — search_without_match_returns_empty_page**
  Given the fixture
  When I `GET .../tasks?q=zzz`
  Then the response is `200` with `items` `[]` and `total` `0`.

- **AC4 — search_treats_wildcards_literally**
  Given tasks titled `"100% done"`, `"1000 done"`, `"snake_case"`, `"snakeXcase"`, `"C:\temp"`
  When I `GET .../tasks?q=%`, then `?q=_`, then `?q=\`
  Then each returns only `"100% done"`, `"snake_case"` and `"C:\temp"` respectively.

- **AC5 — search_matches_title_only**
  Given a task titled `"Write docs"` with description `"login flow"`
  When I `GET .../tasks?q=login`
  Then that task is not returned.

- **AC6 — search_is_scoped_to_project**
  Given tasks titled `"Fix login bug"` and `"Write docs"` in project A, and `"Fix login bug"` in project B
  When I `GET /projects/A/tasks?q=login`
  Then only project A's task is returned.

- **AC7 — search_combines_with_other_filters**
  Given `"Fix login bug"` with status `todo` tagged `urgent`, `"Login page redesign"` with status `done` tagged `urgent`, `"Login audit"` with status `todo` and no tags, and `"Write docs"` with status `todo` tagged `urgent`
  When I `GET .../tasks?q=login&status=todo&tag=urgent`
  Then only `"Fix login bug"` is returned.

- **AC8 — search_applies_before_pagination**
  Given 3 tasks whose titles contain `"login"` and 2 that do not
  When I `GET .../tasks?q=login&limit=2`, then `?q=login&limit=2&offset=2`
  Then the first page has 2 items, the second has 1, and both report `total` `3`.

- **AC9 — search_trims_whitespace**
  Given the fixture
  When I `GET .../tasks?q=%20%20login%20` (that is, `"  login "`)
  Then the same two tasks as AC1 are returned.

- **AC10 — empty_search_rejected**
  Given a project
  When I `GET .../tasks?q=` or `?q=%20%20%20` (whitespace only)
  Then the response is `422`.

- **AC11 — search_length_bounds**
  Given a task whose title is exactly 200 × `"a"`
  When I `GET .../tasks?q=` with that 200-char string, then with 201 × `"a"`
  Then the first returns `200` with that task, and the second returns `422`.

- **AC12 — search_unknown_project_404**
  Given no project with id `999999`
  When I `GET /projects/999999/tasks?q=login`
  Then the response is `404` with `{"detail": "Project not found"}`.

- **AC13 — no_search_param_unchanged**
  Given the fixture
  When I `GET .../tasks` without `q`
  Then all three tasks are returned in `id` order with `total` `3` (backward compatible).

## 6. Non-goals
- Searching `description`, tags or other fields (OQ4).
- Full-text search, stemming, typo tolerance, accent-insensitive matching, relevance ranking or a `?sort=` option.
- Multi-term syntax (`q=login bug` is one literal substring, not "login AND bug").
- A trigram / full-text index (OQ5).
- Search across projects (`GET /tasks?q=`).

## 7. Open questions
All resolved 2026-10-17: the owner approved the spec as proposed ("Implement F07 from the spec").

- ~~**OQ1 — Empty `q`:** `422`, or treat as "no filter"?~~ **Resolved:** `?q=` or whitespace-only → `422`.
  Matches the `?tag=` filter (empty tag → `422`) and the "bad filter → 422" convention.
- ~~**OQ2 — Trim `q`?**~~ **Resolved:** trim leading/trailing whitespace, consistent with tag
  normalisation (so a title's leading or trailing space can't be searched for).
- ~~**OQ3 — Max length?**~~ **Resolved:** 200 characters, the title column's limit. Longer → `422`.
- ~~**OQ4 — Fields searched?**~~ **Resolved:** title only, per `feature_list.json`.
- ~~**OQ5 — Index?**~~ **Resolved:** no index for now. A leading-wildcard `ILIKE` can't use a B-tree
  index; per-project task counts are small and the scan is already scoped by `project_id`. A
  `pg_trgm` GIN index would need an extension and a migration — a later feature if needed.
