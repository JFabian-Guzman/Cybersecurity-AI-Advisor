from __future__ import annotations

import uuid
from typing import Any, cast

from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.models.chunk import Chunk
from app.models.scan import Scan

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


def delete_superseded_chunks(session: Session, scan: Scan) -> int:
    """Delete chunks from this repository's older scans; return how many were removed.

    Only scans created before *scan* count as superseded, so an older scan that finishes late
    never wipes a newer scan's chunks. The caller commits, so the delete lands atomically with
    the scan being marked ``succeeded`` and is rolled back if that fails.
    """
    older_scan_ids = select(Scan.id).where(
        Scan.repository_id == scan.repository_id,
        Scan.user_id == scan.user_id,
        Scan.id != scan.id,
        Scan.created_at < scan.created_at,
    )
    statement = (
        delete(Chunk)
        .where(Chunk.user_id == scan.user_id, Chunk.scan_id.in_(older_scan_ids))
        .execution_options(synchronize_session=False)
    )
    result = cast(CursorResult[Any], session.execute(statement))
    return result.rowcount


def get_chunks_by_scan_id(session: Session, scan_id: uuid.UUID, user_id: uuid.UUID) -> list[Chunk]:
    """Return all chunks for *scan_id* owned by *user_id*, ordered by path and index."""
    return (
        session.query(Chunk)
        .filter(Chunk.scan_id == scan_id, Chunk.user_id == user_id)
        .order_by(Chunk.source_path, Chunk.chunk_index)
        .all()
    )
