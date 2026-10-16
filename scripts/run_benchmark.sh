#!/usr/bin/env bash
# run_benchmark.sh — run benchmark B1 under one context variant or one ablation (topics 10, L2).
#
#   scripts/run_benchmark.sh <bloated|router|hygiene>            # context variants A/B/C
#   scripts/run_benchmark.sh --ablate <instructions|verification|state>
#
# Each run: fresh clone of BASE (default HEAD) → apply variant/ablation → claude -p "<B1 prompt>"
# → restore the scoring tools → copy in hidden tests → score (hidden tests + verify.sh layers)
# → runs/bench-<label>-<id>-<n>.json. Then: python3 scripts/compare_runs.py
#
# Env: BENCH_OUT=runs  RUNS=3  BUDGET_USD=2  BASE=HEAD  TURNS_FLAG=--max-turns MAX_TURNS=40  KEEP=0
#      CLAUDE_BIN=claude (stages/08-context-optimization/fake_claude.sh: free end-to-end test)
#      DRY_RUN=1  (replay stages/08-context-optimization/fixtures/bench-<label>.json; no API)
set -uo pipefail
cd "$(dirname "$0")/.."

[[ $# -ge 1 ]] || { sed -n '2,13p' "$0"; exit 1; }
if [[ "$1" == "--ablate" ]]; then
  MODE=ablate; WHAT="${2:?--ablate needs instructions|verification|state}"; LABEL="no-$WHAT"
else
  MODE=variant; WHAT="$1"; LABEL="$1"
fi
case "$WHAT" in bloated|router|hygiene|instructions|verification|state) ;; *)
  echo "unknown variant/ablation: $WHAT"; exit 1 ;; esac

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
RUNS="${RUNS:-3}"; BUDGET_USD="${BUDGET_USD:-2}"; BASE="${BASE:-HEAD}"; KEEP="${KEEP:-0}"
TURNS_FLAG="${TURNS_FLAG---max-turns}"; MAX_TURNS="${MAX_TURNS:-40}"; DRY_RUN="${DRY_RUN:-0}"
VARIANTS=stages/08-context-optimization/variants
FIXTURES=stages/08-context-optimization/fixtures
PROMPT="$(sed -n 's/^> //p' benchmarks/B1-project-stats/task.md | head -1)"
ID="$(date +%Y%m%dT%H%M%S)-$$"
ENVS=(COMPOSE_PROJECT_NAME=taskhub-bench API_PORT=8200 DB_PORT=55433 BASE_URL=http://localhost:8200)
OUTDIR="${BENCH_OUT:-runs}"
mkdir -p "$OUTDIR"

apply() {  # apply <clone dir>
  local d="$1"
  case "$WHAT" in
    bloated|router|hygiene)
      cp "$VARIANTS/$WHAT/CLAUDE.md" "$d/CLAUDE.md"; cp "$d/CLAUDE.md" "$d/AGENTS.md"
      if [[ -f "$VARIANTS/$WHAT/settings.overlay.json" ]]; then
        python3 - "$d/.claude/settings.json" "$VARIANTS/$WHAT/settings.overlay.json" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1])); o = json.load(open(sys.argv[2]))
s.setdefault("permissions", {}).setdefault("deny", []).extend(o["permissions"]["deny"])
json.dump(s, open(sys.argv[1], "w"), indent=2)
EOF
      fi ;;
    instructions) rm -rf "$d/CLAUDE.md" "$d/AGENTS.md" "$d/docs" ;;
    verification)  # no stop gate, no verify script for the agent (scoring restores them)
      python3 - "$d/.claude/settings.json" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1])); s.get("hooks", {}).pop("Stop", None)
json.dump(s, open(sys.argv[1], "w"), indent=2)
EOF
      rm -f "$d/scripts/verify.sh" "$d/scripts/smoke_e2e.py" ;;
    state)
      rm -f "$d/feature_list.json" "$d/claude-progress.md" "$d/session-handoff.md"
      python3 - "$d/.claude/settings.json" <<'EOF'
import json, sys
s = json.load(open(sys.argv[1])); s.get("hooks", {}).pop("SessionStart", None)
json.dump(s, open(sys.argv[1], "w"), indent=2)
EOF
      ;;
  esac
}

