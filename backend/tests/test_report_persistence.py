from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.db import engine
from app.main import app
from app.models import Finding, Report, Scan
from app.reporting.generate import generate_report
from app.services.user_services import STUB_USER_ID

client = TestClient(app)


def _create_scan() -> uuid.UUID:
    connect_response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert connect_response.status_code == 201
    repository_id = connect_response.json()["id"]

    scan_response = client.post("/api/scans", json={"repository_id": repository_id})
    assert scan_response.status_code == 201
    return uuid.UUID(scan_response.json()["id"])


def _seed_findings(session: Session, scan_id: uuid.UUID) -> None:
    rows = [
        ("DF003", "critical", "docker"),
        ("DF001", "high", "docker"),
        ("DF001", "high", "docker"),
        ("K8S001", "high", "kubernetes"),
    ]
    for rule_id, severity, category in rows:
        session.add(
            Finding(
                scan_id=scan_id,
                user_id=STUB_USER_ID,
                rule_id=rule_id,
                severity=severity,
                file_path="Dockerfile",
                line_number=1,
                message="message",
                remediation="remediation",
                category=category,
            )
        )
    session.commit()


def test_generate_report_persists_counts() -> None:
    scan_id = _create_scan()

    with Session(engine) as session:
        _seed_findings(session, scan_id)
        scan = session.get(Scan, scan_id)
        assert scan is not None
        generate_report(session, scan.id, scan.user_id)
        session.commit()

    with Session(engine) as session:
        report = session.query(Report).filter(Report.scan_id == scan_id).one()
        assert report.user_id == STUB_USER_ID
        assert report.total_findings == 4
        assert report.severity_counts["critical"] == 1
        assert report.severity_counts["high"] == 3
        assert report.severity_counts["low"] == 0
        assert report.rule_counts == {"DF003": 1, "DF001": 2, "K8S001": 1}
        assert report.category_counts == {"docker": 3, "kubernetes": 1}


def test_generate_report_replaces_previous_run() -> None:
    scan_id = _create_scan()

    with Session(engine) as session:
        _seed_findings(session, scan_id)
        scan = session.get(Scan, scan_id)
        assert scan is not None
        generate_report(session, scan.id, scan.user_id)
        session.commit()
        generate_report(session, scan.id, scan.user_id)
        session.commit()

    with Session(engine) as session:
        reports = session.query(Report).filter(Report.scan_id == scan_id).all()
        assert len(reports) == 1
        assert reports[0].total_findings == 4


def test_generate_report_with_no_findings() -> None:
    scan_id = _create_scan()

    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        assert scan is not None
        generate_report(session, scan.id, scan.user_id)
        session.commit()

    with Session(engine) as session:
        report = session.query(Report).filter(Report.scan_id == scan_id).one()
        assert report.total_findings == 0
        assert report.rule_counts == {}
        assert report.severity_counts == {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
