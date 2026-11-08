"""add cascade deletes for repositories

Revision ID: a7c3e91f4b2d
Revises: 60c50c683cd2
Create Date: 2026-11-08 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7c3e91f4b2d"
down_revision: str | Sequence[str] | None = "60c50c683cd2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Cascade repository deletes down to scans and findings.

    Reports and chunks already cascade from scans. With these two constraints, deleting a
    repository removes its scans, findings, reports and chunks in a single statement.
    """
    op.drop_constraint("scans_repository_id_fkey", "scans", type_="foreignkey")
    op.create_foreign_key(
        "scans_repository_id_fkey",
        "scans",
        "repositories",
        ["repository_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.drop_constraint("findings_scan_id_fkey", "findings", type_="foreignkey")
    op.create_foreign_key(
        "findings_scan_id_fkey",
        "findings",
        "scans",
        ["scan_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Restore the original foreign keys without cascade."""
    op.drop_constraint("findings_scan_id_fkey", "findings", type_="foreignkey")
    op.create_foreign_key("findings_scan_id_fkey", "findings", "scans", ["scan_id"], ["id"])

    op.drop_constraint("scans_repository_id_fkey", "scans", type_="foreignkey")
    op.create_foreign_key("scans_repository_id_fkey", "scans", "repositories", ["repository_id"], ["id"])
