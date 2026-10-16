# Clean-state checklist

Every session ends in a state the next session (or a colleague) can start from with no
briefing (course L12). `make clean-state` automates the starred items; the `handoff` skill
runs it.

| # | Check | How | Auto |
|---|---|---|---|
| 1 | Build and tests pass | `make check` | ★ |
| 2 | Startup path works | `make up` → `GET /health` 200 | ★ |
| 3 | State files valid, WIP = 1, evidence real | `make check-state` | ★ |
| 4 | Progress recorded if code changed | `claude-progress.md` updated | ★ |
| 5 | No debug leftovers in `app/` | no `print(`, `breakpoint()`, `pdb` | ★ |
| 6 | No stray files | no `*.orig`, `*.rej`, `*.bak`, `scratch*`, `tmp_*` | ★ |
| 7 | No merge-conflict markers | `<<<<<<<` / `>>>>>>>` | ★ |
| 8 | `session-handoff.md` names the exact next step | read it as a stranger would | |
| 9 | Work is committed, or the handoff says why not | `git status` | |
| 10 | Nothing half-applied | no migration created but not run; no feature `passing` without verify | |
| 11 | Background processes stopped | no stray `uvicorn`/`docker compose run` | |

**Failure mode this prevents:** the next session spends its first 20 minutes discovering
that the last one left a red test, a scratch file and a migration that never ran.
