#!/usr/bin/env python3
"""How much context does a session load before the agent does anything? (topic 10)

Counts what Claude Code loads at session start for a variant:
  * CLAUDE.md, plus every `@path` import, recursively (max depth 5)
  * the name + description of every skill (.claude/skills/*/SKILL.md) and subagent
    (.claude/agents/*.md) — those descriptions are always in context; bodies load on demand

Tokens come from the Anthropic token-counting endpoint (POST /v1/messages/count_tokens) when
ANTHROPIC_API_KEY is set, otherwise from a chars/4 estimate (marked "~"). Stdlib only, so the
host needs no SDK. Counts are model-specific: MODEL defaults to the benchmark's model.

Usage:
  python3 scripts/context_report.py                       # repo root
  python3 scripts/context_report.py --variant bloated     # stages/08-.../variants/<name>
  python3 scripts/context_report.py --all [--json]        # every variant, comparison table
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ROOT / "stages" / "08-context-optimization" / "variants"
MODEL = os.environ.get("MODEL", "claude-opus-5-5")
IMPORT_RE = re.compile(r"^@(\S+)\s*$", re.M)
FRONT_RE = re.compile(r"^---\n(.*?)\n---", re.S)


def count_tokens(text: str) -> tuple[int, bool]:
    """(tokens, exact). Exact via the API when a key is available, else chars/4."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key and text.strip():
        body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": text}]})
        req = urllib.request.Request(
            "https://api.anthropic.com/v1/messages/count_tokens",
            data=body.encode(),
            method="POST",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return int(json.load(resp)["input_tokens"]), True
        except (urllib.error.URLError, KeyError, ValueError) as exc:
            print(f"  (count_tokens failed: {exc}; using estimate)", file=sys.stderr)
    return max(1, len(text) // 4) if text else 0, False


def expand(path: Path, base: Path, depth: int = 0, seen: set[Path] | None = None) -> list[Path]:
    """CLAUDE.md and its @imports (paths relative to the repo root), recursively."""
    seen = seen if seen is not None else set()
    if depth > 5 or path in seen or not path.exists():
        return []
    seen.add(path)
    out = [path]
    for ref in IMPORT_RE.findall(path.read_text(encoding="utf-8")):
        out += expand(base / ref, base, depth + 1, seen)
    return out


def descriptions() -> str:
    parts = []
    for p in sorted([*ROOT.glob(".claude/skills/*/SKILL.md"), *ROOT.glob(".claude/agents/*.md")]):
        m = FRONT_RE.match(p.read_text(encoding="utf-8"))
        if m:
            fields = dict(line.split(":", 1) for line in m.group(1).splitlines() if ":" in line)
            parts.append(
                f"{fields.get('name', p.stem).strip()}: {fields.get('description', '').strip()}"
            )
    return "\n".join(parts)


def report(name: str, claude_md: Path) -> dict[str, object]:
    files = expand(claude_md, ROOT)
    rows = []
    for f in files:
        text = f.read_text(encoding="utf-8")
        tokens, exact = count_tokens(text)
        rel = f.relative_to(ROOT).as_posix()
        rows.append(
            {"file": rel, "lines": len(text.splitlines()), "tokens": tokens, "exact": exact}
        )
    desc = descriptions()
    d_tokens, d_exact = count_tokens(desc)
    rows.append(
        {
            "file": "(skill + agent descriptions)",
            "lines": len(desc.splitlines()),
            "tokens": d_tokens,
            "exact": d_exact,
        }
    )
    total = sum(int(str(r["tokens"])) for r in rows)
    return {
        "variant": name,
        "model": MODEL,
        "files": rows,
        "total_tokens": total,
        "exact": all(r["exact"] for r in rows),
    }


def print_report(rep: dict[str, object]) -> None:
    mark = "" if rep["exact"] else "~"
    print(
        f"\n== {rep['variant']}  (startup context, "
        f"{'count_tokens' if rep['exact'] else 'chars/4 estimate'}, {rep['model']})"
    )
    for r in rep["files"]:
        print(f"  {mark}{r['tokens']:>7}  {r['lines']:>5} lines  {r['file']}")
    print(f"  {mark}{rep['total_tokens']:>7}  total")


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--variant")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.all:
        targets = [(v.name, v / "CLAUDE.md") for v in sorted(VARIANTS.iterdir()) if v.is_dir()]
    elif args.variant:
        targets = [(args.variant, VARIANTS / args.variant / "CLAUDE.md")]
    else:
        targets = [("repo", ROOT / "CLAUDE.md")]
    reports = [report(n, p) for n, p in targets]

    if args.json:
        print(json.dumps(reports, indent=2))
        return 0
    for rep in reports:
        print_report(rep)
    if len(reports) > 1:
        base = max(int(r["total_tokens"]) for r in reports)
        print("\nVariant      startup tokens   vs largest")
        for r in reports:
            t = int(r["total_tokens"])
            print(f"  {r['variant']:<10} {t:>12}   {t / base:6.0%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
