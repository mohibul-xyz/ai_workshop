#!/usr/bin/env python3
"""PreToolUse(Edit|Write|MultiEdit|NotebookEdit): protect files the agent must not change.

* Committed migrations are immutable (new revision instead).
* .env* / secrets/** hold secrets.
* Harness files (.claude/settings.json, .claude/hooks/**) are the guardrails themselves.
* Hidden benchmark tests score the agent.
"""

from __future__ import annotations

import fnmatch
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import allow, block, git, read_event, rel_path, tool_input  # noqa: E402

HOOK = "guard_files"
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def is_committed(rel: str) -> bool:
    return bool(git("ls-files", "--error-unmatch", rel).returncode == 0)


def check(rel: str) -> tuple[str, str, str] | None:
    name = rel.rsplit("/", 1)[-1]
    if (name == ".env" or name.startswith(".env.")) and name != ".env.example":
        return (
            "editing a .env file",
            "it holds secrets and per-machine config",
            "document new variables in `.env.example` and tell the human to set them",
        )
    if rel.startswith("secrets/"):
        return ("editing secrets/", "secrets are managed by humans", "ask a human")
    if (
        rel == ".claude/settings.json"
        or fnmatch.fnmatch(rel, ".claude/hooks/*")
        or rel.startswith(".claude/hooks/")
    ):
        return (
            "editing harness guardrails",
            "the agent must not loosen its own guardrails",
            "describe the change you want and ask a human to make it",
        )
    if "/hidden/" in f"/{rel}" and rel.startswith("benchmarks/"):
        return (
            "touching hidden benchmark tests",
            "they score your work",
            "work from benchmarks/*/task.md",
        )
    if fnmatch.fnmatch(rel, "migrations/versions/*.py") and is_committed(rel):
        return (
            f"editing committed migration {rel}",
            "applied migrations are history; editing them desynchronises every database "
            "that already ran them",
            "create a new revision: use the `write-migration` skill (`make migration name=<slug>`)",
        )
    return None


def main() -> None:
    event = read_event()
    if event.get("tool_name") not in EDIT_TOOLS:
        allow()
    ti = tool_input(event)
    rel = rel_path(str(ti.get("file_path") or ti.get("notebook_path") or ""))
    hit = check(rel)
    if hit:
        what, why, instead = hit
        block(HOOK, event, what, why, instead)
    allow()


if __name__ == "__main__":
    main()
