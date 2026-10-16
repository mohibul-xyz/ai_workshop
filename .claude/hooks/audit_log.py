#!/usr/bin/env python3
"""PostToolUse(*): append every agent action to .claude/audit.log (JSONL).

Blocks are recorded by the guard hooks themselves (see _common.block), so the log shows both
what the agent did and what it was stopped from doing. Summarise with scripts/audit_report.py.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import _summarise, audit, read_event, tool_input  # noqa: E402


def main() -> None:
    event = read_event()
    response = event.get("tool_response")
    ok = None
    if isinstance(response, dict):
        if "success" in response:
            ok = bool(response["success"])
        elif "interrupted" in response:
            ok = not response["interrupted"]
    audit(
        {
            "event": event.get("hook_event_name", "PostToolUse"),
            "session": str(event.get("session_id", ""))[:8],
            "tool": event.get("tool_name"),
            "decision": "ran",
            "ok": ok,
            "input": _summarise(tool_input(event)),
        }
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
