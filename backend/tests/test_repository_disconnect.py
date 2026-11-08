from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.db import engine
from app.main import app
from app.models import Chunk, Finding, Report, Repository, Scan, User
from app.services.user_services import STUB_USER_ID

client = TestClient(app)


def _create_user() -> uuid.UUID:
    with Session(engine) as session:
        user = User(email=f"other-{uuid.uuid4()}@example.com")
        session.add(user)
        session.commit()
        return user.id


def _create_repository(user_id: uuid.UUID = STUB_USER_ID) -> uuid.UUID:
    with Session(engine) as session:
        repository = Repository(
            user_id=user_id,
            name="disconnect-repo",
            source_type="git_url",
            source_ref=f"https://github.com/example/disconnect-{uuid.uuid4()}",
        )
        session.add(repository)
        session.commit()
        return repository.id


def _create_scan(repository_id: uuid.UUID, status: str, user_id: uuid.UUID = STUB_USER_ID) -> uuid.UUID:
    with Session(engine) as session:
        scan = Scan(repository_id=repository_id, user_id=user_id, status=status)
        session.add(scan)
        session.commit()
        return scan.id


def _add_derived_data(scan_id: uuid.UUID) -> None:
    with Session(engine) as session:
        session.add_all(
            [
                Finding(
                    scan_id=scan_id,
                    user_id=STUB_USER_ID,
                    rule_id="DF001",
                    severity="high",
                    category="docker",
                    file_path="Dockerfile",
                    line_number=None,
                    message="Container runs as root",
                    remediation="Add a USER directive with a non-root user.",
                ),
                Report(
                    scan_id=scan_id,
                    user_id=STUB_USER_ID,
                    total_findings=1,
                    severity_counts={"critical": 0, "high": 1, "medium": 0, "low": 0, "info": 0},
                    rule_counts={"DF001": 1},
                    category_counts={"docker": 1},
                ),
                Chunk(
                    scan_id=scan_id,
                    user_id=STUB_USER_ID,
                    source_path="Dockerfile",
                    chunk_index=0,
                    content="FROM python:3.14-slim\n",
                    token_count=6,
                ),
            ]
        )
        session.commit()


def _count_rows(model: type[Finding] | type[Report] | type[Chunk], scan_id: uuid.UUID) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(model).where(model.scan_id == scan_id)) or 0


def test_disconnect_repository_removes_repository_and_derived_data() -> None:
    repository_id = _create_repository()
    succeeded_scan_id = _create_scan(repository_id, "succeeded")
    failed_scan_id = _create_scan(repository_id, "failed")
    _add_derived_data(succeeded_scan_id)

    response = client.delete(f"/api/repositories/{repository_id}")

    assert response.status_code == 204
    with Session(engine) as session:
        assert session.get(Repository, repository_id) is None
        assert session.get(Scan, succeeded_scan_id) is None
        assert session.get(Scan, failed_scan_id) is None
    assert _count_rows(Finding, succeeded_scan_id) == 0
    assert _count_rows(Report, succeeded_scan_id) == 0
    assert _count_rows(Chunk, succeeded_scan_id) == 0


def test_disconnect_repository_disappears_from_list() -> None:
    repository_id = _create_repository()

    client.delete(f"/api/repositories/{repository_id}")

    listed_ids: set[str] = set()
    offset = 0
    while True:
        page = client.get("/api/repositories", params={"limit": 100, "offset": offset}).json()
        if not page["items"]:
            break
        listed_ids.update(item["id"] for item in page["items"])
        offset += 100
    assert str(repository_id) not in listed_ids


def test_disconnect_unknown_repository_is_not_found() -> None:
    response = client.delete(f"/api/repositories/{uuid.uuid4()}")
    assert response.status_code == 404


def test_disconnect_foreign_repository_is_not_found_and_keeps_its_data() -> None:
    other_user_id = _create_user()
    repository_id = _create_repository(user_id=other_user_id)
    scan_id = _create_scan(repository_id, "succeeded", user_id=other_user_id)

    response = client.delete(f"/api/repositories/{repository_id}")

    assert response.status_code == 404
    with Session(engine) as session:
        assert session.get(Repository, repository_id) is not None
        assert session.get(Scan, scan_id) is not None


@pytest.mark.parametrize("active_status", ["queued", "running"])
def test_disconnect_repository_with_active_scan_conflicts(active_status: str) -> None:
    repository_id = _create_repository()
    scan_id = _create_scan(repository_id, active_status)

    response = client.delete(f"/api/repositories/{repository_id}")

    assert response.status_code == 409
    assert "queued or running" in response.json()["detail"]
    with Session(engine) as session:
        assert session.get(Repository, repository_id) is not None
        assert session.get(Scan, scan_id) is not None
