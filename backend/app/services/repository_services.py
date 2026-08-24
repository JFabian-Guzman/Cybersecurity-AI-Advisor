from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.models import Repository
from app.schemas.repository import RepositoryCreate


def get_repository(db: Session, user_id: uuid.UUID, source_ref: str) -> Repository | None:
    return db.query(Repository).filter(Repository.user_id == user_id, Repository.source_ref == source_ref).first()


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
