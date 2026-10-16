#!/usr/bin/env python3
"""PostToolUse(Edit|Write|MultiEdit): when feature_list.json changes, validate it immediately.

Enforces WIP=1 and "no passing without evidence" at the moment the agent edits state
(course L7/L8), instead of trusting it to remember the rule.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PROJECT_DIR, allow, read_event, rel_path, tool_input  # noqa: E402


def main() -> None:
    event = read_event()
    rel = rel_path(str(tool_input(event).get("file_path", "")))
    if rel != "feature_list.json":
        allow()
    res = subprocess.run(  # noqa: S603 - fixed argv
        [sys.executable, str(PROJECT_DIR / "scripts" / "check_state.py")],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        print(
            "feature_list.json is now invalid — fix it before continuing:\n"
            + (res.stdout + res.stderr).strip()
            + "\nRules: at most one feature in_progress (WIP=1); 'passing' needs evidence "
            "that exists (e.g. runs/verify-*.log).",
            file=sys.stderr,
        )
        sys.exit(2)
    allow()


if __name__ == "__main__":
    main()
