import os

from dotenv import load_dotenv

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


DATABASE_URL = _normalized_database_url()
