from __future__ import annotations

import uuid
from typing import Annotated, Literal

import structlog
from fastapi import APIRouter, Body, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.jobs import run_scan
from app.models import Scan, User
from app.reporting.export import build_export_document, render_markdown, render_pdf
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


def _get_succeeded_scan_with_report(
    scan_id: uuid.UUID,
    session: Session,
    current_user: User,
) -> tuple[Scan, object]:
    """Return (scan, report) or raise the appropriate HTTP error.

    Enforces the three-step access guard shared by report-related endpoints:
      404 — scan not found or not owned by the current user
      409 — scan exists but has not succeeded yet
      404 — scan succeeded but has no report (shouldn't happen in production;
             guards against incomplete pipeline runs during development)
    """
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

    return scan, report


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
    _scan, report = _get_succeeded_scan_with_report(scan_id, session, current_user)
    return ReportResponse.model_validate(report)


@router.get("/{scan_id}/report/export", response_model=None)
def export_scan_report(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    format: Annotated[Literal["markdown", "pdf"], Query()] = "markdown",
) -> Response:
    """Export the scan report as a downloadable file.

    Query parameters:
        format: ``markdown`` or ``pdf``.

    Responses:
        200 text/markdown — Markdown export with Content-Disposition attachment.
        200 application/pdf — PDF export with Content-Disposition attachment.
        409 — Scan has not succeeded yet.
        404 — Scan not owned by the current user, or report missing.
        422 — ``format`` is not ``markdown`` or ``pdf``.
    """
    scan, report = _get_succeeded_scan_with_report(scan_id, session, current_user)

    repo_name: str = scan.repository.name
    doc = build_export_document(report, repo_name)

    if format == "markdown":
        content = render_markdown(doc)
        filename = f"{doc.repo_slug}-{doc.scan_id}.md"
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # format == "pdf"
    content = render_pdf(doc)
    filename = f"{doc.repo_slug}-{doc.scan_id}.pdf"
    return Response(
        content=content,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
