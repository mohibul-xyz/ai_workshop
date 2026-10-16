#!/usr/bin/env bash
# verify.sh — the three-layer definition of done (course L9/L10).
#
#   Layer 1  static     ruff (lint + format) and mypy --strict
#   Layer 2  behaviour  pytest against Postgres + migration round-trip
#   Layer 3  system     real stack up + scripts/smoke_e2e.py over HTTP
#
# Evidence: everything is tee'd to runs/verify-<timestamp>.log.
# EVIDENCE=F04 make verify  -> also copies the log to evidence/F04-verify.log (committed).
# Exit 0 only if all three layers are green; the failing layer is named on the last line.
set -uo pipefail
cd "$(dirname "$0")/.."

mkdir -p runs
TS="$(date +%Y%m%dT%H%M%S)"
LOG="runs/verify-${TS}.log"
exec > >(tee "$LOG") 2>&1

declare -A RESULT=([static]=skipped [behaviour]=skipped [system]=skipped)
FAILED=""

layer() {  # layer <name> <command...>
  local name="$1"; shift
  printf '\n=== Layer: %s ===\n' "$name"
  if "$@"; then
    RESULT[$name]=pass
    return 0
  fi
  RESULT[$name]=FAIL
  FAILED="${FAILED:-$name}"
  return 1
}

static()    { make -s lint && make -s typecheck; }
behaviour() { make -s test && make -s migrate-check; }
system()    { make -s up && python3 scripts/smoke_e2e.py --base-url "${BASE_URL:-http://localhost:8000}"; }

echo "verify.sh  $(date -Is)  git=$(git rev-parse --short HEAD 2>/dev/null || echo none)$(git diff --quiet 2>/dev/null || echo +dirty)"
layer static static && layer behaviour behaviour && layer system system

summary="VERIFY: static=${RESULT[static]} behaviour=${RESULT[behaviour]} system=${RESULT[system]}"
printf '\n%s\nlog: %s\n' "$summary" "$LOG"

if [[ -n "$FAILED" ]]; then
  echo "RESULT: FAIL at layer '$FAILED' — not done. Fix it and rerun make verify."
  exit 1
fi
if [[ -n "${EVIDENCE:-}" ]]; then
  mkdir -p evidence
  sleep 0.2   # let tee flush
  cp "$LOG" "evidence/${EVIDENCE}-verify.log"
  echo "evidence: evidence/${EVIDENCE}-verify.log"
fi
echo "RESULT: PASS — all three layers green."
