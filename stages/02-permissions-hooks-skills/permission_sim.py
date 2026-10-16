#!/usr/bin/env python3
"""Permission simulator: how would Claude Code decide each agent action under these rules?

A teaching model of Claude Code's permission evaluation (see docs/version-notes.md):

  1. deny rules are checked first  -> "deny"   (deny always wins)
  2. then ask rules                -> "ask"
  3. then allow rules              -> "allow"
  4. no rule matched               -> default: read-only tools "allow", everything else "ask"

Rule forms:
  Tool                 every call of that tool (e.g. "WebFetch")
  Bash(make test)      exact command
  Bash(git diff *)     prefix with wildcard; also matches the bare command "git diff"
  Bash(npm run test:*) legacy prefix form, same meaning as "npm run test *"
  Read(./path/**)      gitignore-style path glob, relative to the project root.
                       Read rules also cover Grep/Glob. Edit rules cover Edit/Write/MultiEdit/
                       NotebookEdit.

Important: Read(...) rules do NOT apply to Bash. `Read(./.env)` blocks the Read tool,
but `cat .env` is a Bash call — deny it with a Bash rule too (and a hook, for variants).

Compound commands (`a && b`, `a; b`, `a | b`) are split; every part must be allowed,
any denied part denies the whole command.

Usage:
  python3 permission_sim.py [--settings .claude/settings.json] [--scenarios scenarios.json]
  python3 permission_sim.py --explain 'Bash' 'git push -f origin main'
  python3 permission_sim.py --explain 'Read' '.env'
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
READ_TOOLS = {"Read", "Grep", "Glob", "LS"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SPLIT_RE = re.compile(r"\s*(?:&&|\|\||;|\|)\s*")


@dataclass
class Decision:
    decision: str
    rule: str | None


def parse_rule(rule: str) -> tuple[str, str | None]:
    m = re.fullmatch(r"(\w+)(?:\((.*)\))?", rule.strip())
    if not m:
        raise ValueError(f"unparseable rule: {rule!r}")
    return m.group(1), m.group(2)


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """gitignore-ish: ** = any depth (incl. none), * = within one segment, ? = one char."""
    p = pattern[2:] if pattern.startswith("./") else pattern.lstrip("/")
    out = ""
    i = 0
    while i < len(p):
        if p.startswith("**/", i):
            out += r"(?:.*/)?"
            i += 3
        elif p.startswith("**", i):
            out += r".*"
            i += 2
        elif p[i] == "*":
            out += r"[^/]*"
            i += 1
        elif p[i] == "?":
            out += r"[^/]"
            i += 1
        else:
            out += re.escape(p[i])
            i += 1
    return re.compile(out + r"$")


def bash_matches(pattern: str, command: str) -> bool:
    command = " ".join(command.split())
    if pattern.endswith(":*"):
        pattern = pattern[:-2] + " *"
    if pattern.endswith(" *") and command == pattern[:-2]:
        return True
    rx = "".join(".*" if ch == "*" else re.escape(ch) for ch in pattern)
    return re.fullmatch(rx, command) is not None


def normalise_path(path: str) -> str:
    p = path.strip()
    root = str(ROOT) + "/"
    if p.startswith(root):
        p = p[len(root) :]
    return p[2:] if p.startswith("./") else p.lstrip("/")


def rule_matches(rule: str, tool: str, arg: str) -> bool:
    rtool, spec = parse_rule(rule)
    if rtool == "Read":
        applies = tool in READ_TOOLS
    elif rtool == "Edit":
        applies = tool in EDIT_TOOLS
    else:
        applies = rtool == tool
    if not applies:
        return False
    if spec is None or spec in ("", "*"):
        return True
    if rtool == "Bash":
        return bash_matches(spec, arg)
    if rtool in ("Read", "Edit"):
        return glob_to_regex(spec).match(normalise_path(arg)) is not None
    return spec == arg


def decide_single(perms: dict[str, list[str]], tool: str, arg: str) -> Decision:
    for kind in ("deny", "ask", "allow"):
        for rule in perms.get(kind, []):
            if rule_matches(rule, tool, arg):
                return Decision(kind, rule)
    return Decision("allow" if tool in READ_TOOLS else "ask", None)


def decide(perms: dict[str, list[str]], tool: str, arg: str) -> Decision:
    if tool != "Bash":
        return decide_single(perms, tool, arg)
    whole = decide_single(perms, tool, arg)
    if whole.decision == "deny":
        return whole
    parts = [p for p in SPLIT_RE.split(arg) if p.strip()]
    if len(parts) <= 1:
        return whole
    results = [decide_single(perms, tool, p) for p in parts]
    for kind in ("deny", "ask"):
        hit = next((r for r in results if r.decision == kind), None)
        if hit:
            return hit
    return Decision("allow", "; ".join(r.rule or "-" for r in results))


def load_perms(settings: Path) -> dict[str, list[str]]:
    data = json.loads(settings.read_text(encoding="utf-8"))
    perms = data.get("permissions", {})
    return {k: list(perms.get(k, [])) for k in ("allow", "ask", "deny")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    ap.add_argument("--settings", default=str(ROOT / ".claude" / "settings.json"))
    ap.add_argument("--scenarios", default=str(HERE / "scenarios.json"))
    ap.add_argument("--explain", nargs=2, metavar=("TOOL", "ARG"))
    ap.add_argument("-v", "--verbose", action="store_true", help="show matching rule for every row")
    args = ap.parse_args()

    settings = Path(args.settings)
    if not settings.exists():
        print(f"settings file not found: {settings}")
        return 1
    perms = load_perms(settings)

    if args.explain:
        d = decide(perms, *args.explain)
        print(
            f"{args.explain[0]}({args.explain[1]}) -> {d.decision.upper()}  "
            f"(rule: {d.rule or 'default'})"
        )
        return 0

    scenarios = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))["scenarios"]
    passed = 0
    print(f"settings: {settings}\n")
    print(f"{'#':>2}  {'expected':8} {'got':8}  action")
    for i, sc in enumerate(scenarios, 1):
        d = decide(perms, sc["tool"], sc["input"])
        ok = d.decision == sc["expected"]
        passed += ok
        mark = "ok " if ok else "XX "
        print(f"{i:>2}  {sc['expected']:8} {d.decision:8}  {mark}{sc['tool']}({sc['input']})")
        if not ok or args.verbose:
            print(f"      rule: {d.rule or 'default (no rule matched)'}")
            if not ok:
                print(f"      why expected: {sc['why']}")
    total = len(scenarios)
    print(f"\nScore: {passed}/{total}")
    if passed == total:
        print("All decisions match the permission matrix. Confirm live with /permissions.")
        return 0
    print("Edit the rules in the settings file until every decision matches.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
