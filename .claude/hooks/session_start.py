#!/usr/bin/env python3
"""SessionStart: inject the harness state so a fresh session can 'continue' with no briefing.

stdout of a SessionStart hook is added to the agent's context (course L5/L6: read state first).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import PROJECT_DIR, git, read_event  # noqa: E402

MAX_PROGRESS_LINES = 25


def current_state_section(text: str) -> str:
    """The '## Current verified state' section of claude-progress.md (or the top of the file)."""
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if ln.lower().startswith("## current")), None)
    if start is None:
        return "\n".join(lines[:MAX_PROGRESS_LINES])
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return "\n".join(lines[start:end][:MAX_PROGRESS_LINES])


def feature_summary() -> list[str]:
    path = PROJECT_DIR / "feature_list.json"
    if not path.exists():
        return ["feature_list.json: MISSING — state subsystem not set up"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"feature_list.json: INVALID JSON ({exc}) — fix it first"]
    feats = data.get("features", data) if isinstance(data, dict) else data
    counts: dict[str, int] = {}
    for f in feats:
        counts[f.get("status", "?")] = counts.get(f.get("status", "?"), 0) + 1
    active = [f for f in feats if f.get("status") == "in_progress"]
    todo = sorted((f for f in feats if f.get("status") == "not_started"),
                  key=lambda f: f.get("priority", 99))
    out = ["Features: " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))]
    if active:
        f = active[0]
        out.append(f"ACTIVE feature: {f['id']} — {f.get('title', '')}")
        if f.get("notes"):
            out.append(f"  notes: {f['notes']}")
    elif todo:
        f = todo[0]
        out.append(f"No feature in progress. Next by priority: {f['id']} — {f.get('title', '')}")
    else:
        out.append("No feature in progress and nothing left not_started.")
    return out


def main() -> None:
    event = read_event()
    parts = ["=== TaskHub harness: session start (from .claude/hooks/session_start.py) ==="]
    if event.get("source"):
        parts.append(f"Session source: {event['source']}")
    parts += feature_summary()

    progress = PROJECT_DIR / "claude-progress.md"
    if progress.exists():
        parts += ["", "From claude-progress.md:", current_state_section(progress.read_text())]

    handoff = PROJECT_DIR / "session-handoff.md"
    if handoff.exists():
        text = handoff.read_text(encoding="utf-8").strip()
        parts += ["", "From session-handoff.md (first 15 lines):", *text.splitlines()[:15]]

    status = git("status", "--short").stdout.strip()
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    parts += ["", f"git branch: {branch or '?'}",
              "git status --short:", status or "(clean)",
              "", "Next: run ./init.sh (or make check) to confirm the baseline before editing."]
    print("\n".join(parts))


if __name__ == "__main__":
    main()
