#!/usr/bin/env bash
# run_goal_loop.sh — a maker-checker loop with a budget (course L13, topic 8).
#
#   for each iteration (until a stop condition):
#     1. MAKER    claude -p "<goal + loop memory>"   in a sandbox clone on its own branch
#     2. JUDGE #1 scripts/verify.sh                  (machine: 3-layer definition of done)
#     3. JUDGE #2 claude -p "review against goal"    (reviewer subagent, read-only tools)
#     4. append both verdicts to runs/loop-<id>/loop-state.md (memory for the next iteration)
#
# Stop when: verify passes AND reviewer says accept  -> exit 0  (DONE)
#            total cost >= BUDGET_USD                 -> exit 2  (BUDGET)
#            maker printed NEEDS_HUMAN                -> exit 3  (HUMAN)
#            MAX_ITER iterations                      -> exit 4  (MAX_ITER)
#
# Env:  GOAL=goals/F06-pagination.goal.md  MAX_ITER=3  BUDGET_USD=5  MAKER_BUDGET=3
#       CHECKER_BUDGET=0.50  MAKER_TURNS=40  CHECKER_TURNS=10  RUNNER=docker|local
#       DRY_RUN=1 (replay stages/07-autonomous-loops/fixtures, no API calls, no sandbox)
#       TURNS_FLAG=--max-turns (set empty if your CLI lacks it; see docs/version-notes.md)
set -uo pipefail
cd "$(dirname "$0")/.."

GOAL="${GOAL:-goals/F06-pagination.goal.md}"
MAX_ITER="${MAX_ITER:-3}"
BUDGET_USD="${BUDGET_USD:-5}"
MAKER_BUDGET="${MAKER_BUDGET:-3}"
CHECKER_BUDGET="${CHECKER_BUDGET:-0.50}"
MAKER_TURNS="${MAKER_TURNS:-40}"
CHECKER_TURNS="${CHECKER_TURNS:-10}"
RUNNER="${RUNNER:-docker}"
DRY_RUN="${DRY_RUN:-0}"
FIXTURES="${FIXTURES:-stages/07-autonomous-loops/fixtures}"
TURNS_FLAG="${TURNS_FLAG---max-turns}"

