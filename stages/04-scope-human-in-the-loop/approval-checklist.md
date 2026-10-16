# F04 approval checklist (human-in-the-loop)

Build F04 (due dates + `?overdue=true`) in **six steps**. Stay in the default permission mode so
every edit asks. After each step, check the "approve when" column **yourself** before saying yes.
Reject at least once with a reason ("use `AwareDatetime`, see docs/api-conventions.md") and watch
the agent correct itself.

| Step | Agent does | Approve when (you checked) | Reject if |
|---|---|---|---|
| 1 | **Plan only** (plan mode: Shift+Tab) | Plan touches only F04; lists files (`app/models.py`, migration, `app/schemas.py`, `app/services/tasks.py`, `app/api/tasks.py`, `tests/test_due_dates.py`) and the tests it will write | It mentions tags, pagination, refactors, or "while I'm here" |
| 2 | Model field + migration via `write-migration` skill | `git diff` shows one nullable `timestamptz` column + index; `make migrate-check` → both OK lines | It edits `0001_initial.py`, uses naive `DateTime`, NOT NULL without default, empty `downgrade()` |
| 3 | Schemas | `due_at` in Create / Update / Read; request type rejects naive datetimes (`AwareDatetime`); name ends in `_at` | `due_date`, `str` type, or a required field |
| 4 | Service filter logic | `due_at < now` (strict), `now` is timezone-aware, `status != done` excluded, filter is in `app/services/` not the router | `datetime.utcnow()`, `<=`, done tasks included, SQL strings |
| 5 | Tests | Tests **fail before step 4 and pass after** (ask the agent to prove it); boundary (due == now), done excluded, timezone, combine with `max_priority`, naive input → 422 | Only happy path; assertions on status code only; sleeps |
| 6 | `feature_list.json` + evidence | `EVIDENCE=F04 make verify` green on all 3 layers; `evidence/F04-verify.log` exists; `make check-state` OK | `passing` before verify is green; invented evidence paths |

**Commit after every approved step** (`git commit` asks for approval):
`F04 step N: <what>`. Reference history: `git log --oneline --grep "F04 step"`.

## Reflection (2 minutes)
- Which step did you reject, and what did the agent change?
- What would have slipped through if you had approved without running the command?
- Which of these approvals could become an automated check (a hook or a test)?
