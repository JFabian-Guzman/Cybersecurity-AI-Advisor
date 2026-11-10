from __future__ import annotations

import os
import uuid
from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import app.jobs as jobs
from app.db.db import engine
from app.models import Chunk, Repository, Scan, User
from app.services.user_services import STUB_USER_ID

SandboxRunner = Callable[[str, list[str]], list[dict]]

NOW = datetime.now(UTC)
EARLIER = NOW - timedelta(minutes=5)


def _create_user() -> uuid.UUID:
    with Session(engine) as session:
        user = User(email=f"other-{uuid.uuid4()}@example.com")
        session.add(user)
        session.commit()
        return user.id


def _create_repository(user_id: uuid.UUID = STUB_USER_ID) -> uuid.UUID:
    with Session(engine) as session:
        repository = Repository(
            user_id=user_id,
            name="retention-repo",
            source_type="git_url",
            source_ref=f"https://github.com/example/retention-{uuid.uuid4()}",
        )
        session.add(repository)
        session.commit()
        return repository.id


def _create_scan(repository_id: uuid.UUID, created_at: datetime, user_id: uuid.UUID = STUB_USER_ID) -> uuid.UUID:
    with Session(engine) as session:
        scan = Scan(repository_id=repository_id, user_id=user_id, status="queued", created_at=created_at)
        session.add(scan)
        session.commit()
        return scan.id


def _fake_clone(url: str, dest_dir: str, timeout_seconds: int, max_clone_mb: int) -> None:
    with open(os.path.join(dest_dir, "Dockerfile"), "w") as fh:
        fh.write("FROM python:3.14-slim\nUSER 1000\n")


def _empty_sandbox(repo_dir: str, analyzers: list[str]) -> list[dict]:
    return []


def _failing_sandbox(repo_dir: str, analyzers: list[str]) -> list[dict]:
    raise RuntimeError("simulated sandbox failure")


def _run_scan(scan_id: uuid.UUID, monkeypatch: pytest.MonkeyPatch, sandbox: SandboxRunner = _empty_sandbox) -> None:
    monkeypatch.setattr(jobs, "clone_repo", _fake_clone)
    monkeypatch.setattr(jobs, "_run_sandbox", sandbox)
    jobs.run_scan(scan_id)


def _chunk_count(scan_id: uuid.UUID) -> int:
    with Session(engine) as session:
        return session.scalar(select(func.count()).select_from(Chunk).where(Chunk.scan_id == scan_id)) or 0


def _scan_status(scan_id: uuid.UUID) -> str:
    with Session(engine) as session:
        scan = session.get(Scan, scan_id)
        assert scan is not None
        return scan.status


def test_successful_rescan_replaces_previous_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    repository_id = _create_repository()
    first_scan_id = _create_scan(repository_id, EARLIER)
    second_scan_id = _create_scan(repository_id, NOW)

    _run_scan(first_scan_id, monkeypatch)
    assert _chunk_count(first_scan_id) >= 1

    _run_scan(second_scan_id, monkeypatch)

    assert _scan_status(second_scan_id) == "succeeded"
    assert _chunk_count(first_scan_id) == 0
    assert _chunk_count(second_scan_id) >= 1


def test_failed_rescan_keeps_previous_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    repository_id = _create_repository()
    first_scan_id = _create_scan(repository_id, EARLIER)
    second_scan_id = _create_scan(repository_id, NOW)
    _run_scan(first_scan_id, monkeypatch)
    first_chunks = _chunk_count(first_scan_id)

    _run_scan(second_scan_id, monkeypatch, sandbox=_failing_sandbox)

    assert _scan_status(second_scan_id) == "failed"
    assert _chunk_count(first_scan_id) == first_chunks
    assert _chunk_count(second_scan_id) == 0


def test_chunking_failure_keeps_previous_chunks_and_scan_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    repository_id = _create_repository()
    first_scan_id = _create_scan(repository_id, EARLIER)
    second_scan_id = _create_scan(repository_id, NOW)
    _run_scan(first_scan_id, monkeypatch)
    first_chunks = _chunk_count(first_scan_id)

    def failing_chunking(*args: object, **kwargs: object) -> int:
        raise RuntimeError("simulated chunking failure")

    monkeypatch.setattr(jobs, "chunk_scan_files", failing_chunking)
    _run_scan(second_scan_id, monkeypatch)

    assert _scan_status(second_scan_id) == "succeeded"
    assert _chunk_count(first_scan_id) == first_chunks
    assert _chunk_count(second_scan_id) == 0


def test_rescan_never_touches_other_repositories_or_users(monkeypatch: pytest.MonkeyPatch) -> None:
    other_user_id = _create_user()
    other_repository_id = _create_repository(user_id=other_user_id)
    other_scan_id = _create_scan(other_repository_id, EARLIER, user_id=other_user_id)
    _run_scan(other_scan_id, monkeypatch)
    other_chunks = _chunk_count(other_scan_id)

    repository_id = _create_repository()
    first_scan_id = _create_scan(repository_id, EARLIER)
    second_scan_id = _create_scan(repository_id, NOW)
    _run_scan(first_scan_id, monkeypatch)
    _run_scan(second_scan_id, monkeypatch)

    assert other_chunks >= 1
    assert _chunk_count(other_scan_id) == other_chunks


def test_older_scan_finishing_late_keeps_newer_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    repository_id = _create_repository()
    older_scan_id = _create_scan(repository_id, EARLIER)
    newer_scan_id = _create_scan(repository_id, NOW)

    _run_scan(newer_scan_id, monkeypatch)
    newer_chunks = _chunk_count(newer_scan_id)
    _run_scan(older_scan_id, monkeypatch)

    assert newer_chunks >= 1
    assert _chunk_count(newer_scan_id) == newer_chunks
