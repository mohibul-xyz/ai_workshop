#!/usr/bin/env python3
"""Migration checks used by `make migrate-check` and the write-migration skill.

--static     (host, stdlib only)
  * filenames are <NNNN>_<snake_slug>.py with sequential ids 0001, 0002, …
  * revision == filename id; down_revision == previous id (linear history, one head)
  * downgrade() is not empty / `pass`
  * op.add_column(... nullable=False ...) needs server_default= (or the 3-step backfill)
  * drop_column / drop_table in upgrade() needs an explicit `# approved-by: <name>` comment
  * committed migrations are immutable: no diff vs --base (default HEAD)

--roundtrip  (tools container; needs sqlalchemy + alembic)
  * on the throwaway MIGCHECK database: reset → upgrade head → downgrade base → upgrade head
  * after downgrade base no tables or enum types may remain (catches incomplete downgrades)
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "migrations" / "versions"
NAME_RE = re.compile(r"^(\d{4})_[a-z0-9_]+\.py$")


def _func(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    return next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name), None)


def _assign(tree: ast.Module, name: str) -> object:
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            targets = [node.target]
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                value = node.value
                if isinstance(value, ast.Constant):
                    return value.value
    return "<missing>"


def _is_empty(fn: ast.FunctionDef) -> bool:
    body = [
        n for n in fn.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))
    ]
    return all(isinstance(n, ast.Pass) for n in body)


def _op_calls(fn: ast.FunctionDef, names: set[str]) -> list[ast.Call]:
    out = []
    for node in ast.walk(fn):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in names
        ):
            out.append(node)
    return out


def _kw(call: ast.AST, name: str) -> ast.expr | None:
    for node in ast.walk(call):
        if isinstance(node, ast.Call):
            for kw in node.keywords:
                if kw.arg == name:
                    return kw.value
    return None


def static_check(base: str) -> list[str]:
    errors: list[str] = []
    files = sorted(p for p in VERSIONS.glob("*.py"))
    prev: str | None = None
    for idx, path in enumerate(files, 1):
        m = NAME_RE.match(path.name)
        if not m:
            errors.append(
                f"{path.name}: name must be NNNN_<snake_slug>.py (use `make migration name=<slug>`)"
            )
            continue
        rev_id = m.group(1)
        if int(rev_id) != idx:
            errors.append(f"{path.name}: expected id {idx:04d} (ids must be sequential)")
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src)
        if _assign(tree, "revision") != rev_id:
            errors.append(
                f"{path.name}: revision = {_assign(tree, 'revision')!r}, expected {rev_id!r}"
            )
        if _assign(tree, "down_revision") != prev:
            errors.append(
                f"{path.name}: down_revision = {_assign(tree, 'down_revision')!r}, "
                f"expected {prev!r} (linear history)"
            )
        prev = rev_id

        up, down = _func(tree, "upgrade"), _func(tree, "downgrade")
        if up is None or down is None:
            errors.append(f"{path.name}: needs both upgrade() and downgrade()")
            continue
        if _is_empty(down) and not _is_empty(up):
            errors.append(f"{path.name}: downgrade() is empty — it must reverse upgrade() exactly")
        for call in _op_calls(up, {"add_column"}):
            nullable = _kw(call, "nullable")
            if (
                isinstance(nullable, ast.Constant)
                and nullable.value is False
                and _kw(call, "server_default") is None
            ):
                errors.append(
                    f"{path.name}:{call.lineno}: NOT NULL add_column without "
                    "server_default — existing rows would fail; use server_default "
                    "or the 3-step backfill (docs/database-rules.md)"
                )
        destructive = _op_calls(up, {"drop_column", "drop_table"})
        if destructive and "# approved-by:" not in src:
            lines = ", ".join(str(c.lineno) for c in destructive)
            errors.append(
                f"{path.name}:{lines}: drop_column/drop_table in upgrade() loses data; "
                "needs a human-approved `# approved-by: <name>` comment"
            )

    # Committed migrations are immutable.
    res = subprocess.run(
        ["git", "diff", "--name-status", base, "--", "migrations/versions"],  # noqa: S603,S607
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    for line in res.stdout.splitlines():
        status, _, name = line.partition("\t")
        if status and status[0] in "MDR":
            errors.append(
                f"{name}: committed migration was "
                f"{'modified' if status[0] == 'M' else 'deleted/renamed'}"
                f" (vs {base}) — create a new revision instead"
            )
    return errors


def roundtrip() -> list[str]:
    from alembic import command
    from alembic.config import Config
    from sqlalchemy import create_engine, inspect, text

    url = os.environ.get(
        "MIGCHECK_DATABASE_URL", "postgresql+psycopg://taskhub:taskhub@db:5432/taskhub_migcheck"
    )
    if "migcheck" not in url:
        return [f"refusing to run round-trip on a non-throwaway database: {url}"]
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))

    os.environ["ALEMBIC_DATABASE_URL"] = url
    cfg = Config(str(ROOT / "alembic.ini"))
    errors: list[str] = []
    steps = [
        ("upgrade head", lambda: command.upgrade(cfg, "head")),
        ("downgrade base", lambda: command.downgrade(cfg, "base")),
        ("upgrade head (again)", lambda: command.upgrade(cfg, "head")),
    ]
    for label, step in steps:
        print(f"  roundtrip: {label}")
        try:
            step()
        except Exception as exc:  # noqa: BLE001 - report any migration failure
            return [f"{label} failed: {type(exc).__name__}: {exc}"]
        if label == "downgrade base":
            with engine.connect() as conn:
                left = [t for t in inspect(conn).get_table_names() if t != "alembic_version"]
                enums = (
                    conn.execute(
                        text(
                            "SELECT typname FROM pg_type t "
                            "JOIN pg_namespace n ON n.oid = t.typnamespace "
                            "WHERE n.nspname = 'public' AND t.typtype = 'e'"
                        )
                    )
                    .scalars()
                    .all()
                )
            if left:
                errors.append(f"after downgrade base, tables remain: {left}")
            if enums:
                errors.append(f"after downgrade base, enum types remain: {list(enums)}")
    engine.dispose()
    return errors


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--static", action="store_true")
    ap.add_argument("--roundtrip", action="store_true")
    ap.add_argument("--base", default="HEAD", help="git ref committed migrations are compared to")
    args = ap.parse_args()
    if not (args.static or args.roundtrip):
        args.static = True

    failed = False
    if args.static:
        errs = static_check(args.base)
        n = len(list(VERSIONS.glob("*.py")))
        print(("FAIL" if errs else "OK  ") + f" migrations static check ({n} revisions)")
        for e in errs:
            print(f"  - {e}")
        failed |= bool(errs)
    if args.roundtrip:
        errs = roundtrip()
        print(("FAIL" if errs else "OK  ") + " migration round-trip upgrade → downgrade → upgrade")
        for e in errs:
            print(f"  - {e}")
        failed |= bool(errs)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
