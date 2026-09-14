from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models import Report


@dataclass(frozen=True)
class ExportDocument:
    """Format-agnostic representation of a scan report ready for export.

    Built once from a persisted ``Report`` + scan metadata; passed to a renderer
    (``render_markdown`` or ``render_pdf``) to produce the final bytes.  Keeping
    the two steps separate guarantees that both formats cover identical content by
    construction rather than by discipline.
    """

    scan_id: uuid.UUID
    repo_name: str
    repo_slug: str  # URL-safe name used in Content-Disposition filenames
    total_findings: int
    severity_counts: dict[str, int]
    rule_counts: dict[str, int]
    category_counts: dict[str, int]


def build_export_document(report: Report, repo_name: str) -> ExportDocument:
    """Construct an :class:`ExportDocument` from a persisted report row.

    Args:
        report: The ORM ``Report`` instance for the scan.
        repo_name: Human-readable repository name from ``scan.repository.name``;
            already resolved by ``to_scan_response`` so no extra query is needed.

    Returns:
        An immutable :class:`ExportDocument` ready to be handed to a renderer.
    """
    repo_slug = repo_name.lower().replace(" ", "-")
    return ExportDocument(
        scan_id=report.scan_id,
        repo_name=repo_name,
        repo_slug=repo_slug,
        total_findings=report.total_findings,
        severity_counts=dict(report.severity_counts),
        rule_counts=dict(report.rule_counts),
        category_counts=dict(report.category_counts),
    )
