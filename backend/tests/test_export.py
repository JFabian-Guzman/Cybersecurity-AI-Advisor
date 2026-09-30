from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

import app.jobs as jobs
from app.main import app
from app.models import Report
from app.reporting.export import (
    ExportDocument,
    build_export_document,
    render_markdown,
    render_pdf,
)
from app.services.user_services import STUB_USER_ID
from tests.conftest import create_scan

client = TestClient(app)

# ---------------------------------------------------------------------------
# Unit tests — ExportDocument builder and Markdown renderer
# ---------------------------------------------------------------------------


def _make_report() -> Report:
    """Return an in-memory Report ORM instance (not persisted) for unit tests."""
    return Report(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        user_id=STUB_USER_ID,
        total_findings=4,
        severity_counts={"critical": 1, "high": 2, "medium": 0, "low": 1, "info": 0},
        rule_counts={"DF001": 2, "DF003": 1, "K8S001": 1},
        category_counts={"docker": 3, "kubernetes": 1},
    )


def test_build_export_document_sets_slug() -> None:
    report = _make_report()
    doc = build_export_document(report, "My Repo Name")
    assert doc.repo_slug == "my-repo-name"
    assert doc.repo_name == "My Repo Name"
    assert doc.total_findings == 4


def test_build_export_document_copies_counts() -> None:
    report = _make_report()
    doc = build_export_document(report, "test-repo")
    assert doc.severity_counts == report.severity_counts
    assert doc.rule_counts == report.rule_counts
    assert doc.category_counts == report.category_counts
    report.severity_counts["critical"] = 99
    assert doc.severity_counts["critical"] == 1


def test_render_markdown_contains_expected_sections() -> None:
    doc = ExportDocument(
        scan_id=uuid.uuid4(),
        repo_name="test-repo",
        repo_slug="test-repo",
        total_findings=4,
        severity_counts={"critical": 1, "high": 2, "medium": 0, "low": 1, "info": 0},
        rule_counts={"DF001": 2, "K8S001": 1},
        category_counts={"docker": 3, "kubernetes": 1},
    )
    md = render_markdown(doc).decode("utf-8")

    assert "# Security Report" in md
    assert "test-repo" in md
    assert str(doc.scan_id) in md
    assert "**Total findings:** 4" in md
    assert "## Findings by Severity" in md
    assert "## Findings by Category" in md
    assert "## Findings by Rule" in md


def test_render_markdown_severity_order() -> None:
    """Severity rows must appear CRITICAL → HIGH → MEDIUM → LOW → INFO."""
    doc = ExportDocument(
        scan_id=uuid.uuid4(),
        repo_name="r",
        repo_slug="r",
        total_findings=0,
        severity_counts={"info": 1, "low": 2, "medium": 3, "high": 4, "critical": 5},
        rule_counts={},
        category_counts={},
    )
    md = render_markdown(doc).decode("utf-8")
    positions = {sev: md.index(sev.capitalize()) for sev in ("Critical", "High", "Medium", "Low", "Info")}
    assert positions["Critical"] < positions["High"] < positions["Medium"] < positions["Low"] < positions["Info"]


def test_render_markdown_zero_findings() -> None:
    doc = ExportDocument(
        scan_id=uuid.uuid4(),
        repo_name="empty-repo",
        repo_slug="empty-repo",
        total_findings=0,
        severity_counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        rule_counts={},
        category_counts={},
    )
    md = render_markdown(doc).decode("utf-8")
    assert "**Total findings:** 0" in md


# ---------------------------------------------------------------------------
# Unit tests — PDF renderer
# ---------------------------------------------------------------------------


def test_render_pdf_produces_valid_pdf() -> None:
    """The output bytes must be a parseable PDF — not just non-empty."""
    from io import BytesIO

    import pypdf

    doc = ExportDocument(
        scan_id=uuid.uuid4(),
        repo_name="test-repo",
        repo_slug="test-repo",
        total_findings=3,
        severity_counts={"critical": 1, "high": 1, "medium": 0, "low": 1, "info": 0},
        rule_counts={"DF001": 2, "K8S001": 1},
        category_counts={"docker": 2, "kubernetes": 1},
    )
    pdf_bytes = render_pdf(doc)

    assert pdf_bytes[:4] == b"%PDF", "Output does not start with PDF magic bytes"

    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


