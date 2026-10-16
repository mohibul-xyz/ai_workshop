# Architecture

Read this when you need to know **where code goes** or how a request flows through TaskHub.

## Layers

```
HTTP request
  └─ app/api/<resource>.py      FastAPI routers: parse/validate input, map errors to HTTP
       └─ app/services/<x>.py   Business logic + queries. No FastAPI imports here.
            └─ app/models.py    SQLAlchemy 2 ORM models (the schema of record)
                 └─ PostgreSQL 16 (schema changed only via migrations/)
```

| Path | Owns | Must not |
|---|---|---|
| `app/main.py` | App factory, `/health`, middleware, router wiring | Contain business logic |
| `app/api/` | Routes, status codes, `HTTPException` | Touch `Session.execute` with raw SQL |
| `app/api/deps.py` | Shared dependencies (`SessionDep`) | — |
| `app/services/` | Queries, filters, transactions, domain errors | Import `fastapi` |
| `app/schemas.py` | Pydantic v2 request/response models | Hold ORM objects as fields |
| `app/models.py` | ORM models, enums, constraints | Be changed without a migration |
| `app/config.py` | `Settings` from env (`pydantic-settings`) | Hard-code secrets |
| `migrations/` | Alembic revisions, sequential ids `0001`, `0002`, … | Be edited after commit |
| `tests/` | pytest; runs against real Postgres (`taskhub_test`) | Mock the database |

## Request flow example: `GET /api/v1/projects/{id}/tasks?status=todo`

1. `app/api/tasks.py::list_tasks` validates `status` (enum) and `max_priority` (1–5).
2. `_require_project` returns 404 if the project does not exist.
3. `app/services/tasks.py::list_tasks` builds a `select(Task)` with optional filters,
   ordered by `Task.id`.
4. FastAPI serialises with `TaskRead` (`from_attributes=True`).

## Errors

- Services raise **domain exceptions** (e.g. `DuplicateProjectError`).
- Routers translate them into `HTTPException` with the shapes in `docs/api-conventions.md`.
- Never catch broad `Exception` in services; let unexpected errors surface as 500 and in logs.

## Database sessions

- One `Session` per request via `app.db.get_session` (dependency).
- Services call `session.commit()` at the end of a write.
- Tests override `get_session` with a session bound to an outer transaction
  (`join_transaction_mode="create_savepoint"`), so commits never leak between tests.

## Runtime

| Service | What it is |
|---|---|
| `db` | Postgres 16; also creates `taskhub_test` and `taskhub_migcheck` (`db/init/`) |
| `migrate` | One-shot `alembic upgrade head` before `api` starts |
| `api` | `uvicorn --reload` on :8000, source bind-mounted |
| `tools` | Same image; runs pytest / ruff / mypy / alembic (`make test`, …) |
| `agent` | Sandboxed Claude Code for autonomous loops (Stage 7) |

All commands go through the `Makefile`; never call `docker compose` with ad-hoc flags
when a target exists.

## Observability

- The API logs JSON lines to stdout, one per request, with `request_id`, `method`, `path`,
  `status`, `duration_ms`. Read them with `make logs` or `docker compose logs api`.
- Every response carries `X-Request-ID`; send one in to correlate a test with its log line.
- Agent actions are logged to `.claude/audit.log` by the audit hook; summarise with
  `python3 scripts/audit_report.py`.

## Adding a feature (shape of a typical change)

1. Model change → migration via the `write-migration` skill.
2. Schema change in `app/schemas.py`.
3. Service logic in `app/services/`.
4. Route in `app/api/`.
5. Tests in `tests/` (see `docs/testing-standards.md`).
6. `feature_list.json` evidence → `make verify`.
