from sqlalchemy.orm import Session

from app.db.db import engine
from app.models import User
from app.services.user_services import STUB_USER_ID

STUB_USER_EMAIL = "stub@local.dev"


def seed() -> None:
    with Session(engine) as session:
        exists = session.get(User, STUB_USER_ID)
        if exists:
            print(f"Stub user already exists: {STUB_USER_EMAIL}")
            return
        session.add(User(id=STUB_USER_ID, email=STUB_USER_EMAIL))
        session.commit()
        print(f"Stub user seeded: {STUB_USER_EMAIL} ({STUB_USER_ID})")


if __name__ == "__main__":
    seed()
