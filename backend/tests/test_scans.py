from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.db import engine
from app.main import app
from app.models import Finding, Repository, Scan, User
from app.reporting.generate import generate_report
from app.services.user_services import STUB_USER_ID

client = TestClient(app)


def _create_scan() -> str:
    connect_response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert connect_response.status_code == 201
    repository_id = connect_response.json()["id"]

    scan_response = client.post("/api/scans", json={"repository_id": repository_id})
    assert scan_response.status_code == 201
    return str(scan_response.json()["id"])


def _create_foreign_scan() -> str:
    """Creates a scan owned by a different user, to assert the stub user can't read it."""
    with Session(engine) as session:
        other_user = User(email=f"other-{uuid.uuid4()}@example.com")
        session.add(other_user)
        session.flush()

        repository = Repository(
            user_id=other_user.id,
            name="foreign-repo",
            source_type="git_url",
            source_ref=f"https://github.com/example/foreign-{uuid.uuid4()}",
        )
        session.add(repository)
        session.flush()

        scan = Scan(repository_id=repository.id, user_id=other_user.id, status="queued")
        session.add(scan)
        session.commit()
        return str(scan.id)


def test_get_scan_owned_by_another_user_is_not_found() -> None:
    scan_id = _create_foreign_scan()
    response = client.get(f"/api/scans/{scan_id}")
    assert response.status_code == 404


def test_get_scan_findings_owned_by_another_user_is_not_found() -> None:
    scan_id = _create_foreign_scan()
    response = client.get(f"/api/scans/{scan_id}/findings")
    assert response.status_code == 404


def test_get_scan_report_owned_by_another_user_is_not_found() -> None:
    scan_id = _create_foreign_scan()
    response = client.get(f"/api/scans/{scan_id}/report")
    assert response.status_code == 404


def test_get_scan_findings_not_found() -> None:
    response = client.get(f"/api/scans/{uuid.uuid4()}/findings")
    assert response.status_code == 404


def test_get_scan_findings_empty() -> None:
    scan_id = _create_scan()
    response = client.get(f"/api/scans/{scan_id}/findings")
    assert response.status_code == 200
    assert response.json() == []


def test_get_scan_findings_returns_seeded_rows() -> None:
    scan_id = _create_scan()

    with Session(engine) as session:
        session.add(
            Finding(
                scan_id=uuid.UUID(scan_id),
                user_id=STUB_USER_ID,
                rule_id="DF001",
                severity="high",
                file_path="Dockerfile",
                line_number=3,
                message="Container runs as root",
                remediation="Add a USER directive with a non-root user.",
            )
        )
        session.commit()

    response = client.get(f"/api/scans/{scan_id}/findings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["rule_id"] == "DF001"
    assert data[0]["severity"] == "high"
    assert data[0]["file_path"] == "Dockerfile"


def test_get_report_not_found() -> None:
    response = client.get(f"/api/scans/{uuid.uuid4()}/report")
    assert response.status_code == 404


def test_get_report_conflict_while_not_succeeded() -> None:
    scan_id = _create_scan()
    response = client.get(f"/api/scans/{scan_id}/report")
    assert response.status_code == 409
    assert "queued" in response.json()["detail"]


def test_get_report_returns_counts() -> None:
    scan_id = _create_scan()

    with Session(engine) as session:
        session.add(
            Finding(
                scan_id=uuid.UUID(scan_id),
                user_id=STUB_USER_ID,
                rule_id="DF001",
                severity="high",
                file_path="Dockerfile",
                line_number=3,
                message="Container runs as root",
                remediation="Add a USER directive with a non-root user.",
                category="docker",
            )
        )
        session.commit()

        scan = session.get(Scan, uuid.UUID(scan_id))
        assert scan is not None
        generate_report(session, scan.id, scan.user_id)
        scan.status = "succeeded"
        session.commit()

    response = client.get(f"/api/scans/{scan_id}/report")
    assert response.status_code == 200
    data = response.json()
    assert data["scan_id"] == scan_id
    assert data["total_findings"] == 1
    assert data["severity_counts"]["high"] == 1
    assert data["rule_counts"] == {"DF001": 1}
    assert data["category_counts"] == {"docker": 1}
