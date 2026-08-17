
import uuid

from sqlalchemy.orm import Session
from app.models.user import User

STUB_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_current_user(db: Session) -> User:
    user = db.get(User, STUB_USER_ID)
    if user is None:
        raise RuntimeError("Stub user not found — run seed.py first")
    return user