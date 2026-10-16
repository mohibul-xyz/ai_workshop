"""F05: task tags. One test per acceptance criterion in specs/F05-task-tags.md (make lab-spec)."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Tag, task_tags


def _create(client: TestClient, project_id: int, **fields: object) -> dict[str, object]:
    resp = client.post(f"/api/v1/projects/{project_id}/tasks", json={"title": "t", **fields})
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


def _titles(client: TestClient, project_id: int, **params: object) -> list[str]:
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params=params)
    assert resp.status_code == 200, resp.text
    return [t["title"] for t in resp.json()]


def test_ac1_create_with_tags(client: TestClient, project_id: int) -> None:
    task = _create(client, project_id, tags=["urgent", "ops"])
    assert task["tags"] == ["ops", "urgent"]


def test_ac2_tags_default_empty(client: TestClient, project_id: int) -> None:
    task = _create(client, project_id)
    assert task["tags"] == []
    assert client.get(f"/api/v1/tasks/{task['id']}").json()["tags"] == []


def test_ac3_tags_normalised_and_deduplicated(client: TestClient, project_id: int) -> None:
    task = _create(client, project_id, tags=[" Urgent ", "urgent", "OPS"])
    assert task["tags"] == ["ops", "urgent"]


def test_ac4_invalid_tag_rejected(client: TestClient, project_id: int) -> None:
    for bad in ["", "   ", "x" * 33, "has space", "under_score", "émoji"]:
        resp = client.post(
            f"/api/v1/projects/{project_id}/tasks", json={"title": "bad", "tags": [bad]}
        )
        assert resp.status_code == 422, bad
    assert _titles(client, project_id) == []


def test_ac5_too_many_tags_rejected(client: TestClient, project_id: int) -> None:
    resp = client.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "x", "tags": [f"t{i}" for i in range(11)]},
    )
    assert resp.status_code == 422
    ten = _create(client, project_id, tags=[f"t{i}" for i in range(10)] + ["t0"])
    assert ten["tags"] == sorted(f"t{i}" for i in range(10))


def test_ac6_patch_replaces_tags(client: TestClient, project_id: int) -> None:
    task_id = _create(client, project_id, tags=["a", "b"])["id"]
    resp = client.patch(f"/api/v1/tasks/{task_id}", json={"tags": ["c"]})
    assert resp.status_code == 200
    assert resp.json()["tags"] == ["c"]
    assert client.patch(f"/api/v1/tasks/{task_id}", json={"tags": []}).json()["tags"] == []


def test_ac7_patch_without_tags_keeps_them(client: TestClient, project_id: int) -> None:
    task_id = _create(client, project_id, tags=["a"])["id"]
    resp = client.patch(f"/api/v1/tasks/{task_id}", json={"title": "renamed"})
    assert resp.json()["title"] == "renamed"
    assert resp.json()["tags"] == ["a"]


def test_ac8_filter_by_tag(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="u", tags=["urgent"])
    _create(client, project_id, title="o", tags=["ops"])
    _create(client, project_id, title="none")
    assert _titles(client, project_id, tag="urgent") == ["u"]


def test_ac9_filter_by_tag_is_normalised_and_scoped(client: TestClient, project_id: int) -> None:
    other = client.post("/api/v1/projects", json={"name": "Other"}).json()["id"]
    _create(client, project_id, title="mine", tags=["urgent"])
    _create(client, other, title="theirs", tags=["urgent"])
    assert _titles(client, project_id, tag="URGENT") == ["mine"]
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"tag": "no spaces"})
    assert resp.status_code == 422


def test_ac10_filter_combines_with_other_filters(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="open", tags=["urgent"], status="todo")
    _create(client, project_id, title="closed", tags=["urgent"], status="done")
    assert _titles(client, project_id, tag="urgent", status="todo") == ["open"]


def test_ac11_tags_shared_across_tasks(
    client: TestClient, project_id: int, session: Session
) -> None:
    _create(client, project_id, tags=["ops"])
    _create(client, project_id, tags=["ops"])
    count = session.scalar(select(func.count()).select_from(Tag).where(Tag.name == "ops"))
    assert count == 1


def test_ac12_deleting_task_removes_links_not_tags(
    client: TestClient, project_id: int, session: Session
) -> None:
    task_id = _create(client, project_id, tags=["ops"])["id"]
    assert client.delete(f"/api/v1/tasks/{task_id}").status_code == 204
    links = session.scalar(
        select(func.count()).select_from(task_tags).where(task_tags.c.task_id == task_id)
    )
    assert links == 0
    assert session.scalar(select(Tag).where(Tag.name == "ops")) is not None
