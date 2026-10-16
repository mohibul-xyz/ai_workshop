# Database rules

Read this **before touching `app/models.py` or `migrations/`**. The `write-migration` skill
follows these rules; `make migrate-check` enforces most of them.

## Golden rules

1. **Every schema change is a migration.** Never `Base.metadata.create_all()` outside tests.
2. **Committed migrations are immutable.** Once a file in `migrations/versions/` is in git, fix
   mistakes with a *new* migration. The `guard_files` hook blocks edits; `check_migrations.py`
   fails if `git diff` shows changes to a committed revision.
3. **Sequential ids.** Revision ids are `0001`, `0002`, … and filenames are `<id>_<slug>.py`.
   Use `make migration name=<snake_slug>`; do not invent hashes.
4. **Linear history.** Exactly one head. `down_revision` points to the previous id.
5. **`downgrade()` reverses `upgrade()` exactly**, in reverse order. An empty `downgrade()` or
   `pass` is rejected.
6. **Round-trip must pass:** upgrade → downgrade → upgrade on the throwaway `taskhub_migcheck`
   database (`make migrate-check`).

## Column changes

| Change | Safe recipe |
|---|---|
| Add nullable column | `op.add_column(...)` — fine |
| Add NOT NULL column to existing table | `server_default=...` **or** 3 steps: add nullable → backfill → `alter_column(nullable=False)` |
| Rename column | Add new → backfill → switch code → drop old in a *later* release. Never `alter_column(new_column_name=...)` in one step on shared data |
| Drop column / table | **Ask a human first.** Data loss is irreversible; the downgrade can recreate the column but not the data |
| Change type | Explicit `postgresql_using=` cast; test downgrade |
| Add enum value | `ALTER TYPE ... ADD VALUE` cannot run in a transaction block on older PG; use `op.execute` with `autocommit_block()` |

## Types and conventions

- Primary keys: `Integer`, named `id`.
- Foreign keys: `<table_singular>_id`, `ondelete="CASCADE"` only when children are meaningless
  without the parent (tasks → project). Always index FK columns.
- Timestamps: `DateTime(timezone=True)` (**timestamptz**). Never naive datetimes.
  Compare with `datetime.now(UTC)` in Python or `func.now()` in SQL.
- Enums: SQLAlchemy `Enum(PyEnum, name="<snake>")`; the downgrade must drop the type.
- Check constraints are named `ck_<table>_<what>`; unique constraints `uq_<table>_<cols>`.
- Many-to-many: association table `<a>_<b>` with a composite primary key.

## Autogenerate is a draft, not a result

`alembic revision --autogenerate` misses or mangles:
- server defaults and check constraints,
- enum type creation/drop,
- renames (it emits drop + add — **data loss**),
- index names.

Always read the generated file line by line before keeping it.

## Queries

- Use SQLAlchemy Core/ORM expressions. **Never** build SQL with f-strings or `%` formatting.
  If raw SQL is unavoidable, use `text()` with bound parameters (`:name`).
- `LIKE`/`ILIKE` user input must be escaped or passed as a bound parameter.
- Avoid N+1: use `selectinload` for collections you return.

## Destructive operations (never without a human)

`DROP TABLE`, `DROP DATABASE`, `TRUNCATE`, `alembic downgrade base`, `docker compose down -v`.
The `guard_bash` hook blocks these. If you think one is needed, stop and say why.

## Databases

| Name | Used by |
|---|---|
| `taskhub` | dev stack (`make up`) |
| `taskhub_test` | `make test` |
| `taskhub_migcheck` | `make migrate-check` round-trip (wiped each run) |
