from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import app.jobs as jobs
from app.db.db import engine
from app.main import app
from app.models import Scan

client = TestClient(app)


def _create_scan() -> uuid.UUID:
    connect_response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert connect_response.status_code == 201
    repository_id = connect_response.json()["id"]

    scan_response = client.post(f"/api/repositories/{repository_id}/scans")
    assert scan_response.status_code == 201
    return uuid.UUID(scan_response.json()["id"])


def test_run_scan_always_requests_all_analyzers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression test for K8s findings never showing up in reports: jobs.run_scan used to
    gate which sandbox analyzers ran on ingestion/classify.py's pre-clone heuristic, which
    silently missed common layouts (e.g. a multi-document YAML with a non-workload document
    before the workload document, outside any k8s/kubernetes/manifests folder). The fix is
    to always request every analyzer and let each one decide for itself whether it finds
    anything, so this asserts "kubernetes" is requested regardless of repo content."""
    scan_id = _create_scan()
    captured_analyzers: list[str] = []

    def fake_clone_repo(url: str, dest_dir: str, timeout_seconds: int, max_clone_mb: int) -> None:
        with open(os.path.join(dest_dir, "manifests.yaml"), "w") as fh:
            fh.write(
                "apiVersion: v1\n"
                "kind: Namespace\n"
                "metadata:\n"
                "  name: demo\n"
                "---\n"
                "apiVersion: apps/v1\n"
                "kind: Deployment\n"
                "metadata:\n"
                "  name: demo\n"
                "spec:\n"
                "  template:\n"
                "    spec:\n"
                "      containers:\n"
                "        - name: app\n"
                "          image: demo:latest\n"
                "          securityContext:\n"
                "            privileged: true\n"
            )

    def fake_run_sandbox(repo_dir: str, analyzers: list[str]) -> list[dict]:
        captured_analyzers.extend(analyzers)
        return []

    monkeypatch.setattr(jobs, "clone_repo", fake_clone_repo)
    monkeypatch.setattr(jobs, "_run_sandbox", fake_run_sandbox)

    jobs.run_scan(scan_id)

    assert "kubernetes" in captured_analyzers
    assert "docker" in captured_analyzers

    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        assert scan is not None
        assert scan.status == "succeeded"
