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
from sqlalchemy.orm import Session

from db import engine
from ingestion.clone import clone_repo
from models import Finding, Scan
from reporting.generate import generate_report

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


def _run_sandbox(repo_dir: str) -> list[dict]:
    client = docker.from_env()
    container = None
    try:
        container = client.containers.create(
            image=SANDBOX_IMAGE,
            volumes={repo_dir: {"bind": "/repo", "mode": "ro"}},
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
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is None:
            log.error("job.scan_not_found", scan_id=str(scan_id))
            return

        tmp_dir = tempfile.mkdtemp(prefix="scan-")
        try:
            scan.status = "running"
            scan.started_at = datetime.now(UTC)
            session.commit()
            log.info("job.scan_running", scan_id=str(scan_id))

            repo = scan.repository
            if repo.source_type != "git_url":
                raise RuntimeError(f"Unsupported source type for scanning: {repo.source_type}")

            clone_repo(repo.source_ref, tmp_dir, timeout_seconds=SANDBOX_TIMEOUT, max_clone_mb=SANDBOX_MAX_CLONE_MB)
            raw_findings = _run_sandbox(tmp_dir)

            for item in raw_findings:
                session.add(
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
                    )
                )

            session.flush()
            generate_report(session, scan)

            scan.status = "succeeded"
            scan.finished_at = datetime.now(UTC)
            session.commit()
            log.info("job.scan_succeeded", scan_id=str(scan_id), findings=len(raw_findings))

        except Exception as exc:
            session.rollback()
            scan.status = "failed"
            scan.error = str(exc)
            scan.finished_at = datetime.now(UTC)
            session.commit()
            log.error("job.scan_failed", scan_id=str(scan_id), error=str(exc))
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
