#!/usr/bin/env python3
"""Generate the three context variants for topic 10 from the live repo.

  variants/bloated/CLAUDE.md   A — ~600 lines: every doc @imported, a changelog, duplicated
                                   tables, stale + contradictory rules, a hard constraint buried
                                   in the middle ("lost in the middle")
  variants/router/CLAUDE.md    B — the Stage 1 router (copy of the root CLAUDE.md)
  variants/hygiene/CLAUDE.md   C — router + a context-hygiene section
  variants/hygiene/settings.overlay.json — deny reads of noise (runs/, logs, lockfiles, fixtures)

Usage: python3 make_variants.py          # (re)write the variants
       python3 make_variants.py --check  # exit 1 if the committed variants are stale
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / "variants"

HYGIENE = """
## Context hygiene (variant C)
- Do not read `runs/**`, `evidence/**`, `*.log`, lockfiles or `stages/**/fixtures/**`; they are
  evidence for humans, not context for you (reads are denied in settings).
- Delegate broad exploration ("where is X used?") to a subagent and keep only its conclusion.
- One feature per session: `/clear` between features; `/compact` when a long task nears the limit.
- Load a `docs/` file only when its "read when" line matches what you are doing right now.
"""

STALE_RULES = [
    "Use `pytest` directly from your shell; the Makefile is optional.",
    "Pagination uses Flask-SQLAlchemy's `.paginate(page, per_page)`.",
    "Timestamps are naive UTC (`datetime.utcnow()`); timezones are handled by the frontend.",
    "Prefer `.dict()` when serialising schemas — it is the stable Pydantic API.",
    "List endpoints return a bare JSON array, never an envelope.",
    "Run `alembic downgrade base && alembic upgrade head` to reset a broken database.",
    "Tests may use SQLite in-memory for speed; Postgres is only needed in production.",
    "Feel free to reformat any file you touch to keep style consistent across the repo.",
    "Use `print()` for debugging; the logs are not structured anyway.",
    "If a test is flaky, mark it `@pytest.mark.skip` and move on.",
]


def bloated(router: str) -> str:
    docs = sorted((ROOT / "docs").glob("*.md"))
    lines = [
        "# TaskHub — complete agent handbook (variant A: bloated)",
        "",
        "This file is the single source of truth. Read ALL of it before every task.",
        "Everything the project knows is imported below so you never have to look elsewhere.",
        "",
        "## Imported documentation",
        *[f"@{d.relative_to(ROOT).as_posix()}" for d in docs],
        "@README.md",
        "@claude-progress.md",
        "@evaluator-rubric.md",
        "@quality-document.md",
        "@clean-state-checklist.md",
        "",
        "## History of this project",
    ]
    for week in range(1, 41):
        lines += [
            f"### Week {week}",
            f"- Discussed naming of endpoints (round {week}); decided to revisit next week.",
            f"- Upgraded dependencies; {'ruff' if week % 2 else 'mypy'} found a few issues, fixed.",
            "- Reminder: keep the README up to date.",
        ]
    lines += ["", "## Coding style (expanded)"]
    for i in range(1, 61):
        lines.append(
            f"{i}. Style rule {i}: prefer clarity; name things well; avoid surprises "
            f"(see also rule {(i % 60) + 1})."
        )
    lines += ["", "## Rules (some may be outdated — use judgement)"]
    for i, rule in enumerate(STALE_RULES, 1):
        lines.append(f"{i}. {rule}")
        if i == len(STALE_RULES) // 2:
            # The one non-negotiable rule, buried mid-file between stale ones.
            lines.append(
                "    IMPORTANT: never edit a committed migration and never read "
                "benchmarks/**/hidden/**."
            )
    lines += ["", "## Glossary"]
    for term in (
        "project",
        "task",
        "status",
        "priority",
        "due date",
        "overdue",
        "tag",
        "envelope",
        "limit",
        "offset",
        "migration",
        "revision",
        "head",
        "fixture",
        "harness",
        "hook",
        "skill",
        "subagent",
        "permission",
        "evidence",
    ):
        lines += [
            f"- **{term}**: see the code; the {term} concept is used throughout TaskHub "
            f"and should be handled consistently wherever {term}s appear."
        ]
    lines += ["", "## Commands (duplicated for convenience)"]
    for _ in range(3):
        lines += [
            "| Purpose | Command |",
            "|---|---|",
            "| Tests | `pytest` |",
            "| Lint | `ruff check .` |",
            "| Types | `mypy app` |",
            "| Run | `uvicorn app.main:app --reload` |",
            "",
        ]
    lines += ["", "## Router (kept for reference)", "", *router.splitlines()]
    while len(lines) < 600:
        lines.append(f"<!-- padding note {len(lines)}: legacy content kept for completeness -->")
    return "\n".join(lines) + "\n"


def build() -> dict[Path, str]:
    router = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    overlay = {
        "permissions": {
            "deny": [
                "Read(./runs/**)",
                "Read(./evidence/**)",
                "Read(./**/*.log)",
                "Read(./**/*.lock)",
                "Read(./stages/**/fixtures/**)",
                "Read(./stages/**/fixtures-human/**)",
            ]
        }
    }
    return {
        OUT / "bloated" / "CLAUDE.md": bloated(router),
        OUT / "router" / "CLAUDE.md": router,
        OUT / "hygiene" / "CLAUDE.md": router.rstrip("\n") + "\n" + HYGIENE,
        OUT / "hygiene" / "settings.overlay.json": json.dumps(overlay, indent=2) + "\n",
    }


def main() -> int:
    files = build()
    if "--check" in sys.argv:
        stale = [p for p, text in files.items() if not p.exists() or p.read_text() != text]
        for p in stale:
            print(f"STALE {p.relative_to(ROOT)} — run: python3 {Path(__file__).relative_to(ROOT)}")
        if not stale:
            print("OK   context variants in sync with CLAUDE.md")
        return 1 if stale else 0
    for path, text in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        print(f"wrote {path.relative_to(ROOT)} ({len(text.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
