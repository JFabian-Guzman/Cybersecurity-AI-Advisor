from __future__ import annotations

import uuid
from dataclasses import dataclass
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models import Report

_SEVERITY_ORDER = ("critical", "high", "medium", "low", "info")

_SEVERITY_COLORS = {
    "critical": colors.HexColor("#dc2626"),
    "high": colors.HexColor("#ea580c"),
    "medium": colors.HexColor("#ca8a04"),
    "low": colors.HexColor("#2563eb"),
    "info": colors.HexColor("#6b7280"),
}


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
    repo_slug: str
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

    lines.append(f"# Security Report — {doc.repo_name}")
    lines.append("")
    lines.append(f"**Scan ID:** `{doc.scan_id}`")
    lines.append(f"**Total findings:** {doc.total_findings}")
    lines.append("")

    lines.append("## Findings by Severity")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    for severity in _SEVERITY_ORDER:
        count = doc.severity_counts.get(severity, 0)
        lines.append(f"| {severity.capitalize()} | {count} |")
    lines.append("")

    lines.append("## Findings by Category")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for category, count in sorted(doc.category_counts.items()):
        lines.append(f"| {category.capitalize()} | {count} |")
    lines.append("")

    lines.append("## Findings by Rule")
    lines.append("")
    lines.append("| Rule ID | Count |")
    lines.append("|---------|-------|")
    for rule_id, count in sorted(doc.rule_counts.items()):
        lines.append(f"| {rule_id} | {count} |")
    lines.append("")

    return "\n".join(lines).encode("utf-8")


def render_pdf(doc: ExportDocument) -> bytes:
    """Render an :class:`ExportDocument` as a PDF binary.

    Uses reportlab with pure-Python wheels — no system-level dependencies
    (pango, cairo, gdk-pixbuf) required in the Docker image.  The PDF is
    built in memory and never touches disk.

    Args:
        doc: The format-agnostic export document produced by
            :func:`build_export_document`.

    Returns:
        PDF bytes suitable for an ``application/pdf`` HTTP response.
    """
    buffer = BytesIO()
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    story = []

    # Title
    story.append(Paragraph(f"Security Report — {doc.repo_name}", styles["Title"]))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph(f"<b>Scan ID:</b> {doc.scan_id}", styles["Normal"]))
    story.append(Paragraph(f"<b>Total findings:</b> {doc.total_findings}", styles["Normal"]))
    story.append(Spacer(1, 0.6 * cm))

    # Findings by Severity
    story.append(Paragraph("Findings by Severity", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * cm))

    severity_data = [["Severity", "Count"]]
    for severity in _SEVERITY_ORDER:
        count = doc.severity_counts.get(severity, 0)
        severity_data.append([severity.capitalize(), str(count)])

    severity_table = Table(severity_data, colWidths=[10 * cm, 5 * cm])
    severity_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(severity_table)
    story.append(Spacer(1, 0.6 * cm))

    # Findings by Category
    story.append(Paragraph("Findings by Category", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * cm))

    category_data = [["Category", "Count"]]
    for category, count in sorted(doc.category_counts.items()):
        category_data.append([category.capitalize(), str(count)])

    if len(category_data) == 1:
        category_data.append(["—", "0"])

    category_table = Table(category_data, colWidths=[10 * cm, 5 * cm])
    category_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(category_table)
    story.append(Spacer(1, 0.6 * cm))

    # Findings by Rule
    story.append(Paragraph("Findings by Rule", styles["Heading2"]))
    story.append(Spacer(1, 0.2 * cm))

    rule_data = [["Rule ID", "Count"]]
    for rule_id, count in sorted(doc.rule_counts.items()):
        rule_data.append([rule_id, str(count)])

    if len(rule_data) == 1:
        rule_data.append(["—", "0"])

    rule_table = Table(rule_data, colWidths=[10 * cm, 5 * cm])
    rule_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 0), (1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f8fafc"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(rule_table)

    pdf.build(story)
    return buffer.getvalue()
