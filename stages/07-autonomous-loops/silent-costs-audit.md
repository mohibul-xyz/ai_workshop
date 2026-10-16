# Silent-costs audit (after an autonomous run)

An autonomous loop that "passes" can still cost you. Course L13 names four silent costs.
Fill this in for every loop result **before** merging its branch. Inputs:
`runs/loop-<id>/summary.json`, `runs/loop-<id>/loop-state.md`, the branch diff,
`python3 scripts/review_diff.py --git main...<branch>`, `make audit-report`.

Run: `runs/loop-__________` · branch `goal/________` · status ______ · cost $____ · turns ____

## 1. Verification debt — did anything ship that nobody verified?
| Question | Answer / evidence |
|---|---|
| Which goal requirements have **no** test that would fail without the change? | |
| Did the reviewer's ✅ rely on evidence (command output, `file:line`) or on the maker's claims? | |
| Any verify layer skipped, flaky, or green only because tests were edited? | |

## 2. Comprehension rot — can a human on the team explain the change?
| Question | Answer / evidence |
|---|---|
| Explain the diff in 3 sentences *without* reading the agent's summary. Could you? | |
| Files changed that you did not expect? Abstractions you would not have added? | |
| Would you be comfortable debugging this at 2 a.m.? | |

## 3. Cognitive surrender — did humans stop thinking?
| Question | Answer / evidence |
|---|---|
| Who read the diff line by line? How long did it take? | |
| Were any reviewer findings dismissed without a reason? | |
| Did we accept because "the loop said DONE"? | |

## 4. Token blowout — was the spend proportionate?
| Metric | Value | Note |
|---|---|---|
| Total cost / budget | $ / $ | |
| Iterations used / cap | / | |
| Turns (maker + checker) | | |
| Cost per accepted requirement | $ | |
| Largest single iteration (`maker-N.json` → `usage`) | | cache reads vs fresh input |
| Would a human + agent pair (Stage 4 style) have been cheaper? | | |

## Decision
- [ ] **accept** — merge (rubric score: __ /12)
- [ ] **revise** — rerun the loop with findings added to the goal file / loop memory
- [ ] **block** — human takes over; reason: ______________________

One change to the harness that would have prevented the worst finding: ______________________
