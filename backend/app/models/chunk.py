from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.scan import Scan


class Chunk(Base):
    """A text chunk extracted from a scanned repository file.

    Chunks are produced by the worker after the sandbox run completes.
    They are the raw material for RAG retrieval in Sprint 4.

    Design decisions (see ADR-0003):
    - No ``embedding`` column this sprint: the vector dimension depends on the
      LLM provider, which is not yet decided.
    - ``token_count`` uses the heuristic ``ceil(len(content) / 4)`` so it is
      non-zero and proportional to length without coupling to any tokenizer.
    - ``chunk_index`` restarts from 0 for each (scan, source_path) pair.
    - The unique constraint on (scan_id, source_path, chunk_index) prevents
      duplicate insertions on retry.
    """

    __tablename__ = "chunks"

    __table_args__ = (UniqueConstraint("scan_id", "source_path", "chunk_index", name="uq_chunks_scan_path_index"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_path: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    scan: Mapped[Scan] = relationship("Scan", back_populates="chunks")

    @staticmethod
    def compute_token_count(content: str) -> int:
        """Heuristic: 1 token ≈ 4 characters (GPT-family rule of thumb).

        Keeps token_count non-zero and proportional to length without
        coupling to any specific tokenizer library.
        """
        return math.ceil(len(content) / 4)
