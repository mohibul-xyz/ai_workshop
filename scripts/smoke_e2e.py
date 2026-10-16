#!/usr/bin/env python3
"""Layer 3 (system) smoke test: exercise the real running stack over HTTP. Stdlib only.

Always checks the baseline (health, F01–F03, request ids). For F04–F06 it checks the
behaviour of every feature that feature_list.json claims is `passing` — so a false
"passing" claim fails verification here, against real Postgres.

Usage: python3 scripts/smoke_e2e.py [--base-url http://localhost:8000]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = "http://localhost:8000"
CHECKS: list[tuple[str, bool, str]] = []


def call(method: str, path: str, body: Any = None) -> tuple[int, Any, dict[str, str]]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(  # noqa: S310 - local smoke test
        BASE + path,
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-Request-ID": f"smoke-{uuid.uuid4().hex[:8]}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            raw = resp.read()
            return resp.status, (json.loads(raw) if raw else None), dict(resp.headers)
    except urllib.error.HTTPError as err:
        raw = err.read()
        try:
            payload = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            payload = raw.decode(errors="replace")
        return err.code, payload, dict(err.headers)


def check(name: str, ok: bool, detail: Any = "") -> bool:
    CHECKS.append((name, ok, "" if ok else str(detail)[:300]))
    return ok


def items(body: Any) -> list[dict[str, Any]]:
    """List endpoints return a list, or the F06 pagination envelope."""
    if isinstance(body, dict) and "items" in body:
        return list(body["items"])
    return list(body or [])


def wait_for_health(timeout: float = 30) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            status, body, _ = call("GET", "/health")
            if status == 200:
                return check("GET /health → 200 ok", body.get("status") == "ok", body)
        except (urllib.error.URLError, ConnectionError, OSError):
            pass
        time.sleep(1)
    return check("GET /health → 200 ok", False, f"no healthy response from {BASE} in {timeout}s")


def baseline() -> int:
    name = f"smoke-{uuid.uuid4().hex[:8]}"
    s, proj, headers = call("POST", "/api/v1/projects", {"name": name})
    check("F01 create project → 201", s == 201, proj)
    check(
        "request id echoed in X-Request-ID",
        any(k.lower() == "x-request-id" for k in headers),
        headers,
    )
    pid = int(proj["id"])
    s, body, _ = call("POST", "/api/v1/projects", {"name": name})
    check("F01 duplicate name → 409", s == 409, body)
    s, body, _ = call("GET", "/api/v1/projects?limit=100")
    check("F01 list projects → 200", s == 200, body)

    s, t1, _ = call("POST", f"/api/v1/projects/{pid}/tasks", {"title": "a", "priority": 1})
    check("F02 create task → 201", s == 201, t1)
    s, t2, _ = call(
        "POST", f"/api/v1/projects/{pid}/tasks", {"title": "b", "priority": 4, "status": "done"}
    )
    s, body, _ = call("PATCH", f"/api/v1/tasks/{t1['id']}", {"status": "in_progress"})
    check("F02 patch task → in_progress", s == 200 and body["status"] == "in_progress", body)
    s, body, _ = call("GET", f"/api/v1/projects/{pid}/tasks?status=done")
    check("F03 filter status=done", s == 200 and [t["title"] for t in items(body)] == ["b"], body)
    s, body, _ = call("GET", f"/api/v1/projects/{pid}/tasks?max_priority=1")
    check(
        "F03 filter max_priority=1", s == 200 and [t["title"] for t in items(body)] == ["a"], body
    )
    s, _, _ = call("DELETE", f"/api/v1/tasks/{t2['id']}")
    check("F02 delete task → 204", s == 204, s)
    s, _, _ = call("GET", f"/api/v1/tasks/{t2['id']}")
    check("F02 deleted task → 404", s == 404, s)
    return pid


def f04(pid: int) -> None:
    past = (datetime.now(UTC) - timedelta(days=2)).isoformat()
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    call("POST", f"/api/v1/projects/{pid}/tasks", {"title": "late", "due_at": past})
    call(
        "POST",
        f"/api/v1/projects/{pid}/tasks",
        {"title": "late-done", "due_at": past, "status": "done"},
    )
    call("POST", f"/api/v1/projects/{pid}/tasks", {"title": "later", "due_at": future})
    s, body, _ = call("GET", f"/api/v1/projects/{pid}/tasks?overdue=true")
    check(
        "F04 overdue=true returns only open past-due tasks",
        s == 200 and [t["title"] for t in items(body)] == ["late"],
        body,
    )


def f05(pid: int) -> None:
    s, task, _ = call(
        "POST", f"/api/v1/projects/{pid}/tasks", {"title": "tagged", "tags": ["urgent", "ops"]}
    )
    check(
        "F05 create task with tags",
        s == 201 and sorted(task.get("tags", [])) == ["ops", "urgent"],
        task,
    )
    s, body, _ = call("GET", f"/api/v1/projects/{pid}/tasks?tag=urgent")
    check(
        "F05 filter tag=urgent", s == 200 and [t["title"] for t in items(body)] == ["tagged"], body
    )


def f06(pid: int) -> None:
    for i in range(3):
        call("POST", f"/api/v1/projects/{pid}/tasks", {"title": f"page-{i}"})
    s, body, _ = call("GET", f"/api/v1/projects/{pid}/tasks?limit=2&offset=0")
    ok = (
        s == 200 and isinstance(body, dict) and {"items", "total", "limit", "offset"} <= body.keys()
    )
    check("F06 envelope {items,total,limit,offset}", ok, body)
    if ok:
        check("F06 limit honoured", len(body["items"]) == 2 and body["total"] >= 3, body)
    s, body, _ = call("GET", f"/api/v1/projects/{pid}/tasks?limit=0")
    check("F06 limit=0 → 422", s == 422, body)


def main() -> int:
    global BASE
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-url", default=BASE)
    BASE = ap.parse_args().base_url.rstrip("/")

    if wait_for_health():
        try:
            pid = baseline()
            feats = json.loads((ROOT / "feature_list.json").read_text())["features"]
            passing = {f["id"] for f in feats if f["status"] == "passing"}
            for fid, fn in (("F04", f04), ("F05", f05), ("F06", f06)):
                if fid in passing:
                    fn(pid)
        except (KeyError, TypeError, ValueError) as exc:
            check("smoke run completed", False, f"{type(exc).__name__}: {exc}")

    width = max(len(n) for n, _, _ in CHECKS)
    for name, ok, detail in CHECKS:
        print(f"  {'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    failed = [n for n, ok, _ in CHECKS if not ok]
    print(f"smoke_e2e: {len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed against {BASE}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
