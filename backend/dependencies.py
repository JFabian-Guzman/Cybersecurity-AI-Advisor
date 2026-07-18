from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from db import engine
from models import User

STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_db() -> Generator[Session]:
    with Session(engine) as session:
        yield session


def get_current_user(session: Annotated[Session, Depends(get_db)]) -> User:
    user = session.get(User, STUB_USER_ID)
    if user is None:
        raise RuntimeError("Stub user not found — run seed.py first")
    return user
