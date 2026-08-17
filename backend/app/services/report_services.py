from sqlalchemy.orm import Session

from app.models import Report


def get_report_by_scan_id(db: Session, scan_id: str) -> Report | None:
    return db.query(Report).filter(Report.scan_id == scan_id).first()