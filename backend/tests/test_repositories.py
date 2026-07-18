from __future__ import annotations

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_list_repositories_empty() -> None:
    response = client.get("/api/repositories")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_connect_repository_returns_scan_id() -> None:
    response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "test-repo"
    assert data["source_type"] == "git_url"
    assert "scan_id" in data


def test_connect_repository_invalid_url() -> None:
    response = client.post(
        "/api/repositories",
        json={"url": "not-a-url", "name": "bad"},
    )
    assert response.status_code == 422


def test_get_scan_not_found() -> None:
    response = client.get("/api/scans/00000000-0000-0000-0000-000000000999")
    assert response.status_code == 404
