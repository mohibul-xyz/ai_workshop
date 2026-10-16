# Benchmark B1 — project stats

**Prompt given to the agent (verbatim, every stage):**

> Add `GET /api/v1/projects/{id}/stats` returning task counts per status.

That is the whole prompt. What the agent *can* discover from the repo depends on the harness
stage: at Stage 0 nothing; from Stage 1 `docs/api-conventions.md`; from Stage 5 `make verify`.

## Contract the hidden tests check (not shown to the agent)
Facilitators: this is what "done" means for scoring. It follows `docs/api-conventions.md`
(nouns for computed sub-resources, counts are integers never null, 404 for a missing parent).

```http
GET /api/v1/projects/{id}/stats  →  200
{"project_id": 1, "total": 5, "counts": {"todo": 2, "in_progress": 1, "done": 2}}
```
- every status key is present, `0` when there are none
- `total` = number of tasks in the project = sum of `counts`
- only that project's tasks are counted
- unknown project → `404 {"detail": "Project not found"}`

## Scoring (one scorecard row per run)
| Signal | How |
|---|---|
| Hidden tests passed | `scripts/run_benchmark.sh` copies `hidden/` into the run's worktree after the agent finishes and runs it |
| Verify layers green | `scripts/verify.sh` in the same worktree |
| Rubric | `evaluator-rubric.md`, by a human or the `reviewer` subagent |
| Turns / tokens / cost | `claude -p --output-format json` → `num_turns`, `usage`, `total_cost_usd` |

Reference solution: `solution.patch` (`git apply benchmarks/B1-project-stats/solution.patch`).
**Never commit it applied** — B1 must stay unimplemented on `main`.
