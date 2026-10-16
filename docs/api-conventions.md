# API conventions

Read this when **adding or changing an endpoint, request field or response field**.

## URLs

- Everything except `/health` and `/docs` lives under `/api/v1`.
- Resources are plural nouns: `/projects`, `/tasks`.
- Children are nested once: `/projects/{project_id}/tasks`. Individual tasks are addressed
  directly: `/tasks/{task_id}`.
- Sub-resources that compute something are nouns: `/projects/{id}/stats`, not `/getStats`.
- Path ids are integers.

## Methods and status codes

| Action | Method | Success | Common errors |
|---|---|---|---|
| Create | `POST` | `201` + body | `404` parent missing, `409` conflict, `422` validation |
| List | `GET` | `200` + list/envelope | `404` parent missing, `422` bad filter |
| Read | `GET` | `200` | `404` |
| Partial update | `PATCH` | `200` + body | `404`, `422` |
| Delete | `DELETE` | `204`, no body | `404` |

`PUT` is not used. Validation errors stay FastAPI's default `422`.

## Error shape

```json
{"detail": "Project not found"}
```

- `detail` is a human-readable sentence; for `422` it is FastAPI's list of errors.
- Do not leak SQL, stack traces or internal ids of other users in `detail`.

## Field naming and types

| Rule | Example |
|---|---|
| `snake_case` JSON fields | `project_id`, `due_at` |
| Timestamps end in `_at`, ISO 8601 **with timezone** | `"due_at": "2026-10-20T17:00:00Z"` |
| Dates without time end in `_on` | `"start_on": "2026-10-20"` |
| Booleans are adjectives/`is_`, never strings | `"overdue": true` |
| Enums are lowercase strings | `"status": "in_progress"` |
| Counts are integers, never null | `"todo": 0` |
| Optional fields are present with `null`, not omitted | `"description": null` |

Request timestamps without a timezone are rejected (`422`) — use Pydantic `AwareDatetime`.

## Filtering

- Filters are query parameters named after the field: `?status=todo`.
- Range filters use `min_`/`max_` prefixes, **inclusive**: `?max_priority=2` → priority ≤ 2.
- Boolean filters accept `true`/`false`: `?overdue=true`.
- Multiple filters combine with **AND**.
- Unknown enum values → `422`.

## Pagination (list endpoints)

List endpoints that can grow unbounded return an **envelope**:

```json
{"items": [...], "total": 42, "limit": 20, "offset": 40}
```

| Param | Default | Bounds | Notes |
|---|---|---|---|
| `limit` | 20 | 1–100 | `limit=0` or `>100` → `422` |
| `offset` | 0 | ≥ 0 | Offset past the end → empty `items`, `total` unchanged |

- `total` counts all rows matching the filters (not just this page).
- Default sort is **ascending `id`** and must be stable across pages.
- Filters apply before pagination.

## Ordering

All list endpoints sort by `id ASC` unless a documented `?sort=` parameter says otherwise.
Changing the default order is a **breaking change**.

## Versioning and compatibility

- Adding an optional response field is non-breaking.
- Removing/renaming a field, changing a type, changing a default, or changing ordering is
  **breaking** — it needs a new version or explicit human approval.

## Response models

- Every route declares `response_model=` (or a return type FastAPI can use).
- Schemas live in `app/schemas.py`: `<Thing>Create`, `<Thing>Update`, `<Thing>Read`.
- `Update` schemas have all fields optional; apply with `model_dump(exclude_unset=True)`.
- Use Pydantic v2 APIs: `model_dump()`, `model_validate()` — never `.dict()` / `.parse_obj()`.
