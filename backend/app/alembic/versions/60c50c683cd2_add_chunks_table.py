"""add chunks table

Revision ID: 60c50c683cd2
Revises: d4100e9f2b1a
Create Date: 2026-09-18 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "60c50c683cd2"
down_revision: str | Sequence[str] | None = "d4100e9f2b1a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the chunks table.

    Chunks are text segments extracted from repository files by the worker.
    They are the input material for RAG retrieval (Sprint 4).

    Design notes:
    - No ``embedding`` column: vector dimension depends on the LLM provider,
      which is undecided.  Adding it now would guarantee a redo migration.
    - ``token_count`` stores a heuristic value (ceil(len(content) / 4)).
    - The unique constraint on (scan_id, source_path, chunk_index) prevents
      duplicate rows on worker retry.
    """
    op.create_table(
        "chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "scan_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scan_id", "source_path", "chunk_index", name="uq_chunks_scan_path_index"),
    )
    op.create_index("ix_chunks_scan_id", "chunks", ["scan_id"])
    op.create_index("ix_chunks_user_id", "chunks", ["user_id"])


def downgrade() -> None:
    """Drop the chunks table."""
    op.drop_index("ix_chunks_user_id", table_name="chunks")
    op.drop_index("ix_chunks_scan_id", table_name="chunks")
    op.drop_table("chunks")
