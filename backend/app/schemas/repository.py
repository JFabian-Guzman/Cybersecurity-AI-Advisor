from __future__ import annotations

import uuid

from pydantic import BaseModel, HttpUrl


class GitUrlRequest(BaseModel):
    url: HttpUrl
    name: str


class RepositoryCreate(BaseModel):
    user_id: uuid.UUID
    name: str
    source_type: str
    source_ref: str


class RepositoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    source_ref: str

    model_config = {"from_attributes": True}


class RepositoryListItem(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str

    model_config = {"from_attributes": True}
