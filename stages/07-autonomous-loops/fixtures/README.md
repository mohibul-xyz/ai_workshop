Recorded (illustrative) outputs for `DRY_RUN=1 scripts/run_goal_loop.sh` — the loop logic,
stop conditions and cost accounting can be tested with no API key and no spend.
Shape matches `claude -p --output-format json` (result, total_cost_usd, num_turns, usage).
Scenario: iteration 1 → verify fails (limit=0 accepted), reviewer says revise;
iteration 2 → fixed, verify passes, reviewer accepts → DONE.