def test_render_pdf_zero_findings_does_not_crash() -> None:
    """A scan with no findings must still produce a valid PDF."""
    from io import BytesIO

    import pypdf

    doc = ExportDocument(
        scan_id=uuid.uuid4(),
        repo_name="clean-repo",
        repo_slug="clean-repo",
        total_findings=0,
        severity_counts={"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0},
        rule_counts={},
        category_counts={},
    )
    pdf_bytes = render_pdf(doc)
    reader = pypdf.PdfReader(BytesIO(pdf_bytes))
    assert len(reader.pages) >= 1


# ---------------------------------------------------------------------------
# Integration tests — HTTP endpoint (Markdown)
# ---------------------------------------------------------------------------


def _run_scan_with_monkeypatch(scan_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drive a full run_scan cycle without Docker, seeding one finding."""

    def fake_clone(url: str, dest_dir: str, timeout_seconds: int, max_clone_mb: int) -> None:
        import os

        with open(os.path.join(dest_dir, "Dockerfile"), "w") as fh:
            fh.write("FROM ubuntu:latest\n")

    def fake_sandbox(repo_dir: str, analyzers: list[str]) -> list[dict]:
        return [
            {
                "rule_id": "DF002",
                "severity": "HIGH",
                "file": "Dockerfile",
                "line": 1,
                "message": "latest tag used",
                "remediation": "Pin to a specific digest",
                "category": "docker",
            }
        ]

    monkeypatch.setattr(jobs, "clone_repo", fake_clone)
    monkeypatch.setattr(jobs, "_run_sandbox", fake_sandbox)
    jobs.run_scan(scan_id)


def test_export_markdown_returns_200_with_attachment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_id = create_scan()
    _run_scan_with_monkeypatch(scan_id, monkeypatch)

    resp = client.get(f"/api/scans/{scan_id}/report/export?format=markdown")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/markdown")
    assert "attachment" in resp.headers["content-disposition"]
    assert ".md" in resp.headers["content-disposition"]


def test_export_markdown_content_is_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_id = create_scan()
    _run_scan_with_monkeypatch(scan_id, monkeypatch)

    resp = client.get(f"/api/scans/{scan_id}/report/export?format=markdown")
    assert resp.status_code == 200
    body = resp.text
    assert "# Security Report" in body
    assert "**Total findings:** 1" in body
    assert "DF002" in body


def test_export_returns_409_when_scan_not_succeeded() -> None:
    scan_id = create_scan()
    resp = client.get(f"/api/scans/{scan_id}/report/export?format=markdown")
    assert resp.status_code == 409


def test_export_returns_404_for_unknown_scan() -> None:
    resp = client.get(f"/api/scans/{uuid.uuid4()}/report/export?format=markdown")
    assert resp.status_code == 404


def test_export_returns_422_for_invalid_format(monkeypatch: pytest.MonkeyPatch) -> None:
    scan_id = create_scan()
    _run_scan_with_monkeypatch(scan_id, monkeypatch)
    resp = client.get(f"/api/scans/{scan_id}/report/export?format=docx")
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Integration tests — HTTP endpoint (PDF)
# ---------------------------------------------------------------------------


def test_export_pdf_returns_200_with_attachment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scan_id = create_scan()
    _run_scan_with_monkeypatch(scan_id, monkeypatch)

    resp = client.get(f"/api/scans/{scan_id}/report/export?format=pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert "attachment" in resp.headers["content-disposition"]
    assert ".pdf" in resp.headers["content-disposition"]


def test_export_pdf_content_is_valid_pdf(monkeypatch: pytest.MonkeyPatch) -> None:
    """The bytes returned by the endpoint must be a parseable PDF."""
    from io import BytesIO

    import pypdf

    scan_id = create_scan()
    _run_scan_with_monkeypatch(scan_id, monkeypatch)

    resp = client.get(f"/api/scans/{scan_id}/report/export?format=pdf")
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"

    reader = pypdf.PdfReader(BytesIO(resp.content))
    assert len(reader.pages) >= 1
