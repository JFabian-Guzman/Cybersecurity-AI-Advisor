from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class ScanCreate(BaseModel):
    repository_id: uuid.UUID
    user_id: uuid.UUID
    status: str = "queued"


class ScanUpdate(BaseModel):
    status: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ScanResponse(BaseModel):
    id: uuid.UUID
    repository_id: uuid.UUID
    repository_name: str
    status: str
    error: str | None
    started_at: datetime | None
    finished_at: datetime | None

    model_config = {"from_attributes": True}
