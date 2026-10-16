---
name: open-pr
description: Push a finished TaskHub feature branch and open a pull request to main with an evidence-based description. Use when a feature is passing and handed off, or when asked to open, create or raise a PR. Fills .github/pull_request_template.md from verify logs, tests, the reviewer verdict and the risk scanner.
---

# Open a PR (one feature → one branch → one PR)

`main` only changes through reviewed PRs. You open the PR; a **human** reviews and merges it
(maker ≠ checker). Never merge your own PR, never push to `main`, never force-push.

## 1. Preconditions — stop and fix if any fails
```bash
git branch --show-current     # must be feat/<ID>-<slug>, never main
git status --short            # must be empty (run the handoff skill first)
make check-state              # the feature is passing with evidence
```
The feature's `evidence/<ID>-verify.log` must exist and end with `RESULT: PASS`.

## 2. Make sure the branch is current with main
```bash
git fetch origin
git log --oneline HEAD..origin/main     # empty = up to date
```
If `main` moved: `git merge origin/main` (not rebase — rewriting pushed history would need a
force-push, which is denied), resolve conflicts, then rerun `EVIDENCE=<ID> make verify` and
commit the refreshed evidence.

## 3. Gather the facts for the description
```bash
git log --oneline main..HEAD
git diff --stat main...HEAD
python3 scripts/review_diff.py --git main...HEAD
tail -n 5 evidence/<ID>-verify.log
```
If the `reviewer` subagent has not reviewed this branch yet, run it now against the spec or
goal. Do not open the PR on a `block` verdict; on `revise`, fix the findings first.

## 4. Write the description
Copy `.github/pull_request_template.md` to `runs/pr-<ID>.md` (git-ignored) and fill **every**
section:
- Cite evidence for each claim: log path, test names, scanner counts, rubric score.
- Every HIGH scanner finding gets one line: why it is fine, or how it was fixed.
- Name anything out of scope or left for later. Do not paste whole logs.
- Delete the HTML comments; no placeholder may remain.

## 5. Push and create the PR (both ask a human)
```bash
git push -u origin feat/<ID>-<slug>
gh pr create --base main --head feat/<ID>-<slug> \
  --title "<ID>: <feature title>" --body-file runs/pr-<ID>.md
```

## 6. Report
The PR URL, the verify result and the reviewer verdict, in three lines. The human merges.

## Autonomous-loop output
The loop's `goal/<name>-<id>` branch lives in its sandbox clone and cannot push. After a human
has reviewed it, bring it into the repo under the feature-branch name and run this skill:
`git fetch .worktrees/goal-<id> goal/<name>-<id>:feat/<ID>-<slug> && git switch feat/<ID>-<slug>`.
