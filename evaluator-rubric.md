# Evaluator rubric

Used by the `reviewer` subagent, by humans reviewing a feature or PR, and for the benchmark
scorecard. Six dimensions, each **0–2**, total **0–12**. Score from evidence only.

| Dimension | 0 | 1 | 2 |
|---|---|---|---|
| **Correctness** | Core behaviour wrong or missing; acceptance tests fail | Happy path works; an edge case or error path is wrong | Every acceptance criterion met, including boundaries and errors |
| **Verification** | No tests, or tests that would pass without the change | Tests exist but miss boundaries/negatives, or only some verify layers ran | Tests fail-before/pass-after; `make verify` green on all 3 layers; evidence recorded |
| **Scope** | Unrelated files changed, or behaviour changed that was not asked for | Minor drift (stray formatting, small unrelated tweak) | Diff contains only what the feature needs |
| **Reliability** | Data loss risk, injection, swallowed errors, irreversible migration | Fragile spots (naive datetimes, missing index, unclear errors) | Safe under real data: tz-aware, parameterised SQL, reversible migration, clear errors |
| **Maintainability** | Wrong layer (SQL in routers, FastAPI in services), duplicated logic | Works but inconsistent with `docs/` conventions | Follows `docs/architecture.md` and `docs/api-conventions.md`; readable; typed |
| **Handoff** | State files untouched; next session would be lost | Progress updated but evidence or next step missing | `feature_list.json` evidence real, `claude-progress.md` + `session-handoff.md` updated, `make clean-state` green |

## How to score

1. Read the contract (spec / goal / task.md) first, then the diff.
2. For each dimension, find the **lowest** level whose description fits any part of the change.
3. Write one line of evidence per dimension (`file:line`, command output, or log path).

## Verdict

| Total | And | Verdict |
|---|---|---|
| 11–12 | no 0 in any dimension | **accept** |
| 7–10 | no 0 in Correctness or Reliability | **revise** |
| ≤ 6, or a 0 in Correctness / Reliability | — | **block** |

## Score sheet

| Dimension | Score | Evidence |
|---|---|---|
| Correctness | | |
| Verification | | |
| Scope | | |
| Reliability | | |
| Maintainability | | |
| Handoff | | |
| **Total** | **/12** | Verdict: |
