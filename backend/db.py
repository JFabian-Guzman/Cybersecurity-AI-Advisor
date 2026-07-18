import os
from datetime import UTC, datetime

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

load_dotenv()


def _normalized_database_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://cybersec:cybersec@localhost:5433/cybersec",
    )
    for prefix in ("postgresql://", "postgres://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


engine: Engine = create_engine(_normalized_database_url(), pool_pre_ping=True)


def check_database() -> dict[str, object]:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()
    return {
        "database": "ok",
        "select_1": result,
        "checked_at": datetime.now(UTC).isoformat(),
    }
