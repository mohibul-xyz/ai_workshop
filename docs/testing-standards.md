# Testing standards

Read this when **writing or changing tests**, or before claiming a feature is done.

## Where tests run

- `make test` runs pytest in the `tools` container against **real Postgres** (`taskhub_test`).
- Migrations are applied once per session (`alembic upgrade head`) by `tests/conftest.py`.
- Each test runs inside an outer transaction that is rolled back — tests are isolated and
  order-independent.
- Do **not** mock the database or SQLAlchemy. The bugs we care about live in the queries.

## Fixtures (tests/conftest.py)

| Fixture | Gives you |
|---|---|
| `client` | `TestClient` with `get_session` overridden |
| `session` | The rolled-back SQLAlchemy `Session` (for direct setup/asserts) |
| `project_id` | A freshly created project's id |

Prefer creating data through the API (`client.post`) so tests exercise the real path;
use `session` only when the API cannot reach the state you need (e.g. a task due in the past).

## What every feature needs

1. **Happy path** — the documented behaviour with realistic data.
2. **Boundaries** — inclusive/exclusive edges (`max_priority=2` includes 2; `due_at == now`).
3. **Negative cases** — 404 for missing parents, 422 for invalid input, 409 for conflicts.
4. **Interaction** — the new filter combined with existing filters.
5. **Regression guard** — existing behaviour (ordering, defaults) still holds.

## Naming

- File per resource/feature: `tests/test_<feature>.py`.
- Test names describe behaviour: `test_overdue_excludes_done_tasks`, not `test_overdue_2`.
- Spec-driven features name tests after acceptance criteria: `test_ac1_<slug>`, `test_ac2_<slug>`;
  `make lab-spec` checks every AC in the spec has one.

## Rules

- **A test must fail before the change and pass after.** Run it against the old code once.
- Never delete or weaken an assertion to make a test pass. If behaviour changed on purpose,
  say so in the commit message and the feature notes.
- No `pytest.skip`, `xfail`, or `@pytest.mark.skip` without a linked reason and human approval.
- No sleeps; no network calls outside the stack; no dependence on wall-clock time — inject
  `now` or create timestamps relative to `datetime.now(UTC)` with a wide margin.
- Assert on **status code and body**, not just one.
- Keep tests deterministic: sort or compare sets when order is not part of the contract.

## Hidden tests

`benchmarks/**/hidden/` holds acceptance tests used to score the benchmark. **You may not read
them** (permissions deny it). Work from the task description and these standards.

## The three verification layers (`make verify`)

| Layer | Command | Proves |
|---|---|---|
| 1. Static | `ruff`, `ruff format --check`, `mypy --strict` | Code is well-formed and typed |
| 2. Behaviour | `pytest` + migration round-trip | Logic and schema changes are correct and reversible |
| 3. System | stack up + `scripts/smoke_e2e.py` | The real service works end-to-end over HTTP |

Evidence is written to `runs/verify-<timestamp>.log`. Cite that path in `feature_list.json`.

## Evidence

"Done" means: the feature's `verification` commands in `feature_list.json` pass, and
`evidence` lists the log file(s) and test names that prove it. Confidence is not evidence.
