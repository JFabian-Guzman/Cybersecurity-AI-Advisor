from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from db import engine
from dependencies import STUB_USER_ID
from main import app
from models import Finding

client = TestClient(app)


def _create_scan() -> str:
    response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert response.status_code == 201
    return str(response.json()["scan_id"])


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
