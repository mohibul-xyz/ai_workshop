#!/usr/bin/env python3
"""Validate feature_list.json — the harness's state primitive (course L8).

Rules:
  * schema: every feature has id, priority, area, title, user_visible_behavior, status,
    verification[], evidence[], notes
  * status in {not_started, in_progress, passing, failing, blocked}
  * WIP = 1: at most one feature is in_progress
  * a passing feature has >= 1 verification command and >= 1 evidence entry
  * evidence entries that name a repo path (e.g. tests/test_x.py::test_y, evidence/F04-verify.log)
    must exist — "done" requires evidence, not confidence
  * ids are unique

Usage: python3 scripts/check_state.py [feature_list.json]   (stdlib only)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REQUIRED = {
    "id": str, "priority": int, "area": str, "title": str, "user_visible_behavior": str,
    "status": str, "verification": list, "evidence": list, "notes": str,
}
STATUSES = {"not_started", "in_progress", "passing", "failing", "blocked"}
PATH_RE = re.compile(r"^((?:app|tests|evidence|runs|specs|migrations|scripts|docs)/[\w./-]+)")


def validate(data: object, root: Path) -> list[str]:
    errors: list[str] = []
    feats = data.get("features") if isinstance(data, dict) else None
    if not isinstance(feats, list):
        return ['top level must be {"features": [...]}']

    seen: set[str] = set()
    for i, f in enumerate(feats):
        where = f"features[{i}]"
        if not isinstance(f, dict):
            errors.append(f"{where}: must be an object")
            continue
        fid = f.get("id", where)
        for key, typ in REQUIRED.items():
            if key not in f:
                errors.append(f"{fid}: missing '{key}'")
            elif not isinstance(f[key], typ) or (typ is int and isinstance(f[key], bool)):
                errors.append(f"{fid}: '{key}' must be {typ.__name__}")
        if fid in seen:
            errors.append(f"{fid}: duplicate id")
        seen.add(fid)
        status = f.get("status")
        if status not in STATUSES:
            errors.append(f"{fid}: status '{status}' not in {sorted(STATUSES)}")
        if status == "passing":
            if not f.get("verification"):
                errors.append(f"{fid}: passing without a verification command")
            if not f.get("evidence"):
                errors.append(f"{fid}: passing without evidence — run the verification and "
                              "record the log/test names")
        for ev in f.get("evidence") or []:
            m = PATH_RE.match(str(ev))
            if m:
                rel = m.group(1).split("::")[0]
                if not (root / rel).exists():
                    errors.append(f"{fid}: evidence path does not exist: {rel}")

    active = [f.get("id") for f in feats if isinstance(f, dict) and f.get("status") == "in_progress"]
    if len(active) > 1:
        errors.append(f"WIP=1 violated: {len(active)} features in_progress ({', '.join(map(str, active))})"
                      " — finish or hand off one before starting another")
    return errors


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "feature_list.json")
    if not path.exists():
        print(f"FAIL {path}: not found")
        return 1
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"FAIL {path}: invalid JSON: {exc}")
        return 1
    errors = validate(data, path.resolve().parent)
    if errors:
        print(f"FAIL {path}")
        for e in errors:
            print(f"  - {e}")
        return 1
    feats = data["features"]
    counts: dict[str, int] = {}
    for f in feats:
        counts[f["status"]] = counts.get(f["status"], 0) + 1
    print(f"OK   {path}: {len(feats)} features ("
          + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())) + ")")
    return 0


if __name__ == "__main__":
    sys.exit(main())
