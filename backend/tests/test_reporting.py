from __future__ import annotations

import uuid

from models import Finding
from reporting.generate import aggregate


def _finding(rule_id: str, severity: str, category: str = "docker") -> Finding:
    return Finding(
        id=uuid.uuid4(),
        scan_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        rule_id=rule_id,
        severity=severity,
        file_path="Dockerfile",
        line_number=1,
        message="message",
        remediation="remediation",
        category=category,
    )


def test_aggregate_empty() -> None:
    report = aggregate([])
    assert report.total_findings == 0
    assert report.severity_counts == {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0,
    }
    assert report.rule_counts == {}
    assert report.category_counts == {}


def test_aggregate_counts_by_severity() -> None:
    report = aggregate(
        [
            _finding("DF003", "critical"),
            _finding("DF001", "high"),
            _finding("DF002", "high"),
            _finding("DF005", "medium"),
        ]
    )
    assert report.severity_counts["critical"] == 1
    assert report.severity_counts["high"] == 2
    assert report.severity_counts["medium"] == 1
    assert report.severity_counts["low"] == 0
    assert report.severity_counts["info"] == 0


def test_aggregate_counts_by_rule() -> None:
    report = aggregate([_finding("DF001", "high"), _finding("DF001", "high"), _finding("DF004", "low")])
    assert report.rule_counts == {"DF001": 2, "DF004": 1}


def test_aggregate_counts_by_category() -> None:
    report = aggregate(
        [
            _finding("DF001", "high"),
            _finding("DF002", "medium"),
            _finding("K8S001", "high", category="kubernetes"),
        ]
    )
    assert report.category_counts == {"docker": 2, "kubernetes": 1}


def test_aggregate_total_matches_input_length() -> None:
    findings = [_finding("DF001", "high") for _ in range(7)]
    assert aggregate(findings).total_findings == 7
