from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from app.models.chunk import Chunk

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Chunking configuration
# ---------------------------------------------------------------------------

CHUNK_SIZE: int = 1500
CHUNK_OVERLAP: int = 200
MAX_CHUNKS_PER_FILE: int = 50
MAX_CHUNKS_PER_SCAN: int = 2000


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def chunk_file_content(content: str, source_path: str, scan_id: uuid.UUID, user_id: uuid.UUID) -> list[Chunk]:
    """Split *content* into overlapping chunks and return unsaved ``Chunk`` objects.

    The caller is responsible for committing the session.  This function
    never touches the database — it only builds the ORM objects.
    """
    chunks: list[Chunk] = []
    step = CHUNK_SIZE - CHUNK_OVERLAP
    position = 0
    chunk_index = 0

    while position < len(content) and chunk_index < MAX_CHUNKS_PER_FILE:
        fragment = content[position : position + CHUNK_SIZE]
        chunks.append(
            Chunk(
                scan_id=scan_id,
                user_id=user_id,
                source_path=source_path,
                chunk_index=chunk_index,
                content=fragment,
                token_count=Chunk.compute_token_count(fragment),
            )
        )
        position += step
        chunk_index += 1

    return chunks


def chunk_scan_files(
    session: Session,
    scan_id: uuid.UUID,
    user_id: uuid.UUID,
    files: list[tuple[str, str]],
) -> int:
    """Chunk a list of *(source_path, content)* pairs and persist the results.

    Returns the total number of chunks persisted.
    Stops when MAX_CHUNKS_PER_SCAN is reached.
    """
    total = 0
    for source_path, content in files:
        if total >= MAX_CHUNKS_PER_SCAN:
            break
        remaining = MAX_CHUNKS_PER_SCAN - total
        file_chunks = chunk_file_content(content, source_path, scan_id, user_id)
        file_chunks = file_chunks[:remaining]
        for chunk in file_chunks:
            session.add(chunk)
        total += len(file_chunks)

    session.flush()
    return total


def get_chunks_by_scan_id(session: Session, scan_id: uuid.UUID, user_id: uuid.UUID) -> list[Chunk]:
    """Return all chunks for *scan_id* owned by *user_id*, ordered by path and index."""
    return (
        session.query(Chunk)
        .filter(Chunk.scan_id == scan_id, Chunk.user_id == user_id)
        .order_by(Chunk.source_path, Chunk.chunk_index)
        .all()
    )
