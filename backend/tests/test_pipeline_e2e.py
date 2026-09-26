"""End-to-end pipeline test — walking skeleton.

Drives the full path:
  create repository → create scan → run job (synchronous, no Docker)
  → findings persisted → report generated → export returns output → chunks stored

Runs against a single-Dockerfile fixture repo seeded via monkeypatch,
following the same pattern as test_export.py.
"""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

import app.jobs as jobs
from app.db.db import SessionLocal
from app.main import app
from app.models import Chunk
from app.services.user_services import STUB_USER_ID
from tests.conftest import create_scan

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_repo(dest_dir: str) -> None:
    """Write a minimal Dockerfile so classify.py detects a text file to chunk."""
    import os

    with open(os.path.join(dest_dir, "Dockerfile"), "w") as fh:
        fh.write(
            "FROM ubuntu:latest\n" "RUN apt-get update && apt-get install -y curl\n" "EXPOSE 80\n" 'CMD ["/bin/bash"]\n'
        )


def _fake_clone(url: str, dest_dir: str, timeout_seconds: int, max_clone_mb: int) -> None:
    _seed_repo(dest_dir)


def _fake_sandbox(repo_dir: str, analyzers: list[str]) -> list[dict]:
    return [
        {
            "rule_id": "DF002",
            "severity": "HIGH",
            "file": "Dockerfile",
            "line": 1,
            "message": "Using latest tag makes the image non-reproducible",
            "remediation": "Pin to a specific digest or version tag",
            "category": "docker",
        }
    ]


def _run_pipeline(scan_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jobs, "clone_repo", _fake_clone)
    monkeypatch.setattr(jobs, "_run_sandbox", _fake_sandbox)
    jobs.run_scan(scan_id)


# ---------------------------------------------------------------------------
# Walking-skeleton E2E test
# ---------------------------------------------------------------------------


def test_full_pipeline_walking_skeleton(monkeypatch: pytest.MonkeyPatch) -> None:
    """One test that verifies every layer of the pipeline.

    Acceptance criteria (sprint3.md — Developer B / Quality / hardening):
    - create repository → create scan → run job → findings persisted
    - report generated
    - export (markdown) returns non-empty output
    - chunks stored (Sprint 3 RAG prep)
    """
    # 1. Create repository + queued scan via the API
    scan_id = create_scan()

    # 2. Run the job synchronously (no Docker, no Redis)
    _run_pipeline(scan_id, monkeypatch)

    # 3. Scan must have succeeded
    scan_resp = client.get(f"/api/scans/{scan_id}")
    assert scan_resp.status_code == 200
    assert scan_resp.json()["status"] == "succeeded"

    # 4. At least one finding must be persisted
    findings_resp = client.get(f"/api/scans/{scan_id}/findings")
    assert findings_resp.status_code == 200
    findings = findings_resp.json()
    assert len(findings) >= 1, "Expected at least one finding after the pipeline ran"
    rule_ids = {f["rule_id"] for f in findings}
    assert "DF002" in rule_ids

    # 5. Report must be generated with accurate totals
    report_resp = client.get(f"/api/scans/{scan_id}/report")
    assert report_resp.status_code == 200
    report = report_resp.json()
    assert report["total_findings"] == len(findings)
    assert report["severity_counts"]["high"] >= 1

    # 6. Markdown export must be non-empty and contain key content
    export_resp = client.get(f"/api/scans/{scan_id}/report/export?format=markdown")
    assert export_resp.status_code == 200
    assert export_resp.headers["content-type"].startswith("text/markdown")
    body = export_resp.text
    assert len(body) > 0, "Export body must not be empty"
    assert "# Security Report" in body
    assert f"**Total findings:** {len(findings)}" in body

    # 7. Chunks must be stored (RAG prep — Sprint 3 chunking pipeline)
    with SessionLocal() as session:
        chunk_count = session.query(Chunk).filter(Chunk.scan_id == scan_id, Chunk.user_id == STUB_USER_ID).count()
    assert chunk_count >= 1, (
        f"Expected at least one chunk for scan {scan_id}; " "check that chunk_scan_files is wired into run_scan"
    )


# ---------------------------------------------------------------------------
# Guard: pipeline must NOT create chunks for a failed scan
# ---------------------------------------------------------------------------


def test_failed_scan_produces_no_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chunking must not run when the sandbox raises an error."""
    scan_id = create_scan()

    def _raise_sandbox(repo_dir: str, analyzers: list[str]) -> list[dict]:
        raise RuntimeError("simulated sandbox failure")

    monkeypatch.setattr(jobs, "clone_repo", _fake_clone)
    monkeypatch.setattr(jobs, "_run_sandbox", _raise_sandbox)
    jobs.run_scan(scan_id)

    scan_resp = client.get(f"/api/scans/{scan_id}")
    assert scan_resp.json()["status"] == "failed"

    with SessionLocal() as session:
        chunk_count = session.query(Chunk).filter(Chunk.scan_id == scan_id).count()
    assert chunk_count == 0, "No chunks must be stored for a failed scan"
