from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from dependencies import get_current_user, get_db
from jobs import run_scan
from models import Repository, Scan, User
from worker import get_queue

log = structlog.get_logger()

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


class GitUrlRequest(BaseModel):
    url: HttpUrl
    name: str


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    source_ref: str
    scan_id: uuid.UUID

    model_config = {"from_attributes": True}


class RepositoryListItem(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str

    model_config = {"from_attributes": True}


@router.post("", response_model=RepositoryResponse, status_code=201)
def connect_repository(
    body: GitUrlRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RepositoryResponse:
    repo = Repository(
        user_id=current_user.id,
        name=body.name,
        source_type="git_url",
        source_ref=str(body.url),
    )
    session.add(repo)
    session.flush()

    scan = Scan(
        repository_id=repo.id,
        user_id=current_user.id,
        status="queued",
    )
    session.add(scan)
    session.commit()
    session.refresh(repo)
    session.refresh(scan)

    get_queue().enqueue(run_scan, scan.id)
    log.info("repository.connected", repo_id=str(repo.id), scan_id=str(scan.id))

    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        source_type=repo.source_type,
        source_ref=repo.source_ref,
        scan_id=scan.id,
    )


@router.post("/upload", status_code=501)
def upload_repository() -> None:
    raise HTTPException(
        status_code=501,
        detail=("Archive upload is not implemented yet. " "Connect a public Git repository URL instead."),
    )


@router.get("", response_model=list[RepositoryListItem])
def list_repositories(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> list[RepositoryListItem]:
    repos = session.query(Repository).filter(Repository.user_id == current_user.id).all()
    return [RepositoryListItem(id=r.id, name=r.name, source_type=r.source_type) for r in repos]
