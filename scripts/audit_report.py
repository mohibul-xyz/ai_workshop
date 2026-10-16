#!/usr/bin/env python3
"""Summarise .claude/audit.log (JSONL written by the audit_log and guard hooks).

Answers: which tools did the agent use, which commands were blocked and by which hook,
which files did it touch? Usage: python3 scripts/audit_report.py [.claude/audit.log] [--since ISO]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", nargs="?", default=str(ROOT / ".claude" / "audit.log"))
    ap.add_argument("--since", default="", help="only records with ts >= this ISO prefix")
    args = ap.parse_args()

    path = Path(args.log)
    if not path.exists():
        print(f"no audit log at {path} — run a Claude Code session in this repo first")
        return 0
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        if str(rec.get("ts", "")) >= args.since:
            records.append(rec)

    ran = [r for r in records if r.get("decision") == "ran"]
    blocked = [r for r in records if r.get("decision") == "block"]
    tools = Counter(str(r.get("tool")) for r in ran)
    files = Counter(
        str(r["input"].get("file_path", "")).replace(str(ROOT) + "/", "")
        for r in ran
        if r.get("tool") in {"Edit", "Write", "MultiEdit", "NotebookEdit"}
        and r.get("input", {}).get("file_path")
    )
    commands = Counter(
        str(r["input"].get("command", "")).split("\n")[0][:80]
        for r in ran
        if r.get("tool") == "Bash"
    )
    sessions = {r.get("session") for r in ran if r.get("session")}
    span = f"{records[0].get('ts')} → {records[-1].get('ts')}" if records else "-"

    print(f"Audit: {len(records)} records, {len(sessions)} session(s), {span}\n")
    print("Tools used:")
    for tool, n in tools.most_common():
        print(f"  {n:5}  {tool}")
    print(f"\nBlocked actions: {len(blocked)}")
    for r in blocked:
        what = r.get("input", {}).get("command") or r.get("input", {}).get("file_path") or ""
        print(
            f"  {r.get('ts')}  {r.get('hook') or r.get('event')}: {r.get('reason')}  [{what[:70]}]"
        )
    print(f"\nFiles touched: {len(files)}")
    for f, n in files.most_common(20):
        print(f"  {n:5}  {f}")
    print("\nMost frequent commands:")
    for c, n in commands.most_common(10):
        print(f"  {n:5}  {c}")
    failed = [r for r in ran if r.get("ok") is False]
    if failed:
        print(f"\nTool calls that reported failure: {len(failed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
