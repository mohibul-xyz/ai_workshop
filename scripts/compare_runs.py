#!/usr/bin/env python3
"""Turn runs/bench-*.json into the topic-10 results table (mean and min–max per variant).

Usage: python3 scripts/compare_runs.py [--glob 'runs/bench-*.json'] [--append-scorecard]
       [--include-dry]   (dry-run records are skipped unless asked for)
"""

from __future__ import annotations

import argparse
import glob
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = ["bloated", "router", "hygiene", "no-instructions", "no-verification", "no-state"]
LABELS = {"bloated": "A. Bloated", "router": "B. Router", "hygiene": "C. Router + hygiene"}


def input_tokens(rec: dict[str, object]) -> int:
    u = rec.get("usage") or {}
    assert isinstance(u, dict)
    return sum(
        int(u.get(k) or 0)
        for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")
    )


def num(rec: dict[str, object], key: str, scale: float = 1.0) -> float:
    value = rec.get(key)
    return float(value) / scale if isinstance(value, int | float) else 0.0


def cell(values: list[float], fmt: str) -> str:
    if not values:
        return "—"
    mean = statistics.fmean(values)
    if len(values) == 1 or min(values) == max(values):
        return fmt.format(mean)
    return f"{fmt.format(mean)} ({fmt.format(min(values))}–{fmt.format(max(values))})"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--glob", default=str(ROOT / "runs" / "bench-*.json"))
    ap.add_argument("--append-scorecard", action="store_true")
    ap.add_argument("--include-dry", action="store_true")
    args = ap.parse_args()

    recs = []
    for path in sorted(glob.glob(args.glob)):
        if path.endswith(".agent.json"):
            continue
        rec = json.loads(Path(path).read_text())
        if rec.get("dry_run") and not args.include_dry:
            continue
        recs.append(rec)
    if not recs:
        print(
            "no benchmark records — run scripts/run_benchmark.sh first "
            "(or --include-dry for dry-run fixtures)"
        )
        return 1

    groups: dict[str, list[dict[str, object]]] = {}
    for r in recs:
        groups.setdefault(str(r["variant"]), []).append(r)
    names = sorted(groups, key=lambda v: (ORDER.index(v) if v in ORDER else 99, v))

    dry = any(r.get("dry_run") for r in recs)
    lines = [
        "| Variant | Runs | Hidden tests passed | Verify layers green | Turns | Input tokens"
        " | Cost (USD) | Duration (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for v in names:
        rs = groups[v]
        hidden = [100 * num(r, "hidden_passed") / (num(r, "hidden_total") or 7) for r in rs]
        lines.append(
            f"| {LABELS.get(v, v)} | {len(rs)} | {cell(hidden, '{:.0f}%')} "
            f"| {cell([num(r, 'verify_layers_green') for r in rs], '{:.1f}')}/3 "
            f"| {cell([num(r, 'num_turns') for r in rs], '{:.0f}')} "
            f"| {cell([float(input_tokens(r)) for r in rs], '{:,.0f}')} "
            f"| {cell([num(r, 'total_cost_usd') for r in rs], '{:.2f}')} "
            f"| {cell([num(r, 'duration_ms', 1000) for r in rs], '{:.0f}')} |"
        )
    table = "\n".join(lines)
    note = (
        "\n\n_Illustrative numbers from dry-run fixtures — replace with real runs._" if dry else ""
    )
    print(table + note)

    if args.append_scorecard:
        sc = ROOT / "experiments" / "scorecard.md"
        with sc.open("a", encoding="utf-8") as fh:
            fh.write(f"\n### Stage 8 results ({len(recs)} runs)\n\n{table}{note}\n")
        print(f"\nappended to {sc.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
