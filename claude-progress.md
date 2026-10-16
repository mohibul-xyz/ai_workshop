# Claude progress log

Durable memory between sessions (course L5). The SessionStart hook prints the
"Current verified state" section into every new session. Update it at the end of
every session with the `handoff` skill — only with facts you **verified**.

## Current verified state
- Baseline: F01–F04 passing; `make verify` green on all three layers (25 tests).
- Active feature: none. Next: F05 (task tags, spec-driven).
- Known issues: none.
- Last verify log: evidence/F04-verify.log

## Session records
<!-- Newest first. One block per session. Template:

### YYYY-MM-DD HH:MM — <feature id> — <one-line outcome>
- Goal:
- Done (verified by …):
- Not done / next step:
- Evidence: runs/verify-…log, tests/…::test_…
- Decisions / surprises:
-->

### 2026-10-17 — F04 — due dates + overdue filter passing
- Goal: F04 in six approved steps (topic 6).
- Done (verified by `EVIDENCE=F04 make verify`): due_at column + migration 0002, schemas, filter, 11 tests.
- Next step: F05 — write specs/F05-task-tags.md with the write-spec skill.
- Evidence: evidence/F04-verify.log, tests/test_due_dates.py
- Decisions / surprises: verify layer 3 caught stale migrations in the dev DB (migrate ran baked image code); fixed in Makefile/compose.

### 2026-10-17 — setup — harness baseline
- Goal: workload + harness in place.
- Done (verified by `make check`): F01–F03 with tests.
- Next step: start F04 with the `write-migration` skill.
- Evidence: tests/test_projects.py, tests/test_tasks.py
