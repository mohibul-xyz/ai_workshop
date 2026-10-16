"""F07: search tasks by title. One test per acceptance criterion in specs/F07-task-search.md."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

FIXTURE_TITLES = ["Fix login bug", "Write docs", "Login page redesign"]


def _create(client: TestClient, project_id: int, **fields: object) -> dict[str, object]:
    resp = client.post(f"/api/v1/projects/{project_id}/tasks", json={"title": "t", **fields})
    assert resp.status_code == 201, resp.text
    body: dict[str, object] = resp.json()
    return body


def _list(client: TestClient, project_id: int, **params: object) -> dict[str, Any]:
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params=params)
    assert resp.status_code == 200, resp.text
    body: dict[str, Any] = resp.json()
    return body


def _titles(client: TestClient, project_id: int, **params: object) -> list[str]:
    return [t["title"] for t in _list(client, project_id, **params)["items"]]


@pytest.fixture
def fixture_tasks(client: TestClient, project_id: int) -> None:
    for title in FIXTURE_TITLES:
        _create(client, project_id, title=title)


@pytest.mark.usefixtures("fixture_tasks")
def test_ac1_search_matches_title_substring(client: TestClient, project_id: int) -> None:
    page = _list(client, project_id, q="login")
    assert [t["title"] for t in page["items"]] == ["Fix login bug", "Login page redesign"]
    assert page["total"] == 2


@pytest.mark.usefixtures("fixture_tasks")
def test_ac2_search_is_case_insensitive(client: TestClient, project_id: int) -> None:
    assert _titles(client, project_id, q="LoGiN") == ["Fix login bug", "Login page redesign"]


@pytest.mark.usefixtures("fixture_tasks")
def test_ac3_search_without_match_returns_empty_page(client: TestClient, project_id: int) -> None:
    page = _list(client, project_id, q="zzz")
    assert page["items"] == []
    assert page["total"] == 0


def test_ac4_search_treats_wildcards_literally(client: TestClient, project_id: int) -> None:
    for title in ["100% done", "1000 done", "snake_case", "snakeXcase", "C:\\temp"]:
        _create(client, project_id, title=title)
    assert _titles(client, project_id, q="%") == ["100% done"]
    assert _titles(client, project_id, q="_") == ["snake_case"]
    assert _titles(client, project_id, q="\\") == ["C:\\temp"]


def test_ac5_search_matches_title_only(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="Write docs", description="login flow")
    assert _titles(client, project_id, q="login") == []


def test_ac6_search_is_scoped_to_project(client: TestClient, project_id: int) -> None:
    other = client.post("/api/v1/projects", json={"name": "Other"}).json()["id"]
    _create(client, project_id, title="Fix login bug", description="mine")
    _create(client, project_id, title="Write docs", description="mine, no match")
    _create(client, other, title="Fix login bug", description="theirs")
    items = _list(client, project_id, q="login")["items"]
    assert [t["description"] for t in items] == ["mine"]


def test_ac7_search_combines_with_other_filters(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="Fix login bug", status="todo", tags=["urgent"])
    _create(client, project_id, title="Login page redesign", status="done", tags=["urgent"])
    _create(client, project_id, title="Login audit", status="todo")
    _create(client, project_id, title="Write docs", status="todo", tags=["urgent"])
    titles = _titles(client, project_id, q="login", status="todo", tag="urgent")
    assert titles == ["Fix login bug"]


def test_ac8_search_applies_before_pagination(client: TestClient, project_id: int) -> None:
    for title in ["login a", "other b", "login c", "other d", "login e"]:
        _create(client, project_id, title=title)
    first = _list(client, project_id, q="login", limit=2)
    second = _list(client, project_id, q="login", limit=2, offset=2)
    assert [t["title"] for t in first["items"]] == ["login a", "login c"]
    assert [t["title"] for t in second["items"]] == ["login e"]
    assert first["total"] == second["total"] == 3


@pytest.mark.usefixtures("fixture_tasks")
def test_ac9_search_trims_whitespace(client: TestClient, project_id: int) -> None:
    assert _titles(client, project_id, q="  login ") == ["Fix login bug", "Login page redesign"]


def test_ac10_empty_search_rejected(client: TestClient, project_id: int) -> None:
    for blank in ["", "   "]:
        resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"q": blank})
        assert resp.status_code == 422, repr(blank)
    # q is validated before the project lookup, like ?tag= (plan step 3)
    assert client.get("/api/v1/projects/999999/tasks", params={"q": ""}).status_code == 422


def test_ac11_search_length_bounds(client: TestClient, project_id: int) -> None:
    _create(client, project_id, title="a" * 200)
    assert _titles(client, project_id, q="a" * 200) == ["a" * 200]
    assert _titles(client, project_id, q=" " + "a" * 200 + " ") == ["a" * 200]  # length after trim
    resp = client.get(f"/api/v1/projects/{project_id}/tasks", params={"q": "a" * 201})
    assert resp.status_code == 422


def test_ac12_search_unknown_project_404(client: TestClient) -> None:
    resp = client.get("/api/v1/projects/999999/tasks", params={"q": "login"})
    assert resp.status_code == 404
    assert resp.json() == {"detail": "Project not found"}


@pytest.mark.usefixtures("fixture_tasks")
def test_ac13_no_search_param_unchanged(client: TestClient, project_id: int) -> None:
    page = _list(client, project_id)
    assert [t["title"] for t in page["items"]] == FIXTURE_TITLES
    assert page["total"] == 3
