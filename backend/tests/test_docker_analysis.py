from __future__ import annotations

from pathlib import Path

from analysis.docker import inspect_files


def _write_dockerfile(tmp_path: Path, content: str, name: str = "Dockerfile") -> str:
    (tmp_path / name).write_text(content)
    return str(tmp_path)


def test_inspect_files_empty_path() -> None:
    assert inspect_files("/tmp/nonexistent-path-12345") == []


def test_inspect_files_ignores_non_dockerfiles(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("FROM python:latest\n")
    repo = _write_dockerfile(tmp_path, "FROM python:3.14-slim\nUSER 1000\n")

    findings = inspect_files(repo)

    assert findings == []


def test_check_tags_ignores_digest_pinned_image(tmp_path: Path) -> None:
    repo = _write_dockerfile(tmp_path, "FROM python@sha256:abcdef1234567890\nUSER 1000\n")
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF002" for f in findings)


def test_check_tags_ignores_reference_to_earlier_build_stage(tmp_path: Path) -> None:
    content = "FROM python:3.14-slim AS builder\nFROM builder\nUSER 1000\n"
    repo = _write_dockerfile(tmp_path, content)
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF002" for f in findings)


def test_check_tags_flags_untagged_image(tmp_path: Path) -> None:
    repo = _write_dockerfile(tmp_path, "FROM python\nUSER 1000\n")
    findings = inspect_files(repo)
    assert any(f.rule_id == "DF002" and f.line == 1 for f in findings)


def test_check_secrets_ignores_variable_reference(tmp_path: Path) -> None:
    content = "FROM python:3.14-slim\nENV PASSWORD=$SECRET_PASSWORD\nUSER 1000\n"
    repo = _write_dockerfile(tmp_path, content)
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF003" for f in findings)


def test_check_secrets_ignores_non_secret_keys(tmp_path: Path) -> None:
    content = "FROM python:3.14-slim\nENV APP_ENV=production\nUSER 1000\n"
    repo = _write_dockerfile(tmp_path, content)
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF003" for f in findings)


def test_check_remote_url_ignores_copy(tmp_path: Path) -> None:
    content = "FROM python:3.14-slim\nCOPY https://example.com/install.sh /tmp/install.sh\nUSER 1000\n"
    repo = _write_dockerfile(tmp_path, content)
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF004" for f in findings)


def test_check_version_pinning_ignores_pinned_packages(tmp_path: Path) -> None:
    content = (
        "FROM python:3.14-slim\n"
        "RUN apt-get update && apt-get install -y curl=7.88.1-10\n"
        "RUN pip install requests==2.31.0\n"
        "RUN npm install lodash@4.17.21\n"
        "USER 1000\n"
    )
    repo = _write_dockerfile(tmp_path, content)
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF005" for f in findings)


def test_check_user_ignores_dockerfile_with_user_directive(tmp_path: Path) -> None:
    repo = _write_dockerfile(tmp_path, "FROM python:3.14-slim\nUSER 1000\n")
    findings = inspect_files(repo)
    assert not any(f.rule_id == "DF001" for f in findings)
