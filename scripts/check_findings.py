#!/usr/bin/env python3
"""Check a Stage 0 findings sheet is complete: every row has a location with a line number,
a valid category, evidence and a fix. Also checks that every seeded file is covered.

Usage: python3 scripts/check_findings.py [stages/00-baseline-reading-ai-code/findings-sheet.md]
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "stages" / "00-baseline-reading-ai-code" / "findings-sheet.md"
CATEGORIES = ("invented api", "weak logic", "hidden bug")
FILES = {"export_tasks.py": 3, "overdue.py": 3, "retry.py": 4, "search.py": 1}


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if len(cells) == 5 and cells[0].isdigit():
            rows.append(cells)
    problems = []
    per_file: dict[str, int] = {}
    for num, loc, cat, evidence, fix in rows:
        m = re.match(r"(\w+\.py):\s*(\d+)", loc)
        if not m:
            problems.append(f"row {num}: location needs file.py:<line>")
        else:
            per_file[m.group(1)] = per_file.get(m.group(1), 0) + 1
        if cat.lower() not in CATEGORIES:
            problems.append(f"row {num}: category must be one of {', '.join(CATEGORIES)}")
        if len(evidence) < 8:
            problems.append(f"row {num}: evidence missing (quote the line, the error or the test)")
        if len(fix) < 5:
            problems.append(f"row {num}: fix missing")
    for name, want in FILES.items():
        if per_file.get(name, 0) < want:
            problems.append(f"{name}: {per_file.get(name, 0)}/{want} seeded flaws written up")
    filled = len(rows) - len({p.split(":")[0] for p in problems if p.startswith("row")})
    if problems:
        print(f"TODO {path.name}: {filled}/{len(rows)} rows complete")
        for p in problems[:15]:
            print(f"  - {p}")
        return 1
    print(f"OK   {path.name}: {len(rows)} findings, every seeded flaw written up")
    return 0


if __name__ == "__main__":
    sys.exit(main())
