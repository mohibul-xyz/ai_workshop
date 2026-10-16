#!/usr/bin/env bash
# init.sh — the initialization phase (course L6): install, verify the baseline, show the next task.
# Run at the start of every session BEFORE changing anything. Safe to re-run.
set -euo pipefail
cd "$(dirname "$0")"

say() { printf '\n\033[1m==> %s\033[0m\n' "$*"; }

say "1/5 Tooling"
for bin in docker git make python3; do
  command -v "$bin" >/dev/null || { echo "missing: $bin"; exit 1; }
done
docker compose version >/dev/null || { echo "docker compose v2 is required"; exit 1; }

say "2/5 Install (images + host .venv for hook linting)"
make -s setup

say "3/5 Start the stack"
make -s up
python3 - <<'EOF'
import json, urllib.request
print("health:", json.load(urllib.request.urlopen("http://localhost:8000/health", timeout=5)))
EOF

say "4/5 Verify the baseline (make check + state)"
if ! make -s check; then
  echo
  echo "BASELINE IS RED. Fix or report this before starting new work (course L6)."
  exit 1
fi
python3 scripts/check_state.py

say "5/5 Next feature"
python3 - <<'EOF'
import json
feats = json.load(open("feature_list.json"))["features"]
active = [f for f in feats if f["status"] == "in_progress"]
nxt = active or sorted((f for f in feats if f["status"] == "not_started"), key=lambda f: f["priority"])
if not nxt:
    print("Nothing left to do: every feature is passing.")
else:
    f = nxt[0]
    print(f"{'CONTINUE' if active else 'NEXT'}: {f['id']} — {f['title']}")
    print(f"  behaviour:    {f['user_visible_behavior']}")
    print(f"  verification: {', '.join(f['verification'])}")
    if f.get("notes"):
        print(f"  notes:        {f['notes']}")
EOF
echo
echo "Read session-handoff.md, then plan before editing (WIP = 1)."
