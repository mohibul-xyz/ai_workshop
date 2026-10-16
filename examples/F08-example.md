# Example: building F08 (task assignee) with the harness

A worked walkthrough of the full feature loop, from an empty session to a PR on `main`.
F08 is an **illustrative** feature: it is not in `feature_list.json` yet. Follow these steps to
build it for real, or use them as the template for any new feature.

**F08 — Task assignee.** Tasks get an optional `assignee` (a free-text name). It can be set
on create, changed or cleared with `PATCH`, and used as a filter:
`GET /api/v1/projects/{id}/tasks?assignee=alice`.

F08 needs a migration, so it exercises every harness piece: state, branch, spec, plan,
the `write-migration` skill, hooks, three-layer verify, reviewer, handoff and PR.

```
 1 start ─► 2 branch ─► 3 register ─► 4 spec ─► 5 plan ─► 6 tests (red) ─► 7 migration
   ─► 8 code ─► 9 make check ─► 10 smoke ─► 11 verify ─► 12 review ─► 13 evidence ─► 14 handoff ─► 15 PR
```

Legend: **You:** what you type or do · **Prompt:** what you say to Claude ·
**Harness:** what the harness does on its own · **Gate:** what must be green before moving on.

---

## 1. Start the session and check the baseline

**You:**
```bash
claude        # in the repo root
```
**Harness:** the `SessionStart` hook prints the current verified state, the active feature and
`git status` into Claude's context.

**Prompt:** "Run ./init.sh and tell me the baseline."

**Gate:** `init.sh` ends with `Nothing left to do: every feature is passing` (or names an
`in_progress` feature, which you finish first because of WIP = 1). If it prints
`BASELINE IS RED`, fix that before anything else.

## 2. Create the feature branch

**Prompt:** "Create the branch for F08."

```bash
git switch main && git pull --ff-only
git switch -c feat/F08-task-assignee
```

**Harness:** hard constraint 10 in `CLAUDE.md`: never commit to `main`. The permission matrix
asks you before `git switch`/`git pull`; approve them.

## 3. Register F08 in `feature_list.json`

**Prompt:** "Add F08 'Task assignee' to feature_list.json as in_progress."

```json
{
  "id": "F08",
  "priority": 8,
  "area": "tasks",
  "title": "Task assignee",
  "user_visible_behavior": "Tasks have an optional assignee; GET .../tasks?assignee=alice returns that person's tasks.",
  "status": "in_progress",
  "verification": ["make migrate-check", "make lab-spec", "make verify"],
  "evidence": [],
  "notes": "Spec-driven; needs migration 0004."
}
```

**Harness:** `post_state_check` runs `check_state.py` on save. A second `in_progress` feature
or a `passing` with no evidence is rejected immediately.

**Gate:** `make check-state` → `OK`.

## 4. Write the spec (planner role, no code)

**Prompt:** "Use the write-spec skill for F08."

**Harness:** the `write-spec` skill writes `specs/F08-task-assignee.md` from
`specs/_template.md`: problem, user stories, API contract, data model, Given/When/Then
acceptance criteria, non-goals and open questions.

What a good F08 spec contains (abridged):

| Section | Content |
|---|---|
| API contract | `assignee: string \| null` on `TaskCreate`, `TaskUpdate`, `TaskRead`; `?assignee=` on the list endpoint; `404` missing project; `422` invalid value |
| Data model | `tasks.assignee VARCHAR(100) NULL` + index `ix_tasks_assignee`; migration `0004_add_task_assignee` (nullable, so no backfill) |
| Non-goals | users table, auth, multiple assignees, partial-name search |

```markdown
- **AC1 — create_with_assignee**
  Given a project
  When I POST a task with "assignee": "alice"
  Then the response is 201 and the body has "assignee": "alice".
- **AC2 — assignee_defaults_to_null**      (field present as null, not omitted)
- **AC3 — patch_sets_and_clears_assignee** (PATCH "bob" → "bob"; PATCH null → null)
- **AC4 — filter_by_assignee**             (only alice's tasks, id ASC)
- **AC5 — filter_combines_with_other_filters** (AND with status/max_priority/overdue/tag/q)
- **AC6 — filter_applies_before_pagination**   (total counts every match)
- **AC7 — unknown_assignee_returns_empty_page** (200, items [], total 0)
- **AC8 — invalid_assignee_rejected**      (empty, whitespace-only or > 100 chars → 422)
- **AC9 — missing_project_returns_404**
```

**You (human decision):** answer the open questions in the spec, for example:
- Is the filter case-sensitive? *Decision: exact match after trimming, case-sensitive.*
- Is the name trimmed on write? *Decision: yes; whitespace-only → 422.*