score() {  # score <clone dir> <agent json> <out json> <run n>
  local d="$1" agent="$2" out="$3" n="$4" hidden="0/7" layers=0
  # Scoring always uses the harness's own tools, whatever the agent was given.
  git -C "$d" checkout -q "$BASE" -- scripts/verify.sh scripts/smoke_e2e.py Makefile 2>/dev/null
  mkdir -p "$d/tests/_b1" && cp benchmarks/B1-project-stats/hidden/test_stats.py "$d/tests/_b1/test_b1_hidden.py"
  local res; res="$(cd "$d" && env "${ENVS[@]}" make -s up >/dev/null 2>&1; \
    env "${ENVS[@]}" docker compose --profile tools run --rm -T tools pytest -o addopts="" -q tests/_b1 2>&1 | tail -1)"
  hidden="$(python3 - "$res" <<'EOF'
import re, sys
s = sys.argv[1]
g = lambda w: sum(int(x) for x in re.findall(r"(\d+) " + w, s))
p = g("passed")
print(f"{p}/{p + g('failed') + g('errors?') or 7}")
EOF
)"
  rm -rf "$d/tests/_b1"
  local vlog; vlog="$(cd "$d" && env "${ENVS[@]}" bash scripts/verify.sh 2>&1 | grep -E '^VERIFY:' | tail -1)"
  layers=$(grep -o '=pass' <<< "$vlog" | wc -l)
  python3 - "$agent" "$out" "$LABEL" "$n" "$hidden" "$layers" "$vlog" <<'EOF'
import json, sys
agent, out, label, n, hidden, layers, vlog = sys.argv[1:]
a = json.load(open(agent))
p, t = (int(x) for x in hidden.split("/"))
json.dump({"variant": label, "run": int(n), "hidden_passed": p, "hidden_total": t or 7,
           "verify_layers_green": int(layers), "verify": vlog,
           "num_turns": a.get("num_turns"), "total_cost_usd": a.get("total_cost_usd"),
           "duration_ms": a.get("duration_ms"), "usage": a.get("usage", {}),
           "is_error": a.get("is_error"), "dry_run": False}, open(out, "w"), indent=2)
EOF
}

for ((n = 1; n <= RUNS; n++)); do
  OUT="$OUTDIR/bench-${LABEL}-${ID}-${n}.json"
  if [[ "$DRY_RUN" == "1" ]]; then
    python3 - "$FIXTURES/bench-${LABEL}.json" "$OUT" "$n" <<'EOF'
import json, sys
runs = json.load(open(sys.argv[1]))["runs"]; n = int(sys.argv[3])
rec = dict(runs[(n - 1) % len(runs)], run=n, dry_run=True)
json.dump(rec, open(sys.argv[2], "w"), indent=2)
EOF
    echo "[bench] $LABEL run $n/$RUNS (dry) → $OUT"
    continue
  fi
  DIR=".worktrees/bench-${LABEL}-${ID}-${n}"
  git clone --quiet --no-hardlinks . "$DIR" && git -C "$DIR" checkout -q "$BASE"
  apply "$DIR"
  echo "[bench] $LABEL run $n/$RUNS: claude -p in $DIR (budget \$$BUDGET_USD)"
  flags=(-p "$PROMPT" --output-format json --permission-mode acceptEdits --max-budget-usd "$BUDGET_USD")
  [[ -n "$TURNS_FLAG" ]] && flags+=("$TURNS_FLAG" "$MAX_TURNS")
  (cd "$DIR" && env "${ENVS[@]}" "$CLAUDE_BIN" "${flags[@]}") > "$OUTDIR/bench-${LABEL}-${ID}-${n}.agent.json" 2> /dev/null
  score "$DIR" "$OUTDIR/bench-${LABEL}-${ID}-${n}.agent.json" "$OUT" "$n"
  python3 - "$OUT" <<'EOF'
import json, sys
d = json.load(open(sys.argv[1]))
print(f"[bench] scored {sys.argv[1]}: hidden {d['hidden_passed']}/{d['hidden_total']}, "
      f"verify layers {d['verify_layers_green']}/3, ${d['total_cost_usd']}")
EOF
  (cd "$DIR" && env "${ENVS[@]}" docker compose down >/dev/null 2>&1) || true
  [[ "$KEEP" == "1" ]] || rm -rf "$DIR"
done
echo "[bench] done. Compare: python3 scripts/compare_runs.py --glob '$OUTDIR/bench-*.json'"
