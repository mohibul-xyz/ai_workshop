#!/usr/bin/env python3
"""PreToolUse(Bash): block destructive or exfiltrating shell commands.

Permissions match *patterns* of the whole command; this hook inspects the command text
with code, so it also catches `cd x && rm -rf y`, `rm -fr`, `sh -c "..."`, flag reordering, etc.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _common import allow, block, read_event, tool_input  # noqa: E402

HOOK = "guard_bash"

# (regex, what, why, instead)
RULES: list[tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(r"\brm\s+(-[a-zA-Z]*r[a-zA-Z]*f|-[a-zA-Z]*f[a-zA-Z]*r|(-\S+\s+)*-r\b.*\s-f\b|"
                   r"(-\S+\s+)*-f\b.*\s-r\b|--recursive\b.*--force|--force\b.*--recursive)"),
        "recursive force delete (rm -rf)",
        "it deletes files irreversibly, outside git's safety net",
        "delete specific files with `git rm <file>` or plain `rm <file>`; ask a human for bulk deletes",
    ),
    (
        re.compile(r"\bgit\s+reset\s+.*--hard\b|\bgit\s+reset\s+--hard\b"),
        "git reset --hard",
        "it silently throws away uncommitted work",
        "use `git stash` to set work aside, or `git restore <file>` for one file",
    ),
    (
        re.compile(r"\bgit\s+push\b.*(\s--force\b|\s-f\b|\s--force-with-lease\b|\s\+\S)"),
        "force push",
        "it rewrites shared history",
        "push normally; if history must be rewritten, stop and ask a human",
    ),
    (
        re.compile(r"\bgit\s+(clean\s+-[a-zA-Z]*f|checkout\s+--\s+\.|restore\s+\.)"),
        "bulk discard of working-tree changes",
        "it destroys uncommitted work",
        "restore individual files you are sure about, or `git stash`",
    ),
    (
        re.compile(r"\b(drop\s+(table|database|schema)|truncate(\s+table)?\s+\w)", re.IGNORECASE),
        "DROP / TRUNCATE SQL",
        "it destroys data; schema changes go through migrations, and data loss needs a human",
        "write a migration with the `write-migration` skill; for test data rely on the "
        "rolled-back test transaction",
    ),
    (
        re.compile(r"\bdocker[\s-]compose\b.*\bdown\b.*(\s-v\b|--volumes\b)"),
        "docker compose down -v",
        "it deletes the Postgres volume (all dev data)",
        "use `make down` (keeps the volume); the test DB is reset per test automatically",
    ),
    (
        re.compile(r"\bdocker\s+(volume\s+(rm|prune)|system\s+prune)"),
        "docker volume/system prune",
        "it deletes database volumes and caches for every project on this machine",
        "use `make down`; ask a human to prune",
    ),
    (
        re.compile(r"\balembic\b.*\bdowngrade\s+(base|-\d{2,})"),
        "alembic downgrade base / many steps",
        "it drops every table in the database",
        "test reversibility with `make migrate-check` (uses a throwaway database)",
    ),
    (
        re.compile(r"\b(curl|wget)\b[^|]*\|\s*(sudo\s+)?(ba|z|da)?sh\b"),
        "piping a download into a shell",
        "it executes unreviewed remote code",
        "add dependencies to pyproject.toml and ask a human to rebuild the image",
    ),
    (
        re.compile(r"(^|[\s;&|(])(cat|less|more|head|tail|bat|nl|strings|xxd|od|grep|rg|sed|awk|"
                   r"source|\.)\s+([^|;&]*[\s/'\"])?\.env(?!\.example\b)(\.[\w.-]+)?\b"),
        "reading a .env file",
        "it contains secrets the agent must never see",
        "read `.env.example` for variable names; ask a human for values",
    ),
    (
        re.compile(r"(^|[\s/'\"])(benchmarks/[^\s]*/)?hidden/"),
        "accessing hidden benchmark tests",
        "hidden tests score the benchmark; reading them invalidates the result",
        "work from benchmarks/*/task.md and docs/testing-standards.md",
    ),
    (
        re.compile(r"(^|[\s;&|])sudo\s"),
        "sudo",
        "the agent never needs root on the host",
        "use the Makefile targets, which run inside containers",
    ),
    (
        re.compile(r"\bchmod\s+(-R\s+)?777\b|\bchown\s+-R\b"),
        "recursive permission change",
        "it can break the repo and the containers' bind mounts",
        "change permissions on one specific file, or ask a human",
    ),
]

# `bash -c "..."`, `sh -c '...'`, `eval "..."`: inspect the inner string too.
WRAPPER = re.compile(r"""\b(?:ba|z|da)?sh\s+-c\s+(['"])(.*?)\1|\beval\s+(['"])(.*?)\3""", re.S)


def check(command: str) -> tuple[str, str, str] | None:
    candidates = [command]
    candidates += [m.group(2) or m.group(4) or "" for m in WRAPPER.finditer(command)]
    for text in candidates:
        for rx, what, why, instead in RULES:
            if rx.search(text):
                return what, why, instead
    return None


def main() -> None:
    event = read_event()
    if event.get("tool_name") != "Bash":
        allow()
    command = str(tool_input(event).get("command", ""))
    hit = check(command)
    if hit:
        what, why, instead = hit
        block(HOOK, event, f"{what} in `{command[:200]}`", why, instead)
    allow()


if __name__ == "__main__":
    main()
