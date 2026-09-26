from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Repository, Scan
from app.schemas.repository import RepositoryCreate


def get_repository(db: Session, user_id: uuid.UUID, source_ref: str) -> Repository | None:
    return db.query(Repository).filter(Repository.user_id == user_id, Repository.source_ref == source_ref).first()


def get_repository_by_id(db: Session, repository_id: uuid.UUID, user_id: uuid.UUID) -> Repository | None:
    return db.query(Repository).filter(Repository.id == repository_id, Repository.user_id == user_id).first()


def create_repository(db: Session, repository: RepositoryCreate) -> Repository:
    db_repository = Repository(
        user_id=repository.user_id,
        name=repository.name,
        source_type=repository.source_type,
        source_ref=repository.source_ref,
    )
    db.add(db_repository)
    db.commit()
    db.refresh(db_repository)
    return db_repository


def get_repositories_by_user(
    db: Session, user_id: uuid.UUID, limit: int, offset: int
) -> list[tuple[Repository, str | None]]:
    latest_scan_rank = select(
        Scan.repository_id,
        Scan.status,
        func.row_number().over(partition_by=Scan.repository_id, order_by=Scan.created_at.desc()).label("rn"),
    ).subquery()
    latest_scan = (
        select(latest_scan_rank.c.repository_id, latest_scan_rank.c.status).where(latest_scan_rank.c.rn == 1).subquery()
    )

    return (
        db.query(Repository, latest_scan.c.status)
        .outerjoin(latest_scan, latest_scan.c.repository_id == Repository.id)
        .filter(Repository.user_id == user_id)
        .order_by(Repository.id)
        .offset(offset)
        .limit(limit)
        .all()
    )


def count_repositories_by_user(db: Session, user_id: uuid.UUID) -> int:
    return db.query(Repository).filter(Repository.user_id == user_id).count()
