from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models import User
from app.schemas.repository import GitUrlRequest, RepositoryCreate, RepositoryListResponse, RepositoryResponse
from app.services.repository_services import (
    count_repositories_by_user,
    create_repository,
    get_repositories_by_user,
    get_repository,
)
from app.services.user_services import get_current_user

log = structlog.get_logger()

router = APIRouter(prefix="/api/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=201)
def connect_repository(
    body: GitUrlRequest,
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> RepositoryResponse:
    source_ref = str(body.url)

    repository = get_repository(session, current_user.id, source_ref)
    if repository is None:
        repository = create_repository(
            session,
            RepositoryCreate(
                user_id=current_user.id,
                name=body.name,
                source_type="git_url",
                source_ref=source_ref,
            ),
        )
        log.info("repository.connected", repo_id=str(repository.id))

    return RepositoryResponse.model_validate(repository)

@router.get("", response_model=RepositoryListResponse)
def list_repositories(
    session: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> RepositoryListResponse:
    repositories = get_repositories_by_user(session, current_user.id, limit, offset)
    total = count_repositories_by_user(session, current_user.id)
    return RepositoryListResponse(
        items=[RepositoryResponse.model_validate(repo) for repo in repositories],
        total=total,
    )
