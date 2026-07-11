from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.classify import inspect_repo

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"

FIXTURE_REPOS = sorted(d for d in FIXTURES_DIR.iterdir() if d.is_dir() and d.name.startswith("repo-"))


@pytest.mark.parametrize("fixture_path", FIXTURE_REPOS, ids=lambda p: p.name)
def test_inspect_repo_returns_non_empty_manifest(fixture_path: Path) -> None:
    manifest = inspect_repo(str(fixture_path))
    assert len(manifest.files) > 0
    assert len(manifest.project_types) > 0


@pytest.mark.parametrize("fixture_path", FIXTURE_REPOS, ids=lambda p: p.name)
def test_inspect_repo_detects_docker(fixture_path: Path) -> None:
    manifest = inspect_repo(str(fixture_path))
    assert any(f.path == "Dockerfile" for f in manifest.files)
    assert "docker" in manifest.project_types


@pytest.mark.parametrize(
    "fixture_path, expected_files",
    [
        ("repo-root-user", {"Dockerfile", "expected-findings.yaml", "url.md"}),
        ("repo-latest-tag", {"Dockerfile", "expected-findings.yaml", "url.md"}),
        ("repo-hardcoded-secrets", {"Dockerfile", "expected-findings.yaml", "url.md"}),
        ("repo-add-remote-url", {"Dockerfile", "expected-findings.yaml", "url.md"}),
        ("repo-unpinned-packages", {"Dockerfile", "expected-findings.yaml", "url.md"}),
    ],
)
def test_inspect_repo_file_list(fixture_path: str, expected_files: set[str]) -> None:
    manifest = inspect_repo(str(FIXTURES_DIR / fixture_path))
    found = {f.path for f in manifest.files}
    assert found == expected_files


def test_inspect_repo_empty_path() -> None:
    manifest = inspect_repo("/tmp/nonexistent-path-12345")
    assert manifest.files == []
    assert manifest.project_types == []


def test_inspect_repo_classifies_dockerfile() -> None:
    manifest = inspect_repo(str(FIXTURES_DIR / "repo-root-user"))
    docker_files = [f for f in manifest.files if f.category == "docker"]
    assert any(f.path == "Dockerfile" for f in docker_files)
