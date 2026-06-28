from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from db import engine
from models import Scan

log = structlog.get_logger()


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

            # ToDo: stub — Dev B's analyze(repo_path) will replace this
            findings: list[str] = []

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
