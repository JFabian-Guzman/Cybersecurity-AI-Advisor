from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_list_repositories_empty() -> None:
    response = client.get("/api/repositories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_connect_repository_returns_repository() -> None:
    response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-repo"
    assert data["source_type"] == "git_url"
    assert data["source_ref"] == "https://github.com/example/repo"
    assert "scan_id" not in data


def test_connect_repository_is_idempotent_by_source_ref() -> None:
    body = {"url": "https://github.com/example/idempotent-repo", "name": "idempotent-repo"}

    first = client.post("/api/repositories", json=body)
    second = client.post("/api/repositories", json=body)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] == second.json()["id"]


def test_create_scan_creates_scan() -> None:
    connect_response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/create-scan-repo", "name": "create-scan-repo"},
    )
    assert connect_response.status_code == 201
    repository_id = connect_response.json()["id"]

    response = client.post("/api/scans", json={"repository_id": repository_id})
    assert response.status_code == 201
    data = response.json()
    assert data["repository_id"] == repository_id
    assert data["status"] == "queued"


def test_connect_repository_invalid_url() -> None:
    response = client.post(
        "/api/repositories",
        json={"url": "not-a-url", "name": "bad"},
    )
    assert response.status_code == 422


def test_get_scan_not_found() -> None:
    response = client.get("/api/scans/00000000-0000-0000-0000-000000000999")
    assert response.status_code == 404


def test_upload_repository_is_rejected() -> None:
    response = client.post("/api/repositories/upload")
    assert response.status_code == 501
    assert "not implemented" in response.json()["detail"].lower()


def test_upload_repository_creates_no_records() -> None:
    before = len(client.get("/api/repositories").json())
    client.post("/api/repositories/upload")
    after = len(client.get("/api/repositories").json())
    assert before == after
