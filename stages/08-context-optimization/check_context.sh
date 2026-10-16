#!/usr/bin/env bash
# make lab-context — checkpoint for topic 10 (no API spend).
#  1. variants are in sync with the live CLAUDE.md
#  2. startup-context report: bloated loads far more than router / hygiene
#  3. dry-run benchmark A/B/C x 3 → comparison table (illustrative numbers)
#  4. E2E=1: one real benchmark run with a fake agent (applies the reference patch) — proves the
#     clone → variant → hidden tests → verify → JSON pipeline; expects 7/7 hidden, 3/3 layers
set -uo pipefail
cd "$(dirname "$0")/../.."
fail=0
python3 stages/08-context-optimization/make_variants.py --check || fail=1

python3 - <<'PY' || fail=1
import json, subprocess, sys
reps = {r["variant"]: r for r in json.loads(subprocess.run(
    [sys.executable, "scripts/context_report.py", "--all", "--json"],
    capture_output=True, text=True, check=True).stdout)}
t = {k: v["total_tokens"] for k, v in reps.items()}
ok = t["bloated"] > 3 * t["router"] and t["bloated"] > 3 * t["hygiene"]
how = "count_tokens" if all(r["exact"] for r in reps.values()) else "chars/4 estimate"
print(f"{'OK  ' if ok else 'FAIL'} startup context ({how}): bloated={t['bloated']}  "
      f"router={t['router']}  hygiene={t['hygiene']}  (hygiene saves at run time, not start)")
sys.exit(0 if ok else 1)
PY

OUT="runs/lab-context-$(date +%Y%m%dT%H%M%S)-$$"
for v in bloated router hygiene; do
  BENCH_OUT="$OUT" DRY_RUN=1 RUNS=3 bash scripts/run_benchmark.sh "$v" > /dev/null || fail=1
done
echo "OK   dry-run benchmark table ($OUT):"
python3 scripts/compare_runs.py --include-dry --glob "$OUT/bench-*.json" | sed 's/^/     /' || fail=1

if [[ "${E2E:-0}" == "1" ]]; then
  BENCH_OUT="$OUT/e2e" RUNS=1 CLAUDE_BIN="$PWD/stages/08-context-optimization/fake_claude.sh" \
    bash scripts/run_benchmark.sh router > "$OUT/e2e.log" 2>&1
  python3 - "$OUT/e2e" <<'PY' || fail=1
import glob, json, sys
recs = [json.load(open(p)) for p in glob.glob(sys.argv[1] + "/bench-*.json") if not p.endswith(".agent.json")]
r = recs[0] if recs else {}
ok = r.get("hidden_passed") == 7 and r.get("verify_layers_green") == 3
print(f"{'OK  ' if ok else 'FAIL'} e2e pipeline with fake agent: hidden {r.get('hidden_passed')}/7, "
      f"verify layers {r.get('verify_layers_green')}/3")
sys.exit(0 if ok else 1)
PY
fi
exit $fail
