# Version notes — Claude Code features this harness relies on

Read this when a Claude Code flag, setting or hook behaves unexpectedly. Built and checked
against **Claude Code 2.1.300** (pinned in `Dockerfile.agent`). Facilitators: recheck this
list against `claude --help` and the docs the week before the workshop.

| Feature | Used in | Status on 2.1.300 | If it changed |
|---|---|---|---|
| Hook stdin JSON (`tool_name`, `tool_input`, `hook_event_name`) | `.claude/hooks/_common.py` | Used as documented | Update `read_event` / `tool_input` only |
| PreToolUse exit code 2 = block, stderr → agent | `guard_bash.py`, `guard_files.py` | Used | Switch to JSON `permissionDecision: "deny"` output |
| PostToolUse exit 2 = feedback to agent (edit already applied) | `post_edit_lint.py`, `post_state_check.py` | Used | — |
| Stop hook `{"decision": "block", "reason": …}` + `stop_hook_active` | `stop_gate.py` | Used; loop-safe via `stop_hook_active` | Gate can be disabled with `HARNESS_STOP_GATE=0` |
| SessionStart stdout added to context | `session_start.py` | Used (plain text) | Emit `hookSpecificOutput.additionalContext` JSON instead |
| `$CLAUDE_PROJECT_DIR` in hook commands | `.claude/settings.json` | Used | Use paths relative to the repo root |
| Permission rules `Tool(pattern)`, `Bash(cmd *)`, `Read(./path/**)` | `.claude/settings.json` | Used; the simulator models the same semantics | Re-run `make lab-permissions`; check `/permissions` |
| `permissions.disableBypassPermissionsMode: "disable"` | `.claude/settings.json` | Used | — |
| `permissions.defaultMode` | — | **Not set.** The CLI's mode list is `acceptEdits, auto, bypassPermissions, manual, dontAsk, plan` (no `default`), so we rely on the built-in default | — |
| Skills: `.claude/skills/<name>/SKILL.md` with `name` + `description` frontmatter | 4 skills | Used | — |
| Subagents: `.claude/agents/<name>.md` with `name`, `description`, `tools` | `reviewer.md` | Used | — |
| `claude -p --output-format json` → `result`, `total_cost_usd`, `num_turns`, `usage`, `duration_ms` | `run_goal_loop.sh`, `run_benchmark.sh` | Used | Update `jget` field names / `compare_runs.py` |
| `--max-budget-usd` | loop + benchmark | Listed in `claude --help` | — |
| `--max-turns` | loop + benchmark | **Not listed in `--help`** (historically a hidden print-mode flag) | Set `TURNS_FLAG=` (empty) to drop it; the budget cap still applies |
| `--permission-mode acceptEdits` / `dontAsk` | maker / checker | Both listed | — |
| `--allowedTools` / `--disallowedTools` / `--settings` | checker / maker | Listed | — |
| `/goal` interactive command | Stage 7 alternative | **Unverified** — the loop script does not depend on it | Paste the goal file as the first prompt instead |
| `/context`, `/compact`, `/clear` | Stage 8 | Interactive only | — |
| `@path` imports in CLAUDE.md | `variants/bloated` | Used to show import cost | `context_report.py` resolves them itself |

## Token counting
`scripts/context_report.py` calls `POST /v1/messages/count_tokens` with `ANTHROPIC_API_KEY`
over stdlib `urllib` (the host has no SDK on purpose). Counts are model-specific: set `MODEL`
to the model the benchmark runs; default `claude-opus-5-5`. Without a key it prints a chars/4
estimate marked `~`.
