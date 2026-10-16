#!/usr/bin/env bash
# make lab-loop-dry — checkpoint for topic 8 without spending money: replay recorded maker /
# verifier / reviewer outputs and assert that every stop condition fires as designed.
set -uo pipefail
cd "$(dirname "$0")/../.."
fail=0
expect() {  # expect <name> <exit code> <env...>
  local name="$1" want="$2"; shift 2
  env DRY_RUN=1 "$@" bash scripts/run_goal_loop.sh > /dev/null 2>&1
  local got=$?
  local dir; dir="$(ls -td runs/loop-* | head -1)"
  local status; status="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["status"])' "$dir/summary.json")"
  if [[ "$got" == "$want" ]]; then
    printf 'OK   %-34s exit=%s status=%-8s cost=$%s  (%s)\n' "$name" "$got" "$status" \
      "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["total_cost_usd"])' "$dir/summary.json")" "$dir"
  else
    printf 'FAIL %-34s exit=%s (want %s)\n' "$name" "$got" "$want"; fail=1
  fi
}
expect "goal reached (verify+review pass)" 0
expect "budget cap stops the loop"         2 BUDGET_USD=1
expect "iteration cap stops the loop"      4 MAX_ITER=1
expect "agent asks for a human"            3 FIXTURES=stages/07-autonomous-loops/fixtures-human
exit $fail
