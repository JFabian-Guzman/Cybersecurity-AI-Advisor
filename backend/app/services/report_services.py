import uuid

from sqlalchemy.orm import Session

from app.models import Report


def get_report_by_scan_id(db: Session, scan_id: uuid.UUID, user_id: uuid.UUID) -> Report | None:
    return db.query(Report).filter(Report.scan_id == scan_id, Report.user_id == user_id).first()


def create_report(db: Session, report: Report) -> Report:
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def delete_report_by_scan_id(db: Session, scan_id: uuid.UUID) -> None:
    db.query(Report).filter(Report.scan_id == scan_id).delete()
    db.commit()
