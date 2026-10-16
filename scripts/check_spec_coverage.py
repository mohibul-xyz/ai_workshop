#!/usr/bin/env python3
"""Spec ↔ test traceability (topic 7, spec-driven development).

Every acceptance criterion `**AC<N> — <slug>**` in specs/<ID>-*.md must have exactly one
test named `test_ac<N>_<slug>` somewhere under tests/. Tests named test_ac* that match no
criterion are reported too (a test without a requirement is scope creep or a stale spec).

Usage: python3 scripts/check_spec_coverage.py [specs/F05-task-tags.md ...]   (default: all specs)
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AC_RE = re.compile(r"^\s*-\s*\*\*AC(\d+)\s*[—-]+\s*([a-z0-9_]+)\*\*", re.M)
TEST_RE = re.compile(r"^\s*def (test_ac(\d+)_([a-z0-9_]+))\(", re.M)


def main() -> int:
    specs = [Path(p) for p in sys.argv[1:]] or sorted(
        p for p in (ROOT / "specs").glob("F*.md") if not p.name.endswith(".plan.md")
    )
    tests: dict[str, list[str]] = {}
    for path in (ROOT / "tests").rglob("test_*.py"):
        for m in TEST_RE.finditer(path.read_text(encoding="utf-8")):
            tests.setdefault(m.group(1), []).append(path.relative_to(ROOT).as_posix())

    failed = False
    for spec in specs:
        criteria = AC_RE.findall(spec.read_text(encoding="utf-8"))
        if not criteria:
            print(f"FAIL {spec}: no acceptance criteria found (format: - **AC1 — slug**)")
            failed = True
            continue
        wanted = {f"test_ac{n}_{slug}" for n, slug in criteria}
        missing = sorted(wanted - tests.keys(), key=lambda t: int(t.split("_")[1][2:]))
        dupes = sorted(t for t in wanted if len(tests.get(t, [])) > 1)
        print(
            f"{'FAIL' if missing or dupes else 'OK  '} {spec.relative_to(ROOT)}: "
            f"{len(wanted) - len(missing)}/{len(wanted)} criteria have a test"
        )
        for t in missing:
            print(f"  - missing test: {t}")
        for t in dupes:
            print(f"  - duplicated test name: {t} in {tests[t]}")
        failed |= bool(missing or dupes)

    all_wanted = set()
    for spec in specs:
        all_wanted |= {f"test_ac{n}_{s}" for n, s in AC_RE.findall(spec.read_text())}
    orphans = sorted(t for t in tests if t not in all_wanted)
    for t in orphans:
        print(f"WARN orphan acceptance test (no matching criterion): {t} in {tests[t][0]}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
