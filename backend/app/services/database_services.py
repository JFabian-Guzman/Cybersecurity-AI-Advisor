from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from app.db.db import engine


def check_database() -> dict[str, object]:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()
    return {
        "database": "ok",
        "select_1": result,
        "checked_at": datetime.now(UTC).isoformat(),
    }
