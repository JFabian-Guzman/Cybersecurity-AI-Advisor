from __future__ import annotations

import json
import os
import shutil
import tempfile
import uuid
from datetime import UTC, datetime

import docker
import structlog
from docker.errors import DockerException

from app.db.db import SessionLocal
from app.ingestion.clone import clone_repo
from app.models import Finding
from app.reporting.generate import generate_report
from app.schemas.scan import ScanUpdate
from app.services.findings_services import create_finding
from app.services.scan_services import get_scan, update_scan

log = structlog.get_logger()

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "cybersecurity-ai-advisor-sandbox")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120"))
SANDBOX_MAX_CLONE_MB = int(os.getenv("SANDBOX_MAX_CLONE_MB", "500"))

_SEVERITY_MAP = {
    "CRITICAL": "critical",
    "HIGH": "high",
    "MEDIUM": "medium",
    "LOW": "low",
    "INFO": "info",
}

_ANALYZER_CATEGORIES = ("docker", "kubernetes")


def _run_sandbox(repo_path: str, analyzers: list[str]) -> list[dict]:
    client = docker.from_env()
    container = None
    try:
        container = client.containers.create(
            image=SANDBOX_IMAGE,
            volumes={repo_path: {"bind": "/repo", "mode": "ro"}},
            environment={"ANALYZERS": ",".join(analyzers)},
            network_mode="none",
            read_only=True,
            tmpfs={"/tmp": "size=512m"},
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            mem_limit="512m",
            nano_cpus=1_000_000_000,
            pids_limit=128,
        )
        container.start()
        result = container.wait(timeout=SANDBOX_TIMEOUT)
        if result.get("StatusCode") != 0:
            stderr = container.logs(stdout=False, stderr=True).decode()
            raise RuntimeError(f"Sandbox exited with code {result.get('StatusCode')}: {stderr}")
        output = container.logs(stdout=True, stderr=False).decode()
        log.info("sandbox_output", output=output)
        return json.loads(output)
    except DockerException as exc:
        raise RuntimeError(f"Failed to run sandbox container: {exc}") from exc
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except DockerException:
                pass


def run_scan(scan_id: uuid.UUID) -> None:
    with SessionLocal() as session:
        scan = get_scan(session, scan_id)
        if scan is None:
            log.error("job.scan_not_found", scan_id=str(scan_id))
            return

        tmp_dir = tempfile.mkdtemp(prefix="scan-")
        try:
            update_scan(session, scan_id, ScanUpdate(status="running"))
            log.info("job.scan_running", scan_id=str(scan_id))

            repo = scan.repository
            if repo.source_type != "git_url":
                raise RuntimeError(f"Unsupported source type for scanning: {repo.source_type}")

            clone_repo(repo.source_ref, tmp_dir, timeout_seconds=SANDBOX_TIMEOUT, max_clone_mb=SANDBOX_MAX_CLONE_MB)

            analyzers = list(_ANALYZER_CATEGORIES)
            raw_findings = _run_sandbox(tmp_dir, analyzers)
            log.info("analyzers", analyzers=analyzers)

            for item in raw_findings:
                create_finding(
                    session,
                    Finding(
                        scan_id=scan.id,
                        user_id=scan.user_id,
                        rule_id=item["rule_id"],
                        severity=_SEVERITY_MAP.get(item["severity"], "low"),
                        file_path=item["file"],
                        line_number=item["line"],
                        message=item["message"],
                        remediation=item["remediation"],
                        category=item.get("category", "docker"),
                    ),
                )

            generate_report(session, scan_id, scan.user_id)

            update_scan(session, scan_id, ScanUpdate(status="succeeded", finished_at=datetime.now(UTC)))
            log.info("job.scan_succeeded", scan_id=str(scan_id), findings=len(raw_findings))

        except Exception as exc:
            session.rollback()
            update_scan(session, scan_id, ScanUpdate(status="failed", error=str(exc), finished_at=datetime.now(UTC)))
            log.error("job.scan_failed", scan_id=str(scan_id), error=str(exc))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