ID="$(date +%Y%m%dT%H%M%S)-$$"
OUT="runs/loop-${ID}"
STATE="${OUT}/loop-state.md"
NAME="$(basename "$GOAL" .goal.md)"
BRANCH="goal/${NAME}-${ID}"
SANDBOX=".worktrees/goal-${ID}"
SANDBOX_ENV=(COMPOSE_PROJECT_NAME=taskhub-goal API_PORT=8100 DB_PORT=55432 BASE_URL=http://localhost:8100)
mkdir -p "$OUT"

log() { printf '[loop %s] %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$OUT/loop.log"; }
jget() {  # jget <file> <key> [default]  — read a top-level field from a claude JSON result
  python3 -c 'import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: d={}
v=d.get(sys.argv[2], sys.argv[3] if len(sys.argv)>3 else "")
print(v if not isinstance(v,(dict,list)) else json.dumps(v))' "$@"
}
add() { python3 -c 'import sys; print(round(float(sys.argv[1])+float(sys.argv[2] or 0),4))' "$1" "$2"; }
ge()  { python3 -c 'import sys; sys.exit(0 if float(sys.argv[1])>=float(sys.argv[2]) else 1)' "$1" "$2"; }

fixture() {  # fixture <role> <i> -> path of the iteration's fixture (falls back to the last one)
  local f="$FIXTURES/$1-$2.json"
  [[ -f "$f" ]] || f="$(ls "$FIXTURES"/"$1"-*.json | sort | tail -1)"
  echo "$f"
}

claude_run() {  # claude_run <outfile> <budget> <turns> <prompt> [extra flags...]
  local out="$1" budget="$2" turns="$3" prompt="$4"; shift 4
  local flags=(-p "$prompt" --output-format json --max-budget-usd "$budget" "$@")
  [[ -n "$TURNS_FLAG" ]] && flags+=("$TURNS_FLAG" "$turns")
  if [[ "$RUNNER" == "docker" ]]; then
    (cd "$SANDBOX" && env "${SANDBOX_ENV[@]}" GOAL_SANDBOX=. docker compose --profile agent \
      run --rm -T agent "${flags[@]}") > "$out" 2> "${out%.json}.stderr"
  else
    (cd "$SANDBOX" && claude "${flags[@]}") > "$out" 2> "${out%.json}.stderr"
  fi
}

# ------------------------------------------------------------------ setup
[[ -f "$GOAL" ]] || { echo "goal file not found: $GOAL"; exit 1; }
{
  echo "# Loop state — ${NAME} (${ID})"
  echo
  echo "Goal: \`${GOAL}\` · budget \$${BUDGET_USD} · max ${MAX_ITER} iterations · runner ${RUNNER}$([[ $DRY_RUN == 1 ]] && echo ' · DRY RUN')"
  echo
} > "$STATE"

if [[ "$DRY_RUN" != "1" ]]; then
  if [[ "$RUNNER" == "local" ]] && ! command -v claude >/dev/null; then
    echo "claude CLI not found"; exit 1
  fi
  log "sandbox: cloning to $SANDBOX on branch $BRANCH (self-contained .git, no secrets copied)"
  git clone --quiet --no-hardlinks . "$SANDBOX" && git -C "$SANDBOX" checkout -q -b "$BRANCH"
  mkdir -p "$SANDBOX/runs/loop-${ID}"
  if [[ "$RUNNER" == "docker" ]]; then
    docker image inspect taskhub-agent:dev >/dev/null 2>&1 || \
      (cd "$SANDBOX" && env "${SANDBOX_ENV[@]}" docker compose --profile agent build agent)
  fi
fi

COST=0
TURNS=0
STATUS="MAX_ITER"
START=$(date +%s)

for ((i = 1; i <= MAX_ITER; i++)); do
  log "=== iteration $i/$MAX_ITER (spent \$${COST} of \$${BUDGET_USD}) ==="

  # ---- 1. maker
  MAKER_OUT="$OUT/maker-$i.json"
  if [[ "$DRY_RUN" == "1" ]]; then
    cp "$(fixture maker "$i")" "$MAKER_OUT"
  else
    cp "$STATE" "$SANDBOX/runs/loop-${ID}/loop-state.md"
    PROMPT="$(cat "$GOAL")

---
Loop memory (runs/loop-${ID}/loop-state.md):
$(cat "$STATE")"
    claude_run "$MAKER_OUT" "$MAKER_BUDGET" "$MAKER_TURNS" "$PROMPT" \
      --permission-mode acceptEdits --settings .claude/settings.agent.json
  fi
  m_cost=$(jget "$MAKER_OUT" total_cost_usd 0); m_turns=$(jget "$MAKER_OUT" num_turns 0)
  m_result=$(jget "$MAKER_OUT" result "")
  COST=$(add "$COST" "$m_cost"); TURNS=$((TURNS + m_turns))
  log "maker: \$${m_cost}, ${m_turns} turns, error=$(jget "$MAKER_OUT" is_error false)"

  if grep -q "NEEDS_HUMAN" <<< "$m_result"; then
    STATUS="HUMAN"
    log "maker asked for a human: $(grep -o 'NEEDS_HUMAN.*' <<< "$m_result" | head -1)"
    printf '## Iteration %d\n- maker: %s\n- stopped: needs a human\n\n' "$i" \
      "$(grep -o 'NEEDS_HUMAN.*' <<< "$m_result" | head -1)" >> "$STATE"
    break
  fi

  # ---- 2. judge #1: machine verification
  VERIFY_OUT="$OUT/verify-$i.log"
  if [[ "$DRY_RUN" == "1" ]]; then
    cp "$FIXTURES/verify-$i.log" "$VERIFY_OUT" 2>/dev/null || cp "$(ls "$FIXTURES"/verify-*.log | tail -1)" "$VERIFY_OUT"
  else
    (cd "$SANDBOX" && env "${SANDBOX_ENV[@]}" bash scripts/verify.sh) > "$VERIFY_OUT" 2>&1
  fi
  if grep -q "RESULT: PASS" "$VERIFY_OUT"; then V="pass"; else V="fail"; fi
  V_LINE="$(grep -E '^VERIFY:' "$VERIFY_OUT" | tail -1)"
  log "verify: ${V}  ${V_LINE}"

  # ---- 3. judge #2: independent reviewer (read-only)
  CHECK_OUT="$OUT/checker-$i.json"
  if [[ "$DRY_RUN" == "1" ]]; then
    cp "$(fixture checker "$i")" "$CHECK_OUT"
  else
    CPROMPT="Use the reviewer subagent to review this branch (git diff main...HEAD) against ${GOAL}.
The machine verifier reported: ${V_LINE:-no summary} (${V}).
Return the reviewer's output in its exact format, starting with 'VERDICT:'."
    claude_run "$CHECK_OUT" "$CHECKER_BUDGET" "$CHECKER_TURNS" "$CPROMPT" \
      --permission-mode dontAsk --disallowedTools Edit Write MultiEdit NotebookEdit \
      --allowedTools Read Grep Glob Task Agent "Bash(git diff *)" "Bash(git log *)" \
      "Bash(git status)" "Bash(make check)" "Bash(python3 scripts/review_diff.py *)"
  fi
  c_cost=$(jget "$CHECK_OUT" total_cost_usd 0); c_turns=$(jget "$CHECK_OUT" num_turns 0)
  c_result=$(jget "$CHECK_OUT" result "")
  COST=$(add "$COST" "$c_cost"); TURNS=$((TURNS + c_turns))
  VERDICT="$(grep -oE 'VERDICT: *(accept|revise|block)' <<< "$c_result" | head -1 | awk '{print $2}')"
  VERDICT="${VERDICT:-unknown}"
  log "checker: verdict=${VERDICT}, \$${c_cost}, ${c_turns} turns"

  # ---- 4. memory for the next iteration
  {
    echo "## Iteration $i"
    echo "- maker: \$${m_cost}, ${m_turns} turns — $(tail -c 300 <<< "$m_result" | tr '\n' ' ')"
    echo "- verify: **${V}** — ${V_LINE}"
    grep -E '^\s+FAIL' "$VERIFY_OUT" | head -5 | sed 's/^/  - /'
    echo "- reviewer: **${VERDICT}**"
    sed -n '/FINDINGS:/,/RUBRIC:/p' <<< "$c_result" | head -12 | sed 's/^/  /'
    echo "- spent so far: \$${COST}"
    echo
  } >> "$STATE"

  if [[ "$V" == "pass" && "$VERDICT" == "accept" ]]; then STATUS="DONE"; break; fi
  if [[ "$VERDICT" == "block" ]]; then STATUS="HUMAN"; log "reviewer blocked: needs a human"; break; fi
  if ge "$COST" "$BUDGET_USD"; then STATUS="BUDGET"; log "budget exhausted"; break; fi
done

DURATION=$(( $(date +%s) - START ))
python3 - "$OUT/summary.json" <<EOF
import json, sys
json.dump({"goal": "$GOAL", "status": "$STATUS", "iterations": $i if $i <= $MAX_ITER else $MAX_ITER,
           "total_cost_usd": $COST, "total_turns": $TURNS, "duration_s": $DURATION,
           "branch": "$BRANCH" if "$DRY_RUN" != "1" else None, "dry_run": "$DRY_RUN" == "1",
           "budget_usd": $BUDGET_USD}, open(sys.argv[1], "w"), indent=2)
EOF
printf '## Result\n- status: **%s** · cost $%s · %s turns · %ss\n' "$STATUS" "$COST" "$TURNS" "$DURATION" >> "$STATE"

log "RESULT: ${STATUS} — cost \$${COST}, ${TURNS} turns, ${DURATION}s — see ${STATE}"
if [[ "$DRY_RUN" != "1" ]]; then
  (cd "$SANDBOX" && env "${SANDBOX_ENV[@]}" docker compose down >/dev/null 2>&1) || true
  cat <<EOF

Review before merging (topic 8: a reviewed result, not just a merged one):
  git fetch $SANDBOX $BRANCH:$BRANCH
  git diff main...$BRANCH --stat
  python3 scripts/review_diff.py --git main...$BRANCH --scope app/,tests/
  # score with evaluator-rubric.md, fill stages/07-autonomous-loops/silent-costs-audit.md
EOF
fi
case "$STATUS" in DONE) exit 0 ;; BUDGET) exit 2 ;; HUMAN) exit 3 ;; *) exit 4 ;; esac
