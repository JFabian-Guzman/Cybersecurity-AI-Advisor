from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.db.db import engine
from app.main import app

client = TestClient(app)


def _check_db_connectivity() -> None:
    """Fail fast with a clear message instead of waiting ~13 min for psycopg ConnectionTimeout."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.exit(
            f"Cannot connect to the database — is `docker compose up -d postgres` running "
            f"and mapped to port 5433? Original error: {exc}",
            returncode=1,
        )


@pytest.fixture(scope="session", autouse=True)
def require_db() -> None:
    """Session-scoped: checked once, fails fast with a readable message."""
    _check_db_connectivity()


def create_scan() -> uuid.UUID:
    """Create a repository + queued scan via the API; return the scan UUID.

    Used by integration tests that need a persisted scan row. The repository
    URL is synthetic — no real clone happens unless the test also triggers
    ``jobs.run_scan``.
    """
    connect_response = client.post(
        "/api/repositories",
        json={"url": "https://github.com/example/repo", "name": "test-repo"},
    )
    assert connect_response.status_code == 201
    repository_id = connect_response.json()["id"]

    scan_response = client.post("/api/scans", json={"repository_id": repository_id})
    assert scan_response.status_code == 201
    return uuid.UUID(scan_response.json()["id"])
