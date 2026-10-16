#!/usr/bin/env bash
# Stand-in for `claude -p` so the benchmark pipeline (clone → variant → agent → hidden tests →
# verify → JSON) can be tested end to end for free: it "solves" B1 by applying the reference
# patch and prints a claude-shaped JSON result. CLAUDE_BIN=stages/08-context-optimization/fake_claude.sh
set -euo pipefail
git apply "$(git rev-parse --show-toplevel)/benchmarks/B1-project-stats/solution.patch"
cat <<JSON
{"type": "result", "subtype": "success", "is_error": false, "duration_ms": 1000, "num_turns": 1,
 "total_cost_usd": 0, "result": "applied reference patch (fake agent)",
 "usage": {"input_tokens": 0, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 0, "output_tokens": 0}}
JSON
