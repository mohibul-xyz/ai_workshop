# Findings sheet — reading AI-generated code

Read each file in `ai_written/` **before running anything**. For every flaw you find, fill one
row: where it is, which category, the evidence (the line, the error, or the failing test), and
the fix. Then fix the code and make the tests pass:

```bash
make stage0-check                 # tests vs ai_written/ (start: 12 failing) + this sheet complete
```

Categories: **invented API** (does not exist / wrong library) · **weak logic** (runs, wrong
answer on some inputs) · **hidden bug** (passes the happy path, fails on real data or later).

| # | Location (file:line) | Category | Evidence | Fix |
|---|---|---|---|---|
| 1 | export_tasks.py: | | | |
| 2 | export_tasks.py: | | | |
| 3 | export_tasks.py: | | | |
| 4 | overdue.py: | | | |
| 5 | overdue.py: | | | |
| 6 | overdue.py: | | | |
| 7 | retry.py: | | | |
| 8 | retry.py: | | | |
| 9 | retry.py: | | | |
| 10 | retry.py: | | | |
| 11 | search.py: | | | |

## Reflection
- Which flaw would a quick review have missed? Why did the code *look* right?
- Which flaws would the happy-path test have caught? Which only real data would expose?
- What would you put in the harness so the agent cannot ship these again (a hook, a lint rule,
  a test, a CLAUDE.md constraint)?
