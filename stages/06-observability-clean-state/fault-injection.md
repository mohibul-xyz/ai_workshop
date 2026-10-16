# Fault injection: debug from logs only

Goal: the agent diagnoses a broken stack **using only what the harness exposes**
(`make logs`, `docker compose logs`, `/health`, `runs/verify-*.log`) — not by reading `.env`
(it is denied) and not by you telling it the answer.

## Inject (facilitator or partner, out of the agent's sight)

```bash
# Wrong database host (a typo in an env var)
echo 'DATABASE_URL=postgresql+psycopg://taskhub:taskhub@dbb:5432/taskhub' >> .env
docker compose up -d --force-recreate api
```

Other faults to try:

| Fault | Command | Symptom in logs |
|---|---|---|
| Wrong DB password | `DATABASE_URL=...taskhub:wrong@db...` in `.env` | `password authentication failed` |
| Migrations not applied | `docker compose run --rm tools alembic downgrade -1` | `UndefinedColumn` on task requests (500) |
| Bad log level | `LOG_LEVEL=LOUD` in `.env` | api exits at startup: `Unknown level` |

## Prompt the agent

> "`make verify` fails at the system layer. Find out why from the logs and tell me the fix.
> Don't change code unless the logs show a code bug."

## What good looks like
1. Runs `make verify` (or reads the latest `runs/verify-*.log`) → layer 3 failed.
2. Runs `make logs` / `docker compose logs api` → finds the JSON line with
   `"event": "health"` / `"database unreachable"` and the `error` field.
3. Correlates by `request_id` with the failing smoke check.
4. Concludes "the API cannot resolve host `dbb`; `DATABASE_URL` in `.env` is wrong" and asks
   the human to fix `.env` (it may not read or edit it — `guard_bash`/`guard_files` and
   permissions block that).

## Clean up
```bash
sed -i '/dbb:5432/d' .env && docker compose up -d --force-recreate api
```
Then end the session with the `handoff` skill and `make clean-state`.
