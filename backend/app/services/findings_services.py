from sqlalchemy.orm import Session

from app.models import Finding


def get_findings_by_scan_id(db: Session, scan_id: str) -> list[Finding]:
    return db.query(Finding).filter(Finding.scan_id == scan_id).all()

def create_finding(db: Session, finding: Finding) -> Finding:
    db.add(finding)
    db.commit()
    db.refresh(finding)
    return finding