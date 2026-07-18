from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from models import Finding

SEVERITY_LEVELS = ("critical", "high", "medium", "low", "info")


@dataclass(frozen=True)
class ReportData:
    total_findings: int
    severity_counts: dict[str, int]
    rule_counts: dict[str, int]
    category_counts: dict[str, int]


def aggregate(findings: Sequence[Finding]) -> ReportData:
    severity_counts = dict.fromkeys(SEVERITY_LEVELS, 0)
    rule_counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}

    for finding in findings:
        severity_counts[finding.severity] = severity_counts.get(finding.severity, 0) + 1
        rule_counts[finding.rule_id] = rule_counts.get(finding.rule_id, 0) + 1
        category_counts[finding.category] = category_counts.get(finding.category, 0) + 1

    return ReportData(
        total_findings=len(findings),
        severity_counts=severity_counts,
        rule_counts=rule_counts,
        category_counts=category_counts,
    )
