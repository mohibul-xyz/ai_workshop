# Scorecard — benchmark B1, same model, every stage

Rerun B1 (`benchmarks/B1-project-stats/task.md`) after each stage with the **same model**.
Real numbers come from `scripts/run_benchmark.sh` / `claude -p --output-format json`;
hidden tests are scored only after the agent finishes. Leave a cell blank rather than guess.

| Stage | Hidden tests passed (/7) | Verify layers green (/3) | Rubric (0–12) | Turns | Input tokens | Cost | Human interventions |
|---|---|---|---|---|---|---|---|
| 0 Baseline (prompt only) | | | | | | | |
| 1 Instructions | | | | | | | |
| 2 Permissions, hooks, skills | | | | | | | |
| 3 State | | | | | | | |
| 4 Scope + HITL | | | | | | | |
| 5 Verification + specs | | | | | | | |
| 6 Observability + clean state | | | | | | | |
| 7 Autonomous loop | | | | | | | |
| 8 Optimized context | | | | | | | |

## Five-subsystem audit (1–5 each)

| Subsystem | Stage 0 | Stage 6 | Stage 8 | Evidence |
|---|---|---|---|---|
| Instructions | | | | `make lab-claude-md` |
| Tools | | | | `make lab-permissions`, `make hooks-test` |
| Environment | | | | `./init.sh` on a fresh clone |
| State | | | | `make check-state`; fresh-session "continue" |
| Feedback | | | | `make verify`, reviewer, `make lab-diffs` |

## Stage 8 conclusion
_What we trimmed, what changed, what we keep (one paragraph):_