Then set `Status: approved` at the top. **The spec is the contract**: tests, code and the
reviewer are all judged against it.

## 5. Plan in plan mode

**You:** press **Shift+Tab** to enter plan mode.
**Prompt:** "Plan F08 from specs/F08-task-assignee.md. Write specs/F08-task-assignee.plan.md."

Expected plan shape (same as `specs/F07-task-search.plan.md`):

| # | Step | Files | ACs | Verify with |
|---|---|---|---|---|
| 1 | Tests `test_ac1_…`–`test_ac9_…`, written first | `tests/test_assignee.py` | all | `make test` (red), `make lab-spec` |
| 2 | Model + migration via `write-migration` | `app/models.py`, `migrations/versions/0004_add_task_assignee.py` | AC1–AC3 | `make migrate-check` |
| 3 | Schemas | `app/schemas.py` | AC1–AC3, AC8 | API tests |
| 4 | Service filter | `app/services/tasks.py` | AC4–AC7 | API tests |
| 5 | Route query param | `app/api/tasks.py` | AC4, AC8, AC9 | API tests |
| 6 | Smoke check | `scripts/smoke_e2e.py` | AC1, AC4 | `make verify` (system layer) |
| 7 | Verify, review, state | `feature_list.json`, `claude-progress.md` | — | `EVIDENCE=F08 make verify` |

**You:** check the plan touches **only** F08 files (hard constraint 6), then approve.

## 6. Write the tests first, and see them fail

**Prompt:** "Do step 1 of the plan."

**Harness:** `post_edit_lint` runs ruff on every saved file and feeds errors back straight away.

**Gate:**
```bash
make lab-spec     # 9/9 ACs have a test_ac<N>_<slug>
make test         # the new tests FAIL — that is the point (docs/testing-standards.md)
```
A test that passes before the change proves nothing. Rewrite it.

## 7. Model + migration with the `write-migration` skill

**Prompt:** "Use the write-migration skill for step 2."

**Harness:**
- The skill edits `app/models.py`:
  `assignee: Mapped[str | None] = mapped_column(String(100), index=True)`.
- It runs `make migration name=add_task_assignee`, which **asks** you, then reviews the
  autogenerated `0004_add_task_assignee.py` line by line: `down_revision = "0003"`, index name
  `ix_tasks_assignee`, and a `downgrade()` that drops the index and then the column.
- If Claude tries to "fix" `0003_add_tags.py` instead, `guard_files` **blocks** the edit:
  committed migrations are immutable.

**Gate:**
```bash
make migrate-check   # static rules + upgrade → downgrade → upgrade on taskhub_migcheck
```

## 8. Schemas, service, route

**Prompt:** "Do steps 3–5 of the plan."

**Where the code goes** (from `docs/architecture.md` and `docs/api-conventions.md`):
- `app/schemas.py`: `assignee: str | None` on Create/Update/Read, trimmed, 1–100 characters.
  Pydantic v2 only.
- `app/services/tasks.py`: add `assignee` to `tasks_query` as `Task.assignee == assignee`.
  It is a SQLAlchemy expression, never formatted SQL, applied before pagination.
- `app/api/tasks.py`: `assignee: str | None = Query(None, …)`, passed through to the service.

**Harness:** these edits are allowed without a prompt (`Edit(./app/**)`). `guard_bash`
watches every shell command.

## 9. Fast gate

**Prompt:** "Run make check."

**Gate:** `make check` (lint, mypy --strict, tests) is green, and every F08 test now passes.

**Harness:** if Claude tries to finish while `app/` or `tests/` changed and `make check` is red,
the `Stop` hook refuses and sends the failure back: **no victory without green**.

## 10. System-layer smoke check

**Prompt:** "Do step 6: add an F08 check to scripts/smoke_e2e.py."

Add one or two HTTP checks against the real stack: create a task with an assignee, filter by
it. Editing `scripts/` **asks** you first.

## 11. Three-layer verify, with evidence

**Prompt:** "Run EVIDENCE=F08 make verify."

**Gate:** the last lines read:
```
VERIFY: static=pass behaviour=pass system=pass
evidence: evidence/F08-verify.log
RESULT: PASS — all three layers green.
```
If it reports `RESULT: FAIL at layer '…'`, fix that layer and rerun. Never move on with a red
layer.

## 12. Independent review (maker ≠ checker)

**Prompt:** "Use the reviewer agent to review F08 against specs/F08-task-assignee.md."
Then: "Use the review-diff skill on main...HEAD."

**Harness:**
- The `reviewer` subagent is read-only. It scores the change with `evaluator-rubric.md`
  (0–12) and returns **accept / revise / block**.
