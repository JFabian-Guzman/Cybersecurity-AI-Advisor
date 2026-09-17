"""add finding category, expand severity enum, add reports table

Revision ID: d4100e9f2b1a
Revises: 3073274850c8
Create Date: 2026-07-18 14:57:40.257275

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4100e9f2b1a"
down_revision: str | Sequence[str] | None = "3073274850c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("findings", sa.Column("category", sa.String(32), nullable=False, server_default="docker"))

    op.execute("ALTER TYPE severity_enum RENAME TO severity_enum_old")
    sa.Enum("critical", "high", "medium", "low", "info", name="severity_enum").create(op.get_bind())
    op.execute("ALTER TABLE findings ALTER COLUMN severity TYPE severity_enum USING severity::text::severity_enum")
    op.execute("DROP TYPE severity_enum_old")

    op.create_table(
        "reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("severity_counts", postgresql.JSONB, nullable=False),
        sa.Column("rule_counts", postgresql.JSONB, nullable=False),
        sa.Column("category_counts", postgresql.JSONB, nullable=False),
        sa.Column("total_findings", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_reports_user_id", "reports", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_reports_user_id", table_name="reports")
    op.drop_table("reports")

    op.execute("ALTER TYPE severity_enum RENAME TO severity_enum_new")
    sa.Enum("high", "medium", "low", name="severity_enum").create(op.get_bind())
    op.execute("UPDATE findings SET severity = 'high' WHERE severity = 'critical'")
    op.execute("UPDATE findings SET severity = 'low' WHERE severity = 'info'")
    op.execute("ALTER TABLE findings ALTER COLUMN severity TYPE severity_enum USING severity::text::severity_enum")
    op.execute("DROP TYPE severity_enum_new")

    op.drop_column("findings", "category")
