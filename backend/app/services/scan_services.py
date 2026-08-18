from sqlalchemy.orm import Session

from app.models import Scan
from app.schemas.scan import ScanCreate, ScanUpdate


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


def get_scan(db: Session, scan_id: str) -> Scan | None:
    return db.query(Scan).filter(Scan.id == scan_id).first()


def update_scan(db: Session, scan_id: str, updates: ScanUpdate) -> Scan | None:
    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if scan:
        for field, value in updates.model_dump(exclude_unset=True).items():
            setattr(scan, field, value)
        db.commit()
        db.refresh(scan)
    return scan
