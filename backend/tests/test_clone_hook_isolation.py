from __future__ import annotations

import stat
import subprocess
from pathlib import Path

import pytest

from app.ingestion.clone import clone_repo

CLONE_TIMEOUT_SECONDS = 60
CLONE_MAX_MB = 100


def _git(args: list[str], cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _make_source_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    (path / "Dockerfile").write_text("FROM alpine:3.19\n", encoding="utf-8")
    _git(["init", "--quiet", "--initial-branch=main"], cwd=path)
    _git(["config", "user.email", "test@local.dev"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)
    _git(["add", "."], cwd=path)
    _git(["commit", "--quiet", "-m", "initial"], cwd=path)
    return path.as_uri()


def _make_hook_template(template_dir: Path, sentinel: Path) -> None:
    hooks_dir = template_dir / "hooks"
    hooks_dir.mkdir(parents=True)
    hook = hooks_dir / "post-checkout"
    hook.write_text(f'#!/bin/sh\ntouch "{sentinel.as_posix()}"\n', encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


@pytest.fixture
def malicious_template(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[str, Path]:
    sentinel = tmp_path / "HOOK_EXECUTED"
    template_dir = tmp_path / "template"
    _make_hook_template(template_dir, sentinel)
    monkeypatch.setenv("GIT_TEMPLATE_DIR", str(template_dir))
    source_url = _make_source_repo(tmp_path / "source")
    return source_url, sentinel


def test_hook_fixture_is_capable_of_executing(malicious_template: tuple[str, Path], tmp_path: Path) -> None:
    source_url, sentinel = malicious_template
    dest = tmp_path / "control"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-checkout", "--depth", "1", "--", source_url, str(dest)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(dest), "checkout", "--quiet", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    if not sentinel.exists():
        pytest.skip("git hooks do not execute in this environment; the isolation test below is vacuous")


def test_clone_repo_does_not_execute_repository_hooks(malicious_template: tuple[str, Path], tmp_path: Path) -> None:
    source_url, sentinel = malicious_template
    dest = tmp_path / "scanned"

    clone_repo(source_url, str(dest), CLONE_TIMEOUT_SECONDS, CLONE_MAX_MB)

    assert not sentinel.exists(), "a git hook executed on the host during clone_repo"
    assert (dest / "Dockerfile").is_file()
    assert not (dest / ".git").exists()
