from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.user import User

STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_current_user(db: Annotated[Session, Depends(get_db)]) -> User:
    user = db.get(User, STUB_USER_ID)
    if user is None:
        raise RuntimeError("Stub user not found — run seed.py first")
    return user
