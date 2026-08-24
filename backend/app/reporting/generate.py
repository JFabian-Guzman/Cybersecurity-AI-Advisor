from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy.orm import Session

from app.models import Finding, Report
from app.schemas.report import ReportFinding
from app.services.findings_services import get_findings_by_scan_id
from app.services.report_services import create_report, delete_report_by_scan_id

SEVERITY_LEVELS = ("critical", "high", "medium", "low", "info")


def add_report_findings(findings: Sequence[Finding]) -> ReportFinding:
    severity_counts = dict.fromkeys(SEVERITY_LEVELS, 0)
    rule_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        rule_counts[finding.rule_id] = rule_counts.get(finding.rule_id, 0) + 1
        category_counts[finding.category] = category_counts.get(finding.category, 0) + 1

    return ReportFinding(
        total_findings=len(findings),
        severity_counts=severity_counts,
        rule_counts=rule_counts,
        category_counts=category_counts,
    )


def generate_report(session: Session, scan_id: uuid.UUID, user_id: uuid.UUID) -> Report:
    findings = get_findings_by_scan_id(session, scan_id, user_id)
    data = add_report_findings(findings)

    delete_report_by_scan_id(session, scan_id)

    report = create_report(
        session,
        Report(
            scan_id=scan_id,
            user_id=user_id,
            total_findings=data.total_findings,
            severity_counts=data.severity_counts,
            rule_counts=data.rule_counts,
            category_counts=data.category_counts,
        ),
    )
    return report
