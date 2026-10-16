<!-- Title: "<ID>: <feature title>", e.g. "F07: Search tasks by title".
     Every claim below cites evidence (a log path, a test name, command output). No placeholders. -->

## Feature
- **ID / title:** <!-- F07 — Search tasks by title -->
- **Spec / goal:** <!-- specs/F07-task-search.md, or goals/F07-….goal.md, or "none (small change)" -->
- **Branch:** <!-- feat/F07-task-search -->

## Summary
<!-- 2–4 lines: what changed for the user of the API, and why. -->

## Changes
| File | Change |
|---|---|
| <!-- app/services/tasks.py --> | <!-- title search filter (ILIKE, parameterised) --> |

## Verification
- **`make verify`:** static=… behaviour=… system=… — log: `evidence/<ID>-verify.log`
- **Tests that failed before and pass after:** <!-- tests/test_x.py::test_ac1_… -->
- **Spec coverage (`make lab-spec`):** <!-- N/N acceptance criteria have a test, or n/a -->

## Review
- **Reviewer subagent:** <!-- rubric x/12, verdict accept|revise -->
- **Risk scanner (`python3 scripts/review_diff.py --git main...HEAD`):** <!-- HIGH/MED/LOW counts; one line per HIGH explaining why it is fine or how it was fixed -->

## Risk and rollout
- **Migrations:** <!-- none, or 000N_<slug>.py — round-trip green, downgrade reverses upgrade -->
- **Behaviour changes to existing endpoints:** <!-- none, or what and why -->
- **Out of scope / follow-ups:** <!-- what was deliberately not done -->

## Checklist
- [ ] Diff contains only files this feature needs
- [ ] No test weakened (no deleted assertions, no `skip`/`xfail`)
- [ ] `feature_list.json` status + evidence and `claude-progress.md` updated; `make check-state` green
- [ ] `make clean-state` green
