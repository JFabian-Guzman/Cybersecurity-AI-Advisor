import uuid

from sqlalchemy.orm import Session

from app.models import Finding


def get_findings_by_scan_id(
    db: Session,
    scan_id: uuid.UUID,
    user_id: uuid.UUID,
    severities: list[str] | None = None,
    categories: list[str] | None = None,
) -> list[Finding]:
    query = db.query(Finding).filter(Finding.scan_id == scan_id, Finding.user_id == user_id)
    if severities:
        query = query.filter(Finding.severity.in_(severities))
    if categories:
        query = query.filter(Finding.category.in_(categories))
    return query.all()


def create_finding(db: Session, finding: Finding) -> Finding:
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding
