from sqlalchemy.orm import Session

from app.models import Scan
from app.schemas.scan import ScanCreate


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