"""B1 hidden acceptance tests — copied into a run's worktree only AFTER the agent finishes.

Agents must not read this file (permissions deny benchmarks/**/hidden/**; guard hooks block it).
"""

from fastapi.testclient import TestClient


def _task(client: TestClient, project_id: int, status: str) -> int:
    resp = client.post(f"/api/v1/projects/{project_id}/tasks", json={"title": "t", "status": status})
    assert resp.status_code == 201
    return int(resp.json()["id"])


def _stats(client: TestClient, project_id: int) -> dict:
    resp = client.get(f"/api/v1/projects/{project_id}/stats")
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_b1_counts_per_status(client: TestClient, project_id: int) -> None:
    for status in ("todo", "todo", "in_progress", "done", "done"):
        _task(client, project_id, status)
    body = _stats(client, project_id)
    assert body["counts"] == {"todo": 2, "in_progress": 1, "done": 2}
    assert body["total"] == 5
    assert body["project_id"] == project_id


def test_b1_missing_statuses_are_zero(client: TestClient, project_id: int) -> None:
    _task(client, project_id, "done")
    assert _stats(client, project_id)["counts"] == {"todo": 0, "in_progress": 0, "done": 1}


def test_b1_empty_project(client: TestClient, project_id: int) -> None:
    body = _stats(client, project_id)
    assert body["counts"] == {"todo": 0, "in_progress": 0, "done": 0}
    assert body["total"] == 0


def test_b1_only_counts_this_project(client: TestClient, project_id: int) -> None:
    other = client.post("/api/v1/projects", json={"name": "other"}).json()["id"]
    _task(client, other, "todo")
    _task(client, project_id, "done")
    assert _stats(client, project_id)["total"] == 1


def test_b1_reflects_status_changes(client: TestClient, project_id: int) -> None:
    task_id = _task(client, project_id, "todo")
    client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done"})
    assert _stats(client, project_id)["counts"]["done"] == 1


def test_b1_unknown_project_404(client: TestClient) -> None:
    resp = client.get("/api/v1/projects/999999/stats")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Project not found"}


def test_b1_counts_are_integers(client: TestClient, project_id: int) -> None:
    _task(client, project_id, "todo")
    body = _stats(client, project_id)
    assert all(isinstance(v, int) for v in body["counts"].values())
    assert isinstance(body["total"], int)
