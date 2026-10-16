# Diff review checklist

Walk it **in order** for every PR, branch or autonomous-run result. The scanner
(`python3 scripts/review_diff.py <diff> --scope app/,tests/`) points at lines; this checklist
makes you judge them. Write each finding as `file:line · category · evidence · fix`.

## 1. Scope
- [ ] Does every changed file belong to the stated goal / feature?
- [ ] Any reformatting, renames, `# noqa`, or "while I was there" changes?
- [ ] Does the description match the diff (count the changes it claims)?

## 2. Behaviour change
- [ ] Defaults, ordering, limits, status codes, error shapes — unchanged unless asked?
      Compare with `docs/api-conventions.md`.
- [ ] Do constants agree with their comments (off-by-one)?
- [ ] "Refactor" / "no behaviour change" — prove it: same inputs, same outputs?

## 3. Tests
- [ ] New behaviour has tests that would **fail without** the change?
- [ ] Any assertion removed, loosened (`sorted()`, `in`, `>=`), or turned into status-only?
- [ ] Any `skip`, `xfail`, deleted test, or test edited in the same PR as the code it tests?
- [ ] "Tests still pass" — *because* the tests were changed?

## 4. Data and migrations
- [ ] Committed migrations edited? (Never — new revision.)
- [ ] `drop_column` / `drop_table` / type narrowing — approved by a human, data backed up?
- [ ] `downgrade()` reverses `upgrade()` exactly? Not `pass`?
- [ ] Schema change removes a field from the API (breaking)?

## 5. Security
- [ ] SQL built with f-strings / `%` / `+`, or user input inside `text()`?
- [ ] Secrets, tokens, credentials, `.env` contents?
- [ ] Broad `except` swallowing errors; new network calls; `eval`/`exec`?

## 6. Reversibility
- [ ] Can this be rolled back by reverting the commit — including the data?
- [ ] What breaks for existing clients / databases if it ships?

## Verdict
- **accept** — no blocking findings
- **revise** — fixable findings (list them)
- **block** — data loss, security issue, or unapproved scope / behaviour change

Score with `evaluator-rubric.md` and record the verdict in `findings-PR-1xx.md`.
