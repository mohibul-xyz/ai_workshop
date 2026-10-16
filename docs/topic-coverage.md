# Topic coverage matrix (executable)

Read this when you need the map from a workshop topic to its artefacts and the command that
proves it. `make lab-all` runs every checkpoint in this table, top to bottom.

| # | Topic | Stage | Course | Hands-on artefacts | Checkpoint |
|---|---|---|---|---|---|
| 1 | Understanding AI-generated code | 0 | L1, L9 | `stages/00-baseline-reading-ai-code/` — `ai_written/` (11 seeded flaws), `tests_stage0/`, `findings-sheet.md`, `solutions/`; key: `facilitator/answers/stage0-findings.md` | `make stage0-check` (participants: red → green) · `make stage0-check SOLUTION=1` |
| 2 | CLAUDE.md | 1 | L2–L4 | `CLAUDE.md` (router), `AGENTS.md` mirror, `docs/*.md`, `stages/01-instructions-claude-md/starter-CLAUDE.md`, `scripts/lint_claude_md.py` | `make lab-claude-md` |
| 3 | Skills | 2 (+3, 5) | L13 | `.claude/skills/{write-migration,handoff,write-spec,review-diff,open-pr}/SKILL.md`, `scripts/check_migrations.py` | `make migrate-check` (round-trip on a throwaway DB) |
| 4 | Hooks | 2 (+3–6) | L2, L9, L11 | `.claude/hooks/` — `guard_bash`, `guard_files`, `post_edit_lint`, `session_start`, `post_state_check`, `stop_gate`, `audit_log`; `scripts/audit_report.py` | `make hooks-test` (25 tests) |
| 5 | Permissions | 2 | L2 | `.claude/settings.json` matrix, `.claude/settings.agent.json`, `stages/02-permissions-hooks-skills/{permission_sim.py,scenarios.json,starter-settings.json}` | `make lab-permissions` → 25/25 |
| 6 | Human-in-the-loop | 4 | L7, L8 | `stages/04-scope-human-in-the-loop/approval-checklist.md`; reference F04 as six commits (`git log --grep "F04 step"`); `post_state_check` hook (WIP = 1) | `make check-state` + F04 `passing` with `evidence/F04-verify.log` |
| 7 | Spec-driven development | 5 | L9, L12 | `specs/_template.md`, `specs/F05-task-tags.md` (12 ACs), `.plan.md`, `tests/test_tags.py::test_ac*`, `.claude/agents/reviewer.md`, `evaluator-rubric.md` | `make lab-spec` (12/12) + `make verify` |
| 8 | Autonomous mode | 7 | L13 | `goals/F06-pagination.goal.md`, `scripts/run_goal_loop.sh`, `Dockerfile.agent`, `stages/07-autonomous-loops/{fixtures,silent-costs-audit.md}` | `make lab-loop-dry` (DONE / BUDGET / MAX_ITER / HUMAN all fire) |
| 9 | Reading diffs critically | 5 (+7) | L9 | `stages/05-verification-specs-diffs/prs/PR-10{1,2,3}.diff`, `scripts/review_diff.py`, `review-checklist.md`; key: `facilitator/answers/prs.md` | `make lab-diffs` (11/11 seeded rules, 0 false HIGHs) |
| 10 | Context optimization | 8 | L2, L4, L13 | `stages/08-context-optimization/variants/{bloated,router,hygiene}`, `scripts/{context_report.py,run_benchmark.sh,compare_runs.py}`, `experiments/scorecard.md` | `make lab-context` (`E2E=1` adds a real pipeline run with a fake agent) |

## The five subsystems → where they live

| Subsystem | Artefacts | Proof |
|---|---|---|
| Instructions | `CLAUDE.md`, `AGENTS.md`, `docs/` | `make lab-claude-md` |
| Tools | `.claude/settings.json`, `.claude/hooks/`, `.claude/skills/`, `.claude/agents/` | `make lab-permissions`, `make hooks-test` |
| Environment | `pyproject.toml`, `.python-version`, `Dockerfile`, `docker-compose.yml`, `Makefile`, `init.sh` | `./init.sh` |
| State | `feature_list.json`, `claude-progress.md`, `session-handoff.md` | `make check-state` |
| Feedback | `scripts/verify.sh`, `scripts/smoke_e2e.py`, `stop_gate`, `reviewer`, `review_diff.py`, `clean_state_check.py` | `make verify`, `make clean-state` |

## Workshop reset
The reference build has F04–F06 `passing`. To run the day for real, participants start from a
state where those are `not_started` (the stage-tag snapshots planned for phase 2 do this).
B1 (`/projects/{id}/stats`) is deliberately never implemented on `main`.
