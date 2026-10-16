#!/usr/bin/env python3
"""Stop: "no victory without green" (course L9).

If the working tree has code changes (app/, migrations/, tests/) and `make check` fails, the
agent is not allowed to stop: the failure is sent back as the reason to keep working.

Loop safety:
  * if `stop_hook_active` is true (we already blocked once this turn), allow the stop;
  * only gate when code actually changed;
  * HARNESS_STOP_GATE=0 disables it (e.g. for ablation runs).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PROJECT_DIR, audit, git, read_event  # noqa: E402

CODE_PREFIXES = ("app/", "migrations/", "tests/")
CHECK_CMD = os.environ.get("HARNESS_STOP_CHECK", "make check")
TAIL = 40


def changed_code_files() -> list[str]:
    out = git("status", "--porcelain", "--untracked-files=all").stdout
    files = [line[3:].split(" -> ")[-1] for line in out.splitlines() if len(line) > 3]
    return [f for f in files if f.startswith(CODE_PREFIXES)]


def main() -> None:
    event = read_event()
    if os.environ.get("HARNESS_STOP_GATE", "1") == "0" or event.get("stop_hook_active"):
        sys.exit(0)
    changed = changed_code_files()
    if not changed:
        sys.exit(0)
    res = subprocess.run(  # noqa: S602 - command is configured by the harness, not the agent
        CHECK_CMD,
        shell=True,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0:
        sys.exit(0)
    tail = "\n".join((res.stdout + res.stderr).strip().splitlines()[-TAIL:])
    reason = (
        f"You changed code ({', '.join(changed[:5])}{'…' if len(changed) > 5 else ''}) "
        f"but `{CHECK_CMD}` is failing, so the work is not done. Fix the failures below, "
        "rerun `make check`, and only then finish. If you are blocked and need a human, "
        "say so explicitly and record it in session-handoff.md.\n\n" + tail
    )
    audit({"event": "Stop", "decision": "block", "hook": "stop_gate", "reason": "make check red"})
    print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    main()
