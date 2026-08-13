from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_db
from models import Finding, Report, Scan, User

router = APIRouter(prefix="/api/scans", tags=["scans"])


class ScanResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    repository_name: str
    status: str
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class FindingResponse(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    rule_id: str
    severity: str
    category: str
    file_path: str
    line_number: int | None
    message: str
    remediation: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportResponse(BaseModel):
    scan_id: uuid.UUID
    total_findings: int
    severity_counts: dict[str, int]
    rule_counts: dict[str, int]
    category_counts: dict[str, int]
    created_at: datetime

    model_config = {"from_attributes": True}


def _get_owned_scan(scan_id: uuid.UUID, session: Session, current_user: User) -> Scan:
    scan = session.query(Scan).filter(Scan.id == scan_id, Scan.user_id == current_user.id).first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScanResponse:
    scan = _get_owned_scan(scan_id, session, current_user)
    return ScanResponse(
        id=scan.id,
        repository_id=scan.repository_id,
        repository_name=scan.repository.name,
        status=scan.status,
        error=scan.error,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
    )


@router.get("/{scan_id}/findings", response_model=list[FindingResponse])
def get_scan_findings(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[FindingResponse]:
    scan = _get_owned_scan(scan_id, session, current_user)
    findings = session.query(Finding).filter(Finding.scan_id == scan.id).all()
    return [
        FindingResponse(
            id=f.id,
            scan_id=f.scan_id,
            rule_id=f.rule_id,
            severity=f.severity,
            category=f.category,
            file_path=f.file_path,
            line_number=f.line_number,
            message=f.message,
            remediation=f.remediation,
            created_at=f.created_at,
        )
        for f in findings
    ]


@router.get("/{scan_id}/report", response_model=ReportResponse)
def get_scan_report(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ReportResponse:
    scan = _get_owned_scan(scan_id, session, current_user)

    if scan.status != "succeeded":
        raise HTTPException(
            status_code=409,
            detail=f"Report is not available while the scan is {scan.status}",
        )

    report = session.query(Report).filter(Report.scan_id == scan.id).first()
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    return ReportResponse(
        scan_id=report.scan_id,
        total_findings=report.total_findings,
        severity_counts=report.severity_counts,
        rule_counts=report.rule_counts,
        category_counts=report.category_counts,
        created_at=report.created_at,
    )
