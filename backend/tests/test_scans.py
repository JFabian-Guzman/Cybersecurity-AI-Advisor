from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
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


def _create_foreign_repository() -> str:
    """Creates a repository owned by a different user, to assert the stub user can't scan it."""
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
        session.commit()
        return str(repository.id)


class _BrokenQueue:
    def enqueue(self, *args: object, **kwargs: object) -> None:
        raise RedisConnectionError("redis is down")


def _break_queue(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.scans.get_queue", lambda: _BrokenQueue())


def test_create_scan_unknown_repository_is_not_found() -> None:
    response = client.post("/api/scans", json={"repository_id": str(uuid.uuid4())})
    assert response.status_code == 404


def test_create_scan_foreign_repository_is_not_found() -> None:
    repository_id = _create_foreign_repository()
    response = client.post("/api/scans", json={"repository_id": repository_id})
    assert response.status_code == 404


def test_create_scan_marks_failed_when_enqueue_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    connect_response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    repository_id = connect_response.json()["id"]

    _break_queue(monkeypatch)
    response = client.post("/api/scans", json={"repository_id": repository_id})

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "failed"
    assert "enqueue" in data["error"]
    assert data["finished_at"] is not None

    fetched = client.get(f"/api/scans/{data['id']}")
    assert fetched.json()["status"] == "failed"


def test_retry_scan_marks_failed_when_enqueue_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_id = _create_scan()
    with Session(engine) as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        assert scan is not None
        scan.status = "failed"
        scan.error = "Sandbox exited with code 1"
        session.commit()

    _break_queue(monkeypatch)
    response = client.post(f"/api/scans/{scan_id}/retry")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "failed"
    assert "enqueue" in data["error"]


def test_get_scan_owned_by_another_user_is_not_found() -> None:
    scan_id = _create_foreign_scan()
    response = client.get(f"/api/scans/{scan_id}")
    assert response.status_code == 404


def test_retry_scan_not_found() -> None:
    response = client.post(f"/api/scans/{uuid.uuid4()}/retry")
    assert response.status_code == 404


def test_retry_scan_owned_by_another_user_is_not_found() -> None:
    scan_id = _create_foreign_scan()
    response = client.post(f"/api/scans/{scan_id}/retry")
    assert response.status_code == 404


def test_retry_succeeded_scan_conflicts() -> None:
    scan_id = _create_scan()
    with Session(engine) as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        assert scan is not None
        scan.status = "succeeded"
        scan.error = None
        session.commit()

    response = client.post(f"/api/scans/{scan_id}/retry")
    assert response.status_code == 409


def test_retry_failed_scan_resets_status_and_error() -> None:
    scan_id = _create_scan()
    with Session(engine) as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        assert scan is not None
        scan.status = "failed"
        scan.error = "Sandbox exited with code 1"
        session.commit()

    response = client.post(f"/api/scans/{scan_id}/retry")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == scan_id
    assert data["status"] == "queued"
    assert data["error"] is None
    assert data["started_at"] is None
    assert data["finished_at"] is None


def test_retry_stuck_running_scan_resets_to_queued() -> None:
    scan_id = _create_scan()
    with Session(engine) as session:
        scan = session.get(Scan, uuid.UUID(scan_id))
        assert scan is not None
        scan.status = "running"
        session.commit()

    response = client.post(f"/api/scans/{scan_id}/retry")
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


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


def test_get_scan_findings_filters_by_severity() -> None:
    scan_id = _create_scan()
    scan_uuid = uuid.UUID(scan_id)

    with Session(engine) as session:
        session.add_all(
            [
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="DF001",
                    severity="high",
                    category="docker",
                    file_path="Dockerfile",
                    line_number=1,
                    message="Container runs as root",
                    remediation="Add a USER directive with a non-root user.",
                ),
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="DF002",
                    severity="medium",
                    category="docker",
                    file_path="Dockerfile",
                    line_number=2,
                    message="Unpinned package",
                    remediation="Pin package versions.",
                ),
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="K8S001",
                    severity="critical",
                    category="kubernetes",
                    file_path="deploy.yaml",
                    line_number=1,
                    message="Privileged container",
                    remediation="Drop the privilege flag.",
                ),
            ]
        )
        session.commit()

    response = client.get(
        f"/api/scans/{scan_id}/findings",
        params=[("severity", "high"), ("severity", "critical")],
    )
    assert response.status_code == 200
    data = response.json()
    assert {f["rule_id"] for f in data} == {"DF001", "K8S001"}


def test_get_scan_findings_filters_by_category() -> None:
    scan_id = _create_scan()
    scan_uuid = uuid.UUID(scan_id)

    with Session(engine) as session:
        session.add_all(
            [
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="DF001",
                    severity="high",
                    category="docker",
                    file_path="Dockerfile",
                    line_number=1,
                    message="Container runs as root",
                    remediation="Add a USER directive with a non-root user.",
                ),
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="K8S001",
                    severity="high",
                    category="kubernetes",
                    file_path="deploy.yaml",
                    line_number=1,
                    message="Privileged container",
                    remediation="Drop the privilege flag.",
                ),
            ]
        )
        session.commit()

    response = client.get(f"/api/scans/{scan_id}/findings", params={"category": "kubernetes"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["rule_id"] == "K8S001"


def test_get_scan_findings_filters_by_severity_and_category() -> None:
    scan_id = _create_scan()
    scan_uuid = uuid.UUID(scan_id)

    with Session(engine) as session:
        session.add_all(
            [
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="DF001",
                    severity="high",
                    category="docker",
                    file_path="Dockerfile",
                    line_number=1,
                    message="Container runs as root",
                    remediation="Add a USER directive with a non-root user.",
                ),
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="K8S001",
                    severity="high",
                    category="kubernetes",
                    file_path="deploy.yaml",
                    line_number=1,
                    message="Privileged container",
                    remediation="Drop the privilege flag.",
                ),
                Finding(
                    scan_id=scan_uuid,
                    user_id=STUB_USER_ID,
                    rule_id="DF002",
                    severity="low",
                    category="docker",
                    file_path="Dockerfile",
                    line_number=2,
                    message="Unpinned package",
                    remediation="Pin package versions.",
                ),
            ]
        )
        session.commit()

    response = client.get(
        f"/api/scans/{scan_id}/findings",
        params=[("severity", "high"), ("category", "docker")],
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["rule_id"] == "DF001"


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
