"""Shared helpers for TaskHub harness hooks. Stdlib only — hooks run on the host.

Claude Code hook protocol (see docs/version-notes.md):
  * The tool call arrives as JSON on stdin:
      {"hook_event_name": "PreToolUse", "tool_name": "Bash",
       "tool_input": {"command": "..."}, "cwd": "...", "session_id": "...", ...}
  * exit 0  -> allow / continue (stdout is shown in the transcript; for SessionStart it is
               added to the agent's context)
  * exit 2  -> BLOCK; stderr is fed back to the agent so it can correct course
  * other   -> non-blocking error shown to the user

Messages are written FOR THE AGENT: what was blocked, why, and what to do instead.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, NoReturn

PROJECT_DIR = Path(os.environ.get("CLAUDE_PROJECT_DIR") or Path(__file__).resolve().parents[2])
AUDIT_LOG = PROJECT_DIR / ".claude" / "audit.log"


def read_event() -> dict[str, Any]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def tool_input(event: dict[str, Any]) -> dict[str, Any]:
    ti = event.get("tool_input") or {}
    return ti if isinstance(ti, dict) else {}


def rel_path(file_path: str) -> str:
    """Path relative to the project root, with forward slashes ('' if outside)."""
    if not file_path:
        return ""
    p = Path(file_path)
    if not p.is_absolute():
        p = PROJECT_DIR / p
    try:
        return p.resolve().relative_to(PROJECT_DIR.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def audit(record: dict[str, Any]) -> None:
    """Append one JSON line to .claude/audit.log; never let auditing break the agent."""
    if os.environ.get("HARNESS_AUDIT", "1") == "0":
        return
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **record}
        with AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record, sort_keys=True) + "\n")
    except OSError:
        pass


def block(hook: str, event: dict[str, Any], what: str, why: str, instead: str) -> NoReturn:
    """Block the tool call (exit 2) with an actionable message for the agent."""
    msg = f"BLOCKED by {hook}: {what}\nWhy: {why}\nDo instead: {instead}"
    audit(
        {
            "event": event.get("hook_event_name", "PreToolUse"),
            "tool": event.get("tool_name"),
            "decision": "block",
            "hook": hook,
            "reason": what,
            "input": _summarise(tool_input(event)),
        }
    )
    print(msg, file=sys.stderr)
    sys.exit(2)


def allow() -> NoReturn:
    sys.exit(0)


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        ["git", *args], cwd=PROJECT_DIR, capture_output=True, text=True, check=False
    )


def _summarise(ti: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in ("command", "file_path", "path", "pattern", "url", "description", "subagent_type"):
        if key in ti:
            val = str(ti[key])
            out[key] = val if len(val) <= 300 else val[:300] + "…"
    return out
