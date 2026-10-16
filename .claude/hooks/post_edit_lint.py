#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): run ruff on the edited Python file, feed errors back.

The edit already happened, so exit 2 does not undo it — it puts ruff's output in front of
the agent immediately (fast feedback, course L9), instead of at `make check` time.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PROJECT_DIR, allow, read_event, rel_path, tool_input  # noqa: E402

SKIP_PREFIXES = ("stages/00-baseline-reading-ai-code/ai_written/", "stages/08-context-optimization/")


def find_ruff() -> str | None:
    venv = PROJECT_DIR / ".venv" / "bin" / "ruff"
    if venv.exists():
        return str(venv)
    return shutil.which("ruff")


def main() -> None:
    event = read_event()
    rel = rel_path(str(tool_input(event).get("file_path", "")))
    if not rel.endswith(".py") or rel.startswith(SKIP_PREFIXES):
        allow()
    path = PROJECT_DIR / rel
    if not path.exists():
        allow()
    ruff = find_ruff()
    if ruff is None:
        print("post_edit_lint: ruff not found (run `make setup`); skipping fast lint. "
              "`make lint` still checks this file.")
        allow()
    res = subprocess.run(  # noqa: S603 - fixed argv
        [ruff, "check", "--quiet", "--output-format", "concise", str(path)],
        cwd=PROJECT_DIR, capture_output=True, text=True, check=False,
    )
    fmt = subprocess.run(  # noqa: S603
        [ruff, "format", "--check", "--quiet", str(path)],
        cwd=PROJECT_DIR, capture_output=True, text=True, check=False,
    )
    problems = res.stdout.strip()
    if fmt.returncode != 0:
        problems += f"\n{rel}: not ruff-formatted (fix with `.venv/bin/ruff format {rel}`)"
    if problems.strip():
        print(f"ruff found problems in {rel} — fix them before moving on:\n{problems.strip()}",
              file=sys.stderr)
        sys.exit(2)
    allow()


if __name__ == "__main__":
    main()
