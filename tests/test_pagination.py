"""F06: limit/offset pagination with the {items,total,limit,offset} envelope."""

from fastapi.testclient import TestClient


def _tasks(client: TestClient, project_id: int, n: int, **fields: object) -> None:
    for i in range(n):
        resp = client.post(
            f"/api/v1/projects/{project_id}/tasks", json={"title": f"t{i:02d}", **fields}
        )
        assert resp.status_code == 201


def _page(client: TestClient, project_id: int, **params: object) -> dict[str, object]:
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params=params)
    assert resp.status_code == 200, resp.text
    body: dict[str, object] = resp.json()
    return body


def _titles(page: dict[str, object]) -> list[str]:
    items = page["items"]
    assert isinstance(items, list)
    return [t["title"] for t in items]


def test_envelope_and_defaults(client: TestClient, project_id: int) -> None:
    _tasks(client, project_id, 25)
    page = _page(client, project_id)
    assert set(page) == {"items", "total", "limit", "offset"}
    assert (page["total"], page["limit"], page["offset"]) == (25, 20, 0)
    assert len(_titles(page)) == 20


def test_pages_are_stable_and_ordered_by_id(client: TestClient, project_id: int) -> None:
    _tasks(client, project_id, 7)
    seen = []
    for offset in range(0, 7, 3):
        seen += _titles(_page(client, project_id, limit=3, offset=offset))
    assert seen == [f"t{i:02d}" for i in range(7)]


def test_offset_past_end_returns_empty_items_and_real_total(
    client: TestClient, project_id: int
) -> None:
    _tasks(client, project_id, 3)
    page = _page(client, project_id, offset=10)
    assert page["items"] == []
    assert page["total"] == 3


def test_limit_bounds(client: TestClient, project_id: int) -> None:
    for bad in ({"limit": 0}, {"limit": 101}, {"offset": -1}, {"limit": "x"}):
        resp = client.get(f"/api/v1/projects/{project_id}/tasks", params=bad)
        assert resp.status_code == 422, bad
    assert _page(client, project_id, limit=100)["limit"] == 100
    assert _page(client, project_id, limit=1)["limit"] == 1


def test_total_counts_filtered_rows_before_paging(client: TestClient, project_id: int) -> None:
    _tasks(client, project_id, 4, status="done")
    _tasks(client, project_id, 2, status="todo")
    page = _page(client, project_id, status="done", limit=1)
    assert page["total"] == 4
    assert len(_titles(page)) == 1


def test_pagination_combines_with_tag_filter(client: TestClient, project_id: int) -> None:
    _tasks(client, project_id, 3, tags=["ops"])
    _tasks(client, project_id, 3)
    page = _page(client, project_id, tag="ops", limit=2, offset=2)
    assert page["total"] == 3
    assert len(_titles(page)) == 1


def test_projects_list_is_paginated(client: TestClient) -> None:
    for i in range(3):
        client.post("/api/v1/projects", json={"name": f"pg-{i}"})
    resp = client.get("/api/v1/projects", params={"limit": 2})
    body = resp.json()
    assert resp.status_code == 200
    assert body["limit"] == 2
    assert len(body["items"]) == 2
    assert body["total"] >= 3
    assert client.get("/api/v1/projects", params={"limit": 0}).status_code == 422
