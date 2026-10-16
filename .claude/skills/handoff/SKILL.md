---
name: handoff
description: End-of-session routine for TaskHub. Use when the user says handoff, wrap up, end session, stop for today, or before the context is cleared. Records verified progress, writes the handoff note, checks the repo is clean, and commits.
---

# Handoff (end every session clean)

The next session starts with **no memory** of this one. It only sees the repo. Write what it
needs, and only what you **verified**.

## 1. Re-verify the current state
```bash
make check          # fast gate
make check-state    # feature_list.json valid, WIP = 1
```
If you finished a feature, run `make verify` and keep the log path it prints.
Never mark anything passing on a red check.

## 2. Update `feature_list.json`
- The active feature's `status`: `passing` (only with `make verify` green), `in_progress`
  (not finished), `blocked` (needs a human; say why in `notes`).
- `evidence`: the verify log path and the test names (`tests/test_x.py::test_y`) that prove it.
  For a passing feature, copy the log: `cp runs/verify-<ts>.log evidence/<ID>-verify.log`.
- `notes`: one line on where the work stands.

## 3. Update `claude-progress.md`
- Rewrite **Current verified state** (baseline, active feature, known issues, last verify log).
- Add a session record at the top of **Session records** using the template in the file:
  goal, done (verified by …), not done / next step, evidence, decisions / surprises.

## 4. Overwrite `session-handoff.md`
Fill every bullet: active feature, state of the work, **exact next step** (a command or file),
commands to re-verify, open questions for a human, and what *not* to do.

## 5. Clean state
```bash
make clean-state
```
Fix everything it reports: stray debug prints, `breakpoint()`, scratch files, `*.orig`,
an un-updated progress file, failing tests. Remove temporary files you created.

## 6. Commit (on the feature branch)
Check `git branch --show-current` is `feat/<ID>-<slug>`, never `main` (if you are on `main`,
`git switch -c feat/<ID>-<slug>` first — uncommitted changes move with you). Stage only the
files for this feature plus the three state files, then
`git commit -m "<ID>: <what changed> (handoff)"`. A human approves the commit (permissions ask).

## 7. Open the PR (feature passing only)
If the feature is now `passing`, run the `open-pr` skill. If it is still `in_progress`, leave
the commit on the branch; the next session continues there.

## 8. Report to the user
Three lines: what is done (with evidence and the PR URL, if any), what is next, what needs a human.
