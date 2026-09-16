from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.models import Report

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")


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


def render_markdown(doc: ExportDocument) -> bytes:
    """Render an :class:`ExportDocument` as UTF-8 encoded Markdown.

    The output is deterministic: sections always appear in the same order and
    severity rows follow CRITICAL → HIGH → MEDIUM → LOW → INFO regardless of
    the order they are stored in the database.

    Args:
        doc: The format-agnostic export document produced by
            :func:`build_export_document`.

    Returns:
        UTF-8 encoded Markdown bytes suitable for a ``text/markdown`` HTTP response.
    """
    lines: list[str] = []

    # Header
    lines.append(f"# Security Report — {doc.repo_name}")
    lines.append("")
    lines.append(f"**Scan ID:** `{doc.scan_id}`")
    lines.append(f"**Total findings:** {doc.total_findings}")
    lines.append("")

    # Severity breakdown
    lines.append("## Findings by Severity")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for severity in _SEVERITY_ORDER:
        count = doc.severity_counts.get(severity, 0)
        lines.append(f"| {severity.capitalize()} | {count} |")
    lines.append("")

    # Category breakdown
    lines.append("## Findings by Category")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for category, count in sorted(doc.category_counts.items()):
        lines.append(f"| {category.capitalize()} | {count} |")
    lines.append("")

    # Rule breakdown
    lines.append("## Findings by Rule")
    lines.append("")
    lines.append("| Rule ID | Count |")
    lines.append("|---------|-------|")
    for rule_id, count in sorted(doc.rule_counts.items()):
        lines.append(f"| {rule_id} | {count} |")
    lines.append("")

    return "\n".join(lines).encode("utf-8")
