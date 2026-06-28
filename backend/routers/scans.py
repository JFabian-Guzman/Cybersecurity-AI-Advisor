from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_db
from models import Scan, User

router = APIRouter(prefix="/api/scans", tags=["scans"])


class ScanResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    status: str
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}


@router.get("/{scan_id}", response_model=ScanResponse)
def get_scan(
    scan_id: uuid.UUID,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> ScanResponse:
    scan = session.query(Scan).filter(Scan.id == scan_id, Scan.user_id == current_user.id).first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResponse(
        id=scan.id,
        repository_id=scan.repository_id,
        status=scan.status,
        error=scan.error,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
    )
