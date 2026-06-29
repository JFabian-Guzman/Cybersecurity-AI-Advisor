from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime

import docker
import structlog
from docker.errors import ContainerError, DockerException
from sqlalchemy.orm import Session

from db import engine
from models import Scan

log = structlog.get_logger()

SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "cybersecurity-ai-advisor-sandbox")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT_SECONDS", "120"))
SANDBOX_MAX_CLONE_MB = int(os.getenv("SANDBOX_MAX_CLONE_MB", "500"))


def _run_sandbox(source_type: str, source_ref: str) -> list[str]:
    client = docker.from_env()
    try:
        result = client.containers.run(
            image=SANDBOX_IMAGE,
            environment={
                "SOURCE_TYPE": source_type,
                "SOURCE_REF": source_ref,
                "MAX_CLONE_MB": str(SANDBOX_MAX_CLONE_MB),
            },
            network_mode="none",
            read_only=True,
            tmpfs={"/tmp": "size=512m"},
            cap_drop=["ALL"],
            security_opt=["no-new-privileges:true"],
            mem_limit="512m",
            nano_cpus=1_000_000_000,
            pids_limit=128,
            remove=True,
            stdout=True,
            stderr=False,
        )
        output = result.decode() if isinstance(result, bytes) else result
        log.info("sandbox.completed", output=output)
        return []
    except ContainerError as exc:
        raise RuntimeError(f"Sandbox container exited with error: {exc.stderr}") from exc
    except DockerException as exc:
        raise RuntimeError(f"Failed to launch sandbox container: {exc}") from exc


def run_scan(scan_id: uuid.UUID) -> None:
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        if scan is None:
            log.error("job.scan_not_found", scan_id=str(scan_id))
            return

        try:
            scan.status = "running"
            scan.started_at = datetime.now(UTC)
            session.commit()
            log.info("job.scan_running", scan_id=str(scan_id))

            repo = scan.repository
            findings: list[str] = _run_sandbox(repo.source_type, repo.source_ref)

            scan.status = "succeeded"
            scan.finished_at = datetime.now(UTC)
            session.commit()
            log.info("job.scan_succeeded", scan_id=str(scan_id), findings=len(findings))

        except Exception as exc:
            scan.status = "failed"
            scan.error = str(exc)
            scan.finished_at = datetime.now(UTC)
            session.commit()
            log.error("job.scan_failed", scan_id=str(scan_id), error=str(exc))
