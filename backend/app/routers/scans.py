from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.jobs import run_scan
from app.models import User
from app.schemas.finding import FindingResponse
from app.schemas.report import ReportResponse
from app.schemas.scan import ScanCreate, ScanResponse
from app.services.findings_services import get_findings_by_scan_id
from app.services.report_services import get_report_by_scan_id
from app.services.scan_services import create_scan as create_scan_service
from app.services.scan_services import get_scan as get_scan_service
from app.services.scan_services import to_scan_response
from app.services.user_services import get_current_user
from app.worker import get_queue

log = structlog.get_logger()

router = APIRouter(prefix="/api/scans", tags=["scans"])


@router.post("", response_model=ScanResponse, status_code=201)
def create_scan(
    repository_id: Annotated[uuid.UUID, Body(embed=True)],
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScanResponse:
    scan = create_scan_service(
        session,
        ScanCreate(
            repository_id=repository_id,
            user_id=current_user.id,
            status="queued",
        ),
    )

    get_queue().enqueue(run_scan, scan.id)
    log.info("scan.triggered", repo_id=str(repository_id), scan_id=str(scan.id))

    return to_scan_response(scan)


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScanResponse:
    scan = get_scan_service(session, scan_id, current_user.id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return to_scan_response(scan)


@router.get("/{scan_id}/findings", response_model=list[FindingResponse])
def get_scan_findings(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FindingResponse]:
    scan = get_scan_service(session, scan_id, current_user.id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    findings = get_findings_by_scan_id(session, scan.id, current_user.id)
    return [FindingResponse.model_validate(f) for f in findings]


@router.get("/{scan_id}/report", response_model=ReportResponse)
def get_scan_report(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportResponse:
    scan = get_scan_service(session, scan_id, current_user.id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail=f"Report is not available while the scan is {scan.status}",
        )

    report = get_report_by_scan_id(session, scan.id, current_user.id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse.model_validate(report)
