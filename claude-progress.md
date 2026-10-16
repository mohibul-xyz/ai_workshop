# Claude progress log

Durable memory between sessions (course L5). The SessionStart hook prints the
"Current verified state" section into every new session. Update it at the end of
every session with the `handoff` skill — only with facts you **verified**.

## Current verified state
- Baseline: F01–F03 passing; `make check` green (14 tests).
- Active feature: none. Next: F04 (due dates + overdue filter).
- Known issues: none.
- Last verify log: (none yet — run `make verify`)

## Session records
<!-- Newest first. One block per session. Template:

### YYYY-MM-DD HH:MM — <feature id> — <one-line outcome>
- Goal:
- Done (verified by …):
- Not done / next step:
- Evidence: runs/verify-…log, tests/…::test_…
- Decisions / surprises:
-->

### 2026-10-17 — setup — harness baseline
- Goal: workload + harness in place.
- Done (verified by `make check`): F01–F03 with tests.
- Next step: start F04 with the `write-migration` skill.
- Evidence: tests/test_projects.py, tests/test_tasks.py