- `review_diff.py` flags deleted tests, `skip`, broad `except`, out-of-scope files,
  migration edits and secrets.

**Gate:** verdict **accept**. On **revise**, fix the findings and go back to step 9.
On **block**, stop and discuss with a human.

## 13. Record the evidence

**Prompt:** "Mark F08 passing with evidence."

```json
"status": "passing",
"evidence": [
  "evidence/F08-verify.log",
  "specs/F08-task-assignee.md",
  "migrations/versions/0004_add_task_assignee.py",
  "tests/test_assignee.py::test_ac1_create_with_assignee",
  "tests/test_assignee.py::test_ac4_filter_by_assignee",
  "tests/test_assignee.py::test_ac8_invalid_assignee_rejected"
]
```

**Harness:** `check_state.py` rejects any evidence path that does not exist, so "done" can't
be claimed on confidence.

## 14. Handoff: commit on the branch

**Prompt:** "handoff"

**Harness:** the `handoff` skill:
1. Re-runs `make check` and `make check-state`.
2. Updates `claude-progress.md` (current verified state + a session record) and
   `session-handoff.md`.
3. Runs `make clean-state`: no debug prints, stray files or conflict markers; tests pass; the
   stack starts.
4. Commits on `feat/F08-task-assignee` (**asks** you): `F08: task assignee (handoff)`.

## 15. Open the PR

**Harness:** the `open-pr` skill (the handoff calls it because F08 is `passing`):
1. Checks you are on the feature branch, the tree is clean and F08 has evidence.
2. Brings the branch up to date with `origin/main` by merging (reruns verify if `main` moved).
3. Fills `.github/pull_request_template.md` into `runs/pr-F08.md`: summary, changes, verify
   result, failing-before tests, reviewer verdict, scanner findings, migration risk.
4. Runs `git push -u origin feat/F08-task-assignee` and
   `gh pr create --base main --title "F08: Task assignee" --body-file runs/pr-F08.md`
   (both **ask** you).

**You:** review the PR on GitHub and merge it yourself. Claude never merges its own PR.

---

## If the session ends halfway

Run **handoff** anyway. F08 stays `in_progress`, the work is committed on the branch, and
`session-handoff.md` names the exact next step. In the next session:

```bash
claude                          # SessionStart hook shows F08 in progress
```
**Prompt:** "continue". Claude reads the state, switches to `feat/F08-task-assignee` and
picks up from the next plan step, with no briefing needed.

## What stops you when you go off the path

| You (or Claude) try to… | What happens | Enforced by |
|---|---|---|
| Start F09 while F08 is `in_progress` | `check_state` fails on save: WIP = 1 | `post_state_check` hook |
| Edit `0003_add_tags.py` | Blocked: "create a new revision" | `guard_files` hook |
| Read the hidden benchmark tests or `.env` | Denied | permission matrix |
| `rm -rf`, `git reset --hard`, `alembic downgrade base` | Blocked, with what to do instead | `guard_bash` hook |
| Stop while tests are red | Refused: "keep working" | `Stop` hook (`stop_gate`) |
| Mark F08 `passing` with no or missing evidence | Rejected | `check_state.py` |
| Commit or push | Asks a human first | permission matrix (`ask`) |
| Skip a test with `xfail` | Flagged HIGH in review | `review_diff.py`, reviewer |

## Variations

- **Small change with no schema change** (like F07): skip step 7. A spec is still worth
  it if there are more than ~3 behaviours.
- **Hands-on approval** (topic 6): stay in the default permission mode and approve each plan
  step separately, one commit per approved step (see
  `stages/04-scope-human-in-the-loop/approval-checklist.md`).
- **Autonomous:** after an approved spec, write `goals/F08-task-assignee.goal.md` in the shape
  of `goals/F06-pagination.goal.md` and run
  `make goal-loop GOAL=goals/F08-task-assignee.goal.md BUDGET_USD=3` (costs API money).
  Migrations are denied to the unattended agent, so do step 7 yourself first, or let the loop
  stop with `NEEDS_HUMAN`. Review the loop's branch, then run `open-pr`.

## One-screen checklist

- [ ] `./init.sh` green · on `feat/F08-task-assignee` · F08 `in_progress` (only one)
- [ ] Spec approved, open questions answered · plan approved, F08 files only
- [ ] Tests written first and seen failing · `make lab-spec` 9/9
- [ ] `make migrate-check` green · `make check` green
- [ ] `EVIDENCE=F08 make verify` → 3/3 layers · reviewer **accept**
- [ ] F08 `passing` with real evidence · `make check-state` OK
- [ ] `handoff` → `make clean-state` green, committed on the branch
- [ ] `open-pr` → PR to `main` with the template filled · a human merges
