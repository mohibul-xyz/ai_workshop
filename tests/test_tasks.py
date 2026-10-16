"""F02: task CRUD. F03: filter by status and max priority."""

from fastapi.testclient import TestClient


def _create(client: TestClient, project_id: int, **fields: object) -> dict[str, object]:
    payload = {"title": "t", **fields}
    resp = client.post(f"/api/v1/projects/{project_id}/tasks", json=payload)
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


def test_create_task_defaults(client: TestClient, project_id: int) -> None:
    task = _create(client, project_id, title="Write docs")
    assert task["status"] == "todo"
    assert task["priority"] == 3
    assert task["project_id"] == project_id


def test_create_task_unknown_project_404(client: TestClient) -> None:
    resp = client.post("/api/v1/projects/999999/tasks", json={"title": "x"})
    assert resp.status_code == 404


def test_priority_out_of_range_rejected(client: TestClient, project_id: int) -> None:
    for bad in (0, 6):
        resp = client.post(
            f"/api/v1/projects/{project_id}/tasks", json={"title": "x", "priority": bad}
        )
        assert resp.status_code == 422


def test_get_update_delete_task(client: TestClient, project_id: int) -> None:
    task_id = _create(client, project_id)["id"]
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 200

    resp = client.patch(f"/api/v1/tasks/{task_id}", json={"status": "done", "priority": 1})
    assert resp.status_code == 200
    assert resp.json()["status"] == "done"
    assert resp.json()["priority"] == 1

    assert client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    assert client.get(f"/api/v1/tasks/{task_id}").status_code == 404


def test_patch_unknown_task_404(client: TestClient) -> None:
    assert client.patch("/api/v1/tasks/999999", json={"title": "x"}).status_code == 404


def test_filter_by_status(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="a", status="todo")
    _create(client, project_id, title="b", status="done")
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"status": "done"})
    assert [t["title"] for t in resp.json()["items"]] == ["b"]


def test_filter_by_max_priority_is_inclusive(client: TestClient, project_id: int) -> None:
    for p in (1, 2, 3, 4):
        _create(client, project_id, title=f"p{p}", priority=p)
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"max_priority": 2})
    assert [t["title"] for t in resp.json()["items"]] == ["p1", "p2"]


def test_filters_combine(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="hit", status="todo", priority=1)
    _create(client, project_id, title="wrong-status", status="done", priority=1)
    _create(client, project_id, title="wrong-priority", status="todo", priority=5)
    resp = client.get(
        f"/api/v1/projects/{project_id}/tasks", params={"status": "todo", "max_priority": 2}
    )
    assert [t["title"] for t in resp.json()["items"]] == ["hit"]


def test_invalid_status_filter_422(client: TestClient, project_id: int) -> None:
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"status": "nope"})
    assert resp.status_code == 422
