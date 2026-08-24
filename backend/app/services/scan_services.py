import uuid

from sqlalchemy.orm import Session

from app.models import Scan
from app.schemas.scan import ScanCreate, ScanResponse, ScanUpdate


def create_scan(db: Session, scan: ScanCreate) -> Scan:
    db_scan = Scan(
        repository_id=scan.repository_id,
        user_id=scan.user_id,
        status=scan.status,
    )
    db.add(db_scan)
    db.commit()
    db.refresh(db_scan)
    return db_scan


def to_scan_response(scan: Scan) -> ScanResponse:
    return ScanResponse(
        id=scan.id,
        repository_id=scan.repository_id,
        repository_name=scan.repository.name,
        status=scan.status,
        error=scan.error,
        started_at=scan.started_at,
        finished_at=scan.finished_at,
    )


def get_scan(db: Session, scan_id: uuid.UUID, user_id: uuid.UUID | None = None) -> Scan | None:
    query = db.query(Scan).filter(Scan.id == scan_id)
    if user_id is not None:
        query = query.filter(Scan.user_id == user_id)
    return query.first()


def update_scan(db: Session, scan_id: uuid.UUID, updates: ScanUpdate) -> Scan | None:
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if scan:
        for field, value in updates.model_dump(exclude_unset=True).items():
            setattr(scan, field, value)
        db.commit()
        db.refresh(scan)
    return scan
