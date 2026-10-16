"""F04: due dates + ?overdue=true filter."""

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Task, TaskStatus
from app.services.tasks import list_tasks

NOW = datetime(2026, 10, 17, 12, 0, tzinfo=UTC)


def _create(client: TestClient, project_id: int, **fields: object) -> dict[str, object]:
    resp = client.post(f"/api/v1/projects/{project_id}/tasks", json={"title": "t", **fields})
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def test_due_at_round_trips_with_timezone(client: TestClient, project_id: int) -> None:
    task = _create(client, project_id, due_at="2026-10-20T17:00:00+02:00")
    assert datetime.fromisoformat(str(task["due_at"])) == datetime(2026, 10, 20, 15, 0, tzinfo=UTC)


def test_due_at_is_optional_and_null_by_default(client: TestClient, project_id: int) -> None:
    assert _create(client, project_id)["due_at"] is None


def test_naive_due_at_rejected(client: TestClient, project_id: int) -> None:
    resp = client.post(
        f"/api/v1/projects/{project_id}/tasks", json={"title": "x", "due_at": "2026-10-20T17:00:00"}
    )
    assert resp.status_code == 422


def test_due_at_can_be_patched_and_cleared(client: TestClient, project_id: int) -> None:
    task_id = _create(client, project_id)["id"]
    resp = client.patch(f"/api/v1/tasks/{task_id}", json={"due_at": "2026-11-01T00:00:00Z"})
    assert resp.json()["due_at"].startswith("2026-11-01")
    resp = client.patch(f"/api/v1/tasks/{task_id}", json={"due_at": None})
    assert resp.json()["due_at"] is None


def test_overdue_true_returns_open_past_due_tasks(client: TestClient, project_id: int) -> None:
    past = datetime.now(UTC) - timedelta(days=2)
    future = datetime.now(UTC) + timedelta(days=2)
    _create(client, project_id, title="late", due_at=_iso(past))
    _create(client, project_id, title="late-in-progress", due_at=_iso(past), status="in_progress")
    _create(client, project_id, title="later", due_at=_iso(future))
    _create(client, project_id, title="no-date")
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"overdue": "true"})
    assert resp.status_code == 200
    assert [t["title"] for t in resp.json()["items"]] == ["late", "late-in-progress"]


def test_overdue_excludes_done_tasks(client: TestClient, project_id: int) -> None:
    past = datetime.now(UTC) - timedelta(days=2)
    _create(client, project_id, title="done-late", due_at=_iso(past), status="done")
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"overdue": "true"})
    assert resp.json()["items"] == []


def test_overdue_false_returns_the_complement(client: TestClient, project_id: int) -> None:
    past = datetime.now(UTC) - timedelta(days=2)
    _create(client, project_id, title="late", due_at=_iso(past))
    _create(client, project_id, title="done-late", due_at=_iso(past), status="done")
    _create(client, project_id, title="no-date")
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"overdue": "false"})
    assert [t["title"] for t in resp.json()["items"]] == ["done-late", "no-date"]


def test_overdue_combines_with_other_filters(client: TestClient, project_id: int) -> None:
    past = datetime.now(UTC) - timedelta(days=2)
    _create(client, project_id, title="urgent-late", due_at=_iso(past), priority=1)
    _create(client, project_id, title="minor-late", due_at=_iso(past), priority=5)
    resp = client.get(
        f"/api/v1/projects/{project_id}/tasks", params={"overdue": "true", "max_priority": 2}
    )
    assert [t["title"] for t in resp.json()["items"]] == ["urgent-late"]


def test_overdue_boundary_due_exactly_now_is_not_overdue(session: Session, project_id: int) -> None:
    session.add_all(
        [
            Task(project_id=project_id, title="exactly-now", due_at=NOW),
            Task(project_id=project_id, title="1s-ago", due_at=NOW - timedelta(seconds=1)),
        ]
    )
    session.flush()
    titles = [t.title for t in list_tasks(session, project_id, overdue=True, now=NOW)]
    assert titles == ["1s-ago"]


def test_overdue_compares_across_timezones(session: Session, project_id: int) -> None:
    # 13:30 at +02:00 is 11:30 UTC — before NOW (12:00 UTC), so overdue.
    tz = datetime(2026, 10, 17, 13, 30).astimezone().tzinfo  # any aware tz works
    due = datetime(2026, 10, 17, 11, 30, tzinfo=UTC).astimezone(tz)
    session.add(Task(project_id=project_id, title="tz", due_at=due, status=TaskStatus.todo))
    session.flush()
    assert [t.title for t in list_tasks(session, project_id, overdue=True, now=NOW)] == ["tz"]


def test_naive_now_is_rejected(session: Session, project_id: int) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        list_tasks(session, project_id, overdue=True, now=datetime(2026, 1, 1))  # noqa: DTZ001
