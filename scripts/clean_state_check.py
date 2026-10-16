#!/usr/bin/env python3
"""make clean-state — every session ends in a state the next one can start from (course L12).

Checks (see clean-state-checklist.md):
  1. state files valid            scripts/check_state.py
  2. progress recorded            claude-progress.md touched if code changed since last commit
  3. no stray debug code          print( / breakpoint() / pdb / console logs in app/
  4. no stray files               *.orig, *.rej, *.bak, *.tmp, scratch*, tmp_* , core dumps
  5. no conflict markers          <<<<<<< / >>>>>>> in tracked text files
  6. build + tests pass           make check          (skip with --fast)
  7. startup path works           make up + GET /health (skip with --fast)

Usage: python3 scripts/clean_state_check.py [--fast]
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STRAY = re.compile(r"(\.orig|\.rej|\.bak|\.tmp|\.swp|~)$|(^|/)(scratch|tmp_)[^/]*$|(^|/)core$")
DEBUG = re.compile(r"^\s*(print\(|breakpoint\(\)|import pdb|pdb\.set_trace|import ipdb)")
CODE = ("app/", "migrations/", "tests/")
RESULTS: list[tuple[str, bool, str]] = []


def sh(cmd: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True, check=False)


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((name, ok, detail))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true", help="skip make check and the startup path")
    args = ap.parse_args()

    res = sh(f"{sys.executable} scripts/check_state.py")
    record("state files valid (check_state.py)", res.returncode == 0, res.stdout.strip())

    changed = [
        line[3:].split(" -> ")[-1]
        for line in sh("git status --porcelain --untracked-files=all").stdout.splitlines()
    ]
    code_changed = [f for f in changed if f.startswith(CODE)]
    progress_changed = "claude-progress.md" in changed
    record(
        "progress recorded for uncommitted code changes",
        not code_changed or progress_changed,
        f"code changed ({', '.join(code_changed[:4])}) but claude-progress.md was not updated"
        if code_changed and not progress_changed
        else "",
    )

    debug_hits = []
    for path in (ROOT / "app").rglob("*.py"):
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if DEBUG.match(line):
                debug_hits.append(f"{path.relative_to(ROOT)}:{n}: {line.strip()}")
    record("no debug code in app/", not debug_hits, "; ".join(debug_hits[:5]))

    candidates = sh("git ls-files --others --exclude-standard").stdout.splitlines() + changed
    stray = sorted({f for f in candidates if STRAY.search(f)})
    record("no stray files", not stray, ", ".join(stray[:8]))

    markers = sh("git grep -nE '^(<<<<<<<|>>>>>>>) ' -- ':!*.diff' ':!*.md'").stdout.strip()
    record("no merge-conflict markers", not markers, markers[:200])

    if not args.fast:
        res = sh("make -s check")
        tail = "\n".join((res.stdout + res.stderr).strip().splitlines()[-5:])
        record("make check green", res.returncode == 0, "" if res.returncode == 0 else tail)
        res = sh("make -s up")
        healthy = False
        try:
            with urllib.request.urlopen("http://localhost:8000/health", timeout=10) as r:  # noqa: S310
                healthy = r.status == 200
        except OSError as exc:
            res.stderr += str(exc)
        record("startup path: make up + /health", healthy, "" if healthy else res.stderr[-300:])

    width = max(len(n) for n, _, _ in RESULTS)
    for name, ok, detail in RESULTS:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {'' if ok else detail}")
    failed = [n for n, ok, _ in RESULTS if not ok]
    print(
        f"clean-state: {len(RESULTS) - len(failed)}/{len(RESULTS)} — "
        + (
            "clean, safe to hand off."
            if not failed
            else "NOT clean; fix before ending the session."
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
