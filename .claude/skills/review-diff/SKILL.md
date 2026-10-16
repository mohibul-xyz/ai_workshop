---
name: review-diff
description: Critically review a diff, branch or PR for TaskHub before it is merged. Use when asked to review a PR, a branch, a .diff file, an agent's autonomous-run output, or "what changed". Combines the risk scanner with the human checklist and ends with accept / revise / block.
---

# Review a diff

The scanner finds suspicious **lines**. Only careful reading judges **intent**. Do both.

## 1. Get the diff
- Branch: `git diff main...<branch>` (also `git log main..<branch> --stat`)
- File: `stages/05-verification-specs-diffs/prs/PR-1xx.diff`
- Working tree: `git diff HEAD`

## 2. Run the risk scanner
```bash
python3 scripts/review_diff.py <file.diff | --git main...HEAD> [--scope app/,tests/]
```
Treat every finding as a question, not a verdict.

## 3. Walk the checklist, in order (`stages/05-verification-specs-diffs/review-checklist.md`)
1. **Scope** — does every file belong to the stated goal? Reformatting, renames, unrelated "cleanups"?
2. **Behaviour change** — defaults, ordering, limits, status codes, error shapes. Compare
   with `docs/api-conventions.md`. "Tests still pass" does not mean behaviour is unchanged.
3. **Tests** — were tests added for new behaviour? Were assertions removed or weakened,
   `skip`/`xfail` added? Would the new tests fail without the change?
4. **Data / migrations** — committed migrations edited? `drop_column`/`drop_table`?
   Empty or incomplete `downgrade()`? NOT NULL without default?
5. **Security** — SQL built with f-strings or `%`, secrets, broad `except`, user input in
   `text()`, new network calls.
6. **Reversibility** — can this be rolled back without data loss?

## 4. Verify, don't trust
Apply to a scratch worktree and run the checks when in doubt:
```bash
git worktree add ../review-tmp HEAD && cd ../review-tmp && git apply <diff> && make check
```

## 5. Report
For each finding: `file:line` · category · evidence (quote the line) · required fix.
Then the rubric (`evaluator-rubric.md`, 6 × 0–2) and a verdict:
- **accept** — no blocking findings
- **revise** — fixable findings; list them
- **block** — data loss, security issue, or out-of-scope change that needs a human
