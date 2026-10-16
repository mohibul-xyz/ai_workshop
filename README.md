# TaskHub Harness Lab

A one-day, hands-on workshop that implements the
[Learn Harness Engineering](https://walkinglabs.github.io/learn-harness-engineering/en/) course
end to end, then uses that harness to practise ten agent-engineering skills.

**Stack:** Python 3.12 · FastAPI · PostgreSQL 16 · Alembic · Docker Compose · Claude Code
(`AGENTS.md` mirror for Codex)

TaskHub, a small task-tracker REST API (projects → tasks), is only the **workload**. The real
deliverable is the **harness around it**: the files, rules, hooks, state and checks that turn an
unchanged model from "confidently wrong" into "reliably done".

- [Quick start](#quick-start)
- [How the harness works](#how-the-harness-works)
- [How the topic coverage matrix works](#how-the-topic-coverage-matrix-works)
- [Stages and course map](#stages-and-course-map)
- [Repository layout](#repository-layout)
- [Status: built vs planned](#status-built-vs-planned)

---

## Quick start

Prerequisites: Docker with Compose v2, Git, Make, Python 3 on the host (the hooks are
stdlib-only Python). Claude Code installed and logged in. An `ANTHROPIC_API_KEY` is needed only
for the paid targets (`make goal-loop`, `make benchmark`) and for exact token counts.

```bash
make setup          # build images, create .env from .env.example, host .venv with ruff
./init.sh           # install → start stack → verify baseline → print the next feature
make lab-all        # run every topic checkpoint (12) and summarise
make help           # list every target
```

The API runs at http://localhost:8000/docs once `make up` (or `./init.sh`) has run.

---

## How the harness works

A **harness** is everything outside the model weights. It does not make the model smarter; it
gives the model a closed-loop working system. The course splits it into five subsystems, and
each one lives in specific files in this repo:

| Subsystem | Job | Where it lives here | Proof command |
|---|---|---|---|
| **Instructions** | Tell the agent what the project is and what the hard rules are | [CLAUDE.md](CLAUDE.md) (64-line router), [AGENTS.md](AGENTS.md) mirror, [docs/](docs/) read on demand | `make lab-claude-md` |
| **Tools** | Give the agent enough access, and no more | [.claude/settings.json](.claude/settings.json) (permissions + hooks), [.claude/hooks/](.claude/hooks/), [.claude/skills/](.claude/skills/), [.claude/agents/reviewer.md](.claude/agents/reviewer.md) | `make lab-permissions`, `make hooks-test` |
| **Environment** | Make the runtime reproducible and self-describing | [Dockerfile](Dockerfile), [Dockerfile.agent](Dockerfile.agent), [docker-compose.yml](docker-compose.yml), [Makefile](Makefile), [pyproject.toml](pyproject.toml), [.python-version](.python-version), [init.sh](init.sh) | `./init.sh` |
| **State** | Let work survive across sessions | [feature_list.json](feature_list.json), [claude-progress.md](claude-progress.md), [session-handoff.md](session-handoff.md) | `make check-state` |
| **Feedback** | Show the agent and the human whether the work really is correct | [scripts/verify.sh](scripts/verify.sh), [scripts/smoke_e2e.py](scripts/smoke_e2e.py), `stop_gate` hook, `reviewer` subagent, [scripts/review_diff.py](scripts/review_diff.py), [scripts/clean_state_check.py](scripts/clean_state_check.py) | `make verify`, `make clean-state` |

### The life of one agent session

Each step below is enforced by a file in the repo, not by trusting the agent to remember:

```
SessionStart hook ─► prints progress summary, active feature, git status into context
       │
./init.sh ─────────► tooling → install → stack up → `make check` + check_state → "NEXT: Fxx"
       │              (a red baseline stops the session before any change: course L6)
       ▼
Pick ONE feature (WIP = 1) ─► feature_list.json: in_progress, else highest-priority not_started
       │
For every tool call:
   permissions (deny → ask → allow) ─► PreToolUse hooks ─► tool runs ─► PostToolUse hooks
   pattern match on the call           code inspects it                  lint / state / audit
       │
Agent tries to stop ─► Stop hook: code changed and `make check` red? → "keep working"
       │
"Done" claim ──────► `make verify` (3 layers) → evidence/Fxx-verify.log + test names in feature_list.json
       │
handoff skill ─────► claude-progress.md + session-handoff.md + `make clean-state` → commit
```

### Tools, layer 1: the permission matrix

[.claude/settings.json](.claude/settings.json) is committed and team-wide. Claude Code checks
rules in the order **deny → ask → allow**, and deny always wins.

| | Allow (no prompt) | Ask (human approves) | Deny (never) |
|---|---|---|---|
| **Read** | `app/`, `tests/`, `docs/`, `migrations/`, `specs/`, `goals/`, `stages/`, `scripts/` | — | `.env`, `.env.*`, `secrets/**`, `benchmarks/**/hidden/**` |
| **Edit** | `app/`, `tests/`, `docs/`, `specs/`, the three state files | `migrations/**`, `pyproject.toml`, `docker-compose.yml`, `Dockerfile*`, `Makefile` | `.env*`, `.claude/settings.json`, `.claude/hooks/**`, hidden benchmark tests |
| **Run** | `make test/lint/typecheck/check/verify/check-state/migrate-check/clean-state/hooks-test/lab-*`, `git status/diff/log/show`, `python3 scripts/*` | `git commit/push`, `docker compose up/exec/run`, `alembic *`, `pip install *`, `make migration *` | `curl`, `wget`, `sudo`, `git push --force/-f`, `git reset --hard`, `cat .env*`, `WebFetch` |

Teaching points built into this matrix:
- `Read(./.env)` does **not** block `cat .env` in Bash, so the Bash form is denied separately.
- `disableBypassPermissionsMode: "disable"` keeps the guardrails on even if someone tries to bypass them.
- Personal overrides go in `.claude/settings.local.json` (git-ignored).
- Unattended runs get a **narrower** allowlist,
  [.claude/settings.agent.json](.claude/settings.agent.json), passed with `--settings`. It cannot
  edit migrations, scripts, goals or `.claude/`, cannot run `docker`/`pip`/`git push`, and since
  nobody is there to answer a prompt in `-p` mode, anything not allowed is refused.

[permission_sim.py](stages/02-permissions-hooks-skills/permission_sim.py) models these
semantics. It replays 25 realistic agent actions from
[scenarios.json](stages/02-permissions-hooks-skills/scenarios.json) against a settings file;
`--explain` shows which rule decided a single action.

### Tools, layer 2: hooks (code that runs on every call)

Permissions match *patterns*. Hooks run *code*, so they catch what patterns miss
(`cd x && rm -fr y`, `sh -c "…"`, reordered flags). The protocol: the tool call arrives as
JSON on stdin; **exit 2 blocks** the call (PreToolUse) or feeds the error back (PostToolUse),
and stderr goes to the agent. Every message says what was blocked, why, and what to do instead.

| Hook | Event | Rule |
|---|---|---|
| [session_start.py](.claude/hooks/session_start.py) | `SessionStart` | Injects "Current verified state", the active feature and `git status`, so "continue" works with no briefing |
| [guard_bash.py](.claude/hooks/guard_bash.py) | `PreToolUse` Bash | Blocks `rm -rf`, `git reset --hard`, force push, `DROP`/`TRUNCATE`, `docker compose down -v`, `alembic downgrade base`, `curl … \| sh` |
| [guard_files.py](.claude/hooks/guard_files.py) | `PreToolUse` Edit/Write | Committed migrations are immutable; `.env*`, `secrets/`, harness files and hidden tests are untouchable |
| [post_edit_lint.py](.claude/hooks/post_edit_lint.py) | `PostToolUse` Edit/Write | Runs `ruff` on the edited file and feeds errors back straight away |
| [post_state_check.py](.claude/hooks/post_state_check.py) | `PostToolUse` Edit/Write | When `feature_list.json` changes, runs `check_state.py` (WIP = 1, no `passing` without evidence) |
| [audit_log.py](.claude/hooks/audit_log.py) | `PostToolUse` `*` | Appends every action to `.claude/audit.log` (JSONL); `make audit-report` summarises it |
| [stop_gate.py](.claude/hooks/stop_gate.py) | `Stop` | "No victory without green": if `app/`, `migrations/` or `tests/` changed and `make check` fails, the agent cannot stop. Loop-safe via `stop_hook_active`; `HARNESS_STOP_GATE=0` turns it off for ablation runs |

All hooks have unit tests that pipe fake tool calls in and assert block/allow
([test_hooks.py](.claude/hooks/tests_hooks/test_hooks.py), `make hooks-test`).

### Tools, layer 3: skills and the reviewer subagent

| Skill / agent | Packages | Ends with |
|---|---|---|
| [write-migration](.claude/skills/write-migration/SKILL.md) | Sequential Alembic revision, autogenerate review, safe NOT NULL, exact `downgrade()` | `make migrate-check` (static rules + upgrade → downgrade → upgrade on a throwaway DB) |
| [write-spec](.claude/skills/write-spec/SKILL.md) | Planner role: `specs/<ID>-<slug>.md` with Given/When/Then criteria, then a separate plan | `make lab-spec` (every AC has a `test_ac<N>_*`) |
| [review-diff](.claude/skills/review-diff/SKILL.md) | Risk scanner + human checklist (scope → behaviour → tests → data → security → reversibility) | accept / revise / block |
| [handoff](.claude/skills/handoff/SKILL.md) | End-of-session routine | progress + handoff note + `make clean-state` + commit |
| [reviewer](.claude/agents/reviewer.md) subagent | Independent, read-only checker (Read/Grep/Glob/Bash) | [evaluator-rubric.md](evaluator-rubric.md) score 0–12 and a verdict |

### State: continuity across sessions

- **[feature_list.json](feature_list.json)** is the state primitive. Each feature has
  `id, priority, area, title, user_visible_behavior, status, verification[], evidence[], notes`.
  [check_state.py](scripts/check_state.py) enforces the schema, unique ids, **at most one
  `in_progress`**, and that every `passing` feature has verification commands and evidence
  paths that **exist in the repo**.
- **[claude-progress.md](claude-progress.md)**: the "Current verified state" section plus one
  record per session, newest first. The SessionStart hook prints it.
- **[session-handoff.md](session-handoff.md)**: a short note from the outgoing session to the
  next one (active feature, exact next step, what not to do).

### Feedback: the three-layer definition of done

[scripts/verify.sh](scripts/verify.sh) (`make verify`) is the only way a feature becomes `passing`:

| Layer | Runs | Catches |
|---|---|---|
| 1 Static | `ruff check` + `ruff format --check` + `mypy --strict` | style, type errors, invented APIs |
| 2 Behaviour | `pytest` against Postgres + migration round-trip | logic bugs, irreversible migrations |
| 3 System | `make up` + [smoke_e2e.py](scripts/smoke_e2e.py) over HTTP | wiring, config, stale migrations in the real stack |

Every run writes `runs/verify-<timestamp>.log`. `EVIDENCE=F04 make verify` also copies it to
`evidence/F04-verify.log` (committed), which `feature_list.json` then cites. The layers
short-circuit, and the last line names the failing layer.

On top of verify:
- **Maker ≠ checker.** The `reviewer` subagent judges against the spec or goal, not against
  the code's own claims.
- **Diff review.** [review_diff.py](scripts/review_diff.py) flags deleted tests, `skip`/`xfail`,
  broad `except`, out-of-scope files, migration edits, secrets, `TODO`s and size. The scanner
  finds suspicious lines; only a human judges intent.
- **Clean state.** [clean_state_check.py](scripts/clean_state_check.py) checks state validity,
  that progress was recorded, debug leftovers, stray files, conflict markers, `make check`,
  and that the stack starts. `FAST=1` skips the last two.

### Autonomous mode: the maker-checker loop

[scripts/run_goal_loop.sh](scripts/run_goal_loop.sh) runs a goal file such as
[goals/F06-pagination.goal.md](goals/F06-pagination.goal.md) (goal · verification · stop
conditions · out of scope · memory) in the sandboxed `agent` container (profile `agent`, built
from [Dockerfile.agent](Dockerfile.agent), with only the sandbox clone mounted). Each iteration:

1. **Maker:** `claude -p` with `settings.agent.json`, a per-iteration budget and a turn cap.
2. **Judge 1 (machine):** `scripts/verify.sh`.
3. **Judge 2 (model):** `claude -p` running the `reviewer` subagent on the branch diff.
4. Findings go into `runs/loop-*/loop-state.md`, which the next iteration reads first.

| Stop condition | Exit |
|---|---|
| verify passes **and** reviewer says accept | 0 `DONE` |
| total cost ≥ `BUDGET_USD` | 2 `BUDGET` |
| maker prints `NEEDS_HUMAN: …`, or reviewer says block | 3 `HUMAN` |
| `MAX_ITER` reached | 4 `MAX_ITER` |

After the loop, a human reviews the result with `review-diff` and the rubric, and audits the
four silent costs ([silent-costs-audit.md](stages/07-autonomous-loops/silent-costs-audit.md)).

---

## How the topic coverage matrix works

The matrix in [docs/topic-coverage.md](docs/topic-coverage.md) maps each of the ten workshop
topics to a stage, the course lectures it comes from, the artefacts that implement it, and
**one `make` target that proves it**. It is meant to be run, not only read.

### The matrix

| # | Topic | Stage | Course | Key artefacts | Checkpoint | Passes when |
|---|---|---|---|---|---|---|
| 1 | Understanding AI-generated code | 0 | L1, L9 | `stages/00-…/ai_written/` (11 seeded flaws), `tests_stage0/`, `findings-sheet.md` | `make stage0-check` | bug-proving tests green + findings sheet complete |
| 2 | CLAUDE.md | 1 | L2–L4 | `CLAUDE.md` router, `AGENTS.md`, `docs/`, `lint_claude_md.py` | `make lab-claude-md` | length, required sections, linked files exist, mirror in sync |
| 3 | Skills | 2 (+3, 5) | L13 | 4 skills in `.claude/skills/`, `check_migrations.py` | `make migrate-check` | static rules + round-trip on a throwaway DB |
| 4 | Hooks | 2 (+3–6) | L2, L9, L11 | 7 hooks in `.claude/hooks/`, `audit_report.py` | `make hooks-test` | 25 hook unit tests green |
| 5 | Permissions | 2 | L2 | `settings.json`, `settings.agent.json`, `permission_sim.py`, `scenarios.json` | `make lab-permissions` | simulator 25/25 |
| 6 | Human-in-the-loop | 4 | L7, L8 | `approval-checklist.md`, F04 as six commits, `post_state_check` hook | `make check-state` | WIP = 1, F04 `passing` with `evidence/F04-verify.log` |
| 7 | Spec-driven development | 5 | L9, L12 | `specs/F05-task-tags.md` (12 ACs) + `.plan.md`, `tests/test_tags.py::test_ac*`, `reviewer` | `make lab-spec` + `make verify` | 12/12 ACs have a test; 3 layers green |
| 8 | Autonomous mode | 7 | L13 | goal file, `run_goal_loop.sh`, `Dockerfile.agent`, loop fixtures | `make lab-loop-dry` | DONE / BUDGET / MAX_ITER / HUMAN all fire with the right exit code |
| 9 | Reading diffs critically | 5 (+7) | L9 | `prs/PR-101..103.diff`, `review_diff.py`, `review-checklist.md` | `make lab-diffs` | PRs apply, 11/11 seeded defects flagged, 0 false HIGHs |
| 10 | Context optimization | 8 | L2, L4, L13 | variants `bloated/router/hygiene`, `context_report.py`, `run_benchmark.sh`, `compare_runs.py` | `make lab-context` | variants in sync, bloated loads > 3× router startup tokens, A/B/C table builds |

### `make lab-all`: the whole matrix as one command

`make lab-all` runs the 12 checkpoints in `LAB_CHECKS` in the [Makefile](Makefile), in order,
keeps going after a failure, and prints `all 12 checkpoints green` or the list that failed:

| # | Target | Covers | Needs |
|---|---|---|---|
| 1 | `lab-claude-md` | topic 2 · Instructions | host Python |
| 2 | `lab-permissions` | topic 5 · Tools | host Python |
| 3 | `hooks-test` | topic 4 · Tools | host Python |
| 4 | `migrate-check` | topic 3 · Tools | Docker (throwaway DB) |
| 5 | `check-state` | topic 6 · State | host Python |
| 6 | `verify` | topic 7 · Feedback (3 layers) | Docker (full stack) |
| 7 | `lab-spec` | topic 7 | host Python |
| 8 | `lab-diffs` | topic 9 · Feedback | host Python |
| 9 | `lab-loop-dry` | topic 8 | host only (replays fixtures, no API) |
| 10 | `stage0-check-solution` | topic 1 (against `solutions/` + answer key) | Docker |
| 11 | `lab-context` | topic 10 | host; exact counts with `ANTHROPIC_API_KEY`, else chars/4 estimate |
| 12 | `clean-state` | L12 · end-of-session gate | Docker |

### How the checkpoints stay free and deterministic

Agent output varies and costs money, so each checkpoint proves the **harness machinery** with
no live model. The paid runs are separate targets:

| Mechanism | Free checkpoint (in `lab-all`) | Paid / live run (not in `lab-all`) |
|---|---|---|
| Autonomous loop | `lab-loop-dry`: `DRY_RUN=1` replays recorded maker/verify/checker outputs from `stages/07-autonomous-loops/fixtures/` | `make goal-loop` (`GOAL=… BUDGET_USD=… RUNNER=docker\|local`) |
| Context benchmark | `lab-context`: dry-run A/B/C table from `stages/08-…/fixtures/`; `E2E=1` runs the real clone → variant → hidden tests → verify pipeline with `fake_claude.sh` (expects 7/7, 3/3) | `make benchmark VARIANT=bloated\|router\|hygiene` or `ABLATE=instructions\|verification\|state`, `RUNS=3` |
| Stage 0 reading | `stage0-check-solution` runs the bug-proving tests against `solutions/` | `make stage0-check` runs them against `ai_written/` (red until participants fix it) |

### Reference build vs participant mode

`main` is the **reference build**: F01–F06 are all `passing` with committed evidence, so every
checkpoint can go green. To run the day for real, participants start from a state where
F04–F06 are `not_started` and rebuild them (F04 by hand with approvals, F05 from a spec, F06
with the loop). **Benchmark B1** (`GET /api/v1/projects/{id}/stats`) is deliberately never
implemented on `main`: it is the fixed task rerun at every stage, scored by 7 hidden tests
that the permission matrix stops the agent from reading.

### Matrix vs scorecard

The two measure different things:
- The **coverage matrix** proves each *artefact works*: the hook blocks, the simulator scores
  25/25, the loop stops on budget.
- The **[scorecard](experiments/scorecard.md)** proves the *harness is worth having*. It has one
  row per stage for B1 on the same model (hidden tests /7, verify layers /3, rubric /12, turns,
  input tokens, cost, human interventions), the five-subsystem audit (1–5) at Stages 0, 6 and 8,
  and the Stage 8 ablation conclusion. Its numbers come only from real runs; it is blank on
  `main` on purpose.

---

## Stages and course map

Each stage adds one harness mechanism and teaches the matching workshop topic. B1 is rerun
after each stage to fill a scorecard row.

| Stage | Course | Harness added | Topic | Folder |
|---|---|---|---|---|
| 0 Baseline | L1, P01-A | none: prompt only | 1 Reading AI code | [stages/00-baseline-reading-ai-code](stages/00-baseline-reading-ai-code/) |
| 1 Instructions | L2–L4, P01-B, P02 | `CLAUDE.md` router + `docs/` | 2 CLAUDE.md | [stages/01-instructions-claude-md](stages/01-instructions-claude-md/) |
| 2 Tools | L2, L3, L6, L13 | permissions, guard/lint hooks, `write-migration` | 3 Skills · 4 Hooks · 5 Permissions | [stages/02-permissions-hooks-skills](stages/02-permissions-hooks-skills/) |
| 3 State | L5, L6, P03 | state files, SessionStart hook, `handoff`, `check_state.py` | — | — |
| 4 Scope + HITL | L7, L8, P04 | WIP = 1, `post_state_check` hook; F04 in six approved steps | 6 Human-in-the-loop | [stages/04-scope-human-in-the-loop](stages/04-scope-human-in-the-loop/) |
| 5 Feedback | L9, L10, P05 | `verify.sh`, Stop gate, `reviewer`, rubric; F05 from a spec; seeded PRs | 7 Spec-driven · 9 Diffs | [stages/05-verification-specs-diffs](stages/05-verification-specs-diffs/) |
| 6 Capstone | L11, L12, P06 | JSON logs + request IDs, audit hook, `quality-document.md`, clean-state | — | [stages/06-observability-clean-state](stages/06-observability-clean-state/) |
| 7 Autonomous | L13, P07 | goal file, sandboxed maker-checker loop with budget | 8 Autonomous mode | [stages/07-autonomous-loops](stages/07-autonomous-loops/) |
| 8 Context | L2, L4, L13 | variants A/B/C, token report, benchmark + ablation | 10 Context optimization | [stages/08-context-optimization](stages/08-context-optimization/) |

Principles carried through every stage: give a **map, not a manual** · **constrain, don't
micromanage** (rules as executable checks) · the **maker is not the checker** · **"done"
requires evidence** · **WIP = 1** · **leave a clean state** · **remove one component at a time
and measure**.

---

## Repository layout

```
├── CLAUDE.md  AGENTS.md  docs/        # Instructions (router + on-demand topic docs)
├── .claude/
│   ├── settings.json                  # permission matrix + hook wiring (team-wide)
│   ├── settings.agent.json            # narrowed allowlist for unattended runs
│   ├── hooks/                         # 7 hooks + _common.py + tests_hooks/
│   ├── skills/                        # write-migration, write-spec, review-diff, handoff
│   └── agents/reviewer.md             # independent checker
├── feature_list.json  claude-progress.md  session-handoff.md   # State
├── init.sh  Makefile  Dockerfile  Dockerfile.agent  docker-compose.yml  pyproject.toml
├── evaluator-rubric.md  quality-document.md  clean-state-checklist.md
├── app/  tests/  migrations/          # TaskHub workload (F01–F06)
├── specs/  goals/                     # spec-driven (F05), autonomous (F06)
├── scripts/                           # verify, smoke_e2e, check_*, review_diff, context_report,
│                                      # run_benchmark, compare_runs, run_goal_loop, audit_report
├── evidence/                          # committed verify logs cited by feature_list.json
├── benchmarks/B1-project-stats/       # task.md, solution.patch, hidden/ (agent-denied)
├── experiments/scorecard.md
├── facilitator/answers/               # answer keys: stage 0 findings, seeded PRs
└── stages/00-…/ … 08-…/               # exercises, starters, fixtures, per-stage checkers
```

Docker Compose services: `db` (Postgres 16 + healthcheck), `migrate` (one-shot
`alembic upgrade head`), `api` (`:8000`), `tools` (profile `tools`: pytest/ruff/mypy/alembic)
and `agent` (profile `agent`: sandboxed Claude Code for the loop).

Claude Code features this harness depends on, and what to change if one behaves differently,
are listed in [docs/version-notes.md](docs/version-notes.md) (checked against Claude Code 2.1.300).

---

## Status: built vs planned

**Built and checked:** all ten topics have artefacts, and `make lab-all` is 12/12 green on `main`.

**Planned, not yet in the repo:**
- `stage-NN-start` / `stage-NN-done` git tags, and the participant-mode snapshot with F04–F06 reset.
- A `README.md` in each `stages/NN-*/` folder, and a `FACILITATOR.md` for timing and
  troubleshooting (answer keys already exist in [facilitator/answers/](facilitator/answers/)).
- Stage 3 has no exercise folder yet; its artefacts are the root state files and hooks.
- Real scorecard numbers, which come from running the workshop.
