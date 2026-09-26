from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.db import engine
from app.main import app
from app.models import Repository, Scan
from app.services.user_services import STUB_USER_ID

client = TestClient(app)


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


def test_list_repositories_includes_last_scan_status() -> None:
    no_scan_url = f"https://github.com/example/no-scan-repo-{uuid.uuid4()}"
    no_scan_repo = client.post("/api/repositories", json={"url": no_scan_url, "name": "no-scan-repo"}).json()

    with Session(engine) as session:
        scanned_repo = Repository(
            user_id=STUB_USER_ID,
            name="scanned-repo",
            source_type="git_url",
            source_ref=f"https://github.com/example/scanned-repo-{uuid.uuid4()}",
        )
        session.add(scanned_repo)
        session.flush()

        now = datetime.now(UTC)
        session.add_all(
            [
                Scan(repository_id=scanned_repo.id, user_id=STUB_USER_ID, status="failed", created_at=now),
                Scan(
                    repository_id=scanned_repo.id,
                    user_id=STUB_USER_ID,
                    status="succeeded",
                    created_at=now + timedelta(seconds=1),
                ),
            ]
        )
        session.commit()
        scanned_repo_id = str(scanned_repo.id)

    target_ids = {no_scan_repo["id"], scanned_repo_id}
    listed: dict[str, str | None] = {}
    offset = 0
    while not target_ids.issubset(listed):
        page = client.get("/api/repositories", params={"limit": 100, "offset": offset}).json()
        if not page["items"]:
            break
        listed.update({item["id"]: item["last_scan_status"] for item in page["items"]})
        offset += 100

    assert listed[no_scan_repo["id"]] is None
    assert listed[scanned_repo_id] == "succeeded"


def test_list_repositories_paginates_with_limit_and_offset() -> None:
    for i in range(12):
        client.post(
            "/api/repositories",
            json={"url": f"https://github.com/example/paginated-repo-{i}", "name": f"paginated-repo-{i}"},
        )

    first_page = client.get("/api/repositories", params={"limit": 10, "offset": 0})
    assert first_page.status_code == 200
    first_data = first_page.json()
    assert len(first_data["items"]) == 10
    assert first_data["total"] >= 12

    second_page = client.get("/api/repositories", params={"limit": 10, "offset": 10})
    assert second_page.status_code == 200
    second_data = second_page.json()
    assert len(second_data["items"]) >= 2

    first_ids = {item["id"] for item in first_data["items"]}
    second_ids = {item["id"] for item in second_data["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_list_repository_scans_returns_scans_for_that_repository() -> None:
    url = f"https://github.com/example/repo-scans-{uuid.uuid4()}"
    connect_response = client.post("/api/repositories", json={"url": url, "name": "repo-scans"})
    repository_id = connect_response.json()["id"]

    for _ in range(3):
        scan_response = client.post("/api/scans", json={"repository_id": repository_id})
        assert scan_response.status_code == 201

    response = client.get(f"/api/repositories/{repository_id}/scans")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert all(item["repository_id"] == repository_id for item in data["items"])
    assert all(item["status"] == "queued" for item in data["items"])


def test_list_repository_scans_paginates() -> None:
    url = f"https://github.com/example/repo-scans-paginated-{uuid.uuid4()}"
    connect_response = client.post("/api/repositories", json={"url": url, "name": "repo-scans-paginated"})
    repository_id = connect_response.json()["id"]

    for _ in range(3):
        client.post("/api/scans", json={"repository_id": repository_id})

    first_page = client.get(f"/api/repositories/{repository_id}/scans", params={"limit": 2, "offset": 0})
    assert first_page.status_code == 200
    assert len(first_page.json()["items"]) == 2

    second_page = client.get(f"/api/repositories/{repository_id}/scans", params={"limit": 2, "offset": 2})
    assert second_page.status_code == 200
    assert len(second_page.json()["items"]) == 1


def test_list_repository_scans_not_found() -> None:
    response = client.get(f"/api/repositories/{uuid.uuid4()}/scans")
    assert response.status_code == 404
