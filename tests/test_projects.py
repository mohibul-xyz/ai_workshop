"""F01: projects can be created and listed; names are unique."""

from fastapi.testclient import TestClient


def test_create_project_returns_201_and_body(client: TestClient) -> None:
    resp = client.post("/api/v1/projects", json={"name": "Alpha", "description": "first"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Alpha"
    assert body["description"] == "first"
    assert isinstance(body["id"], int)


def test_duplicate_project_name_returns_409(client: TestClient) -> None:
    assert client.post("/api/v1/projects", json={"name": "Dup"}).status_code == 201
    resp = client.post("/api/v1/projects", json={"name": "Dup"})
    assert resp.status_code == 409
    assert "already exists" in resp.json()["detail"]


def test_list_projects_in_creation_order(client: TestClient) -> None:
    for name in ("One", "Two"):
        client.post("/api/v1/projects", json={"name": name})
    names = [p["name"] for p in client.get("/api/v1/projects").json()["items"]]
    assert names[-2:] == ["One", "Two"]


def test_empty_name_rejected(client: TestClient) -> None:
    assert client.post("/api/v1/projects", json={"name": ""}).status_code == 422


def test_unknown_project_returns_404(client: TestClient) -> None:
    assert client.get("/api/v1/projects/999999").status_code == 404
