#!/usr/bin/env python3
"""Lint CLAUDE.md as a *router*, not an encyclopedia (course L4).

Checks:
  * length <= MAX_LINES (default 200)
  * required sections exist, in order: Overview, Hard constraints, Commands,
    Definition of done, Docs
  * Hard constraints are near the top and number <= 10
  * every backticked repo path in the file exists
  * every doc listed under "Docs" has a "read when" hint
  * --mirror: AGENTS.md is byte-identical (Codex users read AGENTS.md)

Usage: python3 scripts/lint_claude_md.py [CLAUDE.md] [--mirror AGENTS.md] [--max-lines N]
Stdlib only. Exit 0 = clean, 1 = problems found.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED = ["overview", "hard constraints", "commands", "definition of done", "docs"]
PATH_RE = re.compile(r"`([A-Za-z0-9_.\-/*]+)`")
PATH_PREFIXES = (
    "docs/",
    "scripts/",
    "specs/",
    "goals/",
    "app/",
    "tests/",
    "migrations/",
    "stages/",
    "benchmarks/",
    ".claude/",
)
PATH_FILES = {
    "feature_list.json",
    "claude-progress.md",
    "session-handoff.md",
    "init.sh",
    "Makefile",
    "AGENTS.md",
    "evaluator-rubric.md",
    "quality-document.md",
    "clean-state-checklist.md",
}


def lint(path: Path, root: Path, max_lines: int) -> list[str]:
    problems: list[str] = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if len(lines) > max_lines:
        problems.append(f"{len(lines)} lines > {max_lines}: move detail into docs/ and link it")
    if len(lines) < 20:
        problems.append(f"only {len(lines)} lines: the router is missing content")

    headings = [
        (i, line[3:].strip().lower()) for i, line in enumerate(lines) if line.startswith("## ")
    ]
    positions: list[int] = []
    for req in REQUIRED:
        hit = next((i for i, h in headings if h.startswith(req)), None)
        if hit is None:
            problems.append(f"missing section '## {req.title()}'")
        else:
            positions.append(hit)
    if positions != sorted(positions):
        problems.append("sections out of order; expected: " + " -> ".join(REQUIRED))

    # Hard constraints: count numbered/bulleted items, check they are near the top.
    hc = next((i for i, h in headings if h.startswith("hard constraints")), None)
    if hc is not None:
        if hc > 15:
            problems.append(
                f"'Hard constraints' starts at line {hc + 1}; put it near the top "
                "(lost-in-the-middle)"
            )
        nxt = next((i for i, _ in headings if i > hc), len(lines))
        items = [ln for ln in lines[hc + 1 : nxt] if re.match(r"^\s*(\d+\.|[-*])\s+", ln)]
        if not items:
            problems.append("'Hard constraints' has no list items")
        elif len(items) > 10:
            problems.append(f"{len(items)} hard constraints > 10; keep only the non-negotiables")

    # Docs section: each bullet needs a "read when" hint.
    docs = next((i for i, h in headings if h.startswith("docs")), None)
    if docs is not None:
        nxt = next((i for i, _ in headings if i > docs), len(lines))
        for ln in lines[docs + 1 : nxt]:
            if (
                ln.lstrip().startswith(("-", "*"))
                and "read when" not in ln.lower()
                and "read the" not in ln.lower()
                and "goal files" not in ln.lower()
            ):
                problems.append(f"doc entry without a 'read when' hint: {ln.strip()[:70]}")

    # Linked paths must exist.
    for m in PATH_RE.finditer(text):
        ref = m.group(1).rstrip("/")
        if "*" in ref or "<" in ref:
            continue
        if ref.startswith(PATH_PREFIXES) or ref in PATH_FILES:
            if not (root / ref).exists():
                problems.append(f"linked path does not exist: {ref}")
    return problems


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?", default="CLAUDE.md")
    ap.add_argument("--mirror", default=None, help="file that must be byte-identical")
    ap.add_argument("--max-lines", type=int, default=200)
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"FAIL {path}: file not found")
        return 1
    root = Path.cwd()
    problems = lint(path, root, args.max_lines)
    if args.mirror:
        mirror = Path(args.mirror)
        if not mirror.exists():
            problems.append(f"mirror {mirror} not found")
        elif mirror.read_bytes() != path.read_bytes():
            problems.append(f"{mirror} differs from {path}; regenerate with: cp {path} {mirror}")

    n = len(path.read_text(encoding="utf-8").splitlines())
    if problems:
        print(f"FAIL {path} ({n} lines)")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(
        f"OK   {path} ({n} lines, all sections present, links resolve"
        + (", mirror in sync)" if args.mirror else ")")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
