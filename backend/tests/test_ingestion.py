from __future__ import annotations

from pathlib import Path

import pytest

from ingestion.classify import inspect_repo

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"
DOCKER_FIXTURES_DIR = FIXTURES_DIR / "Docker"

DOCKER_FIXTURE_REPOS = sorted(d for d in DOCKER_FIXTURES_DIR.iterdir() if d.is_dir() and d.name.startswith("repo-"))


@pytest.mark.parametrize("fixture_path", DOCKER_FIXTURE_REPOS, ids=lambda p: p.name)
def test_inspect_repo_returns_non_empty_manifest(fixture_path: Path) -> None:
    manifest = inspect_repo(str(fixture_path))
    assert len(manifest.files) > 0
    assert len(manifest.project_types) > 0


@pytest.mark.parametrize("fixture_path", DOCKER_FIXTURE_REPOS, ids=lambda p: p.name)
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
    manifest = inspect_repo(str(DOCKER_FIXTURES_DIR / fixture_path))
    found = {f.path for f in manifest.files}
    assert found == expected_files


def test_inspect_repo_empty_path() -> None:
    manifest = inspect_repo("/tmp/nonexistent-path-12345")
    assert manifest.files == []
    assert manifest.project_types == []


def test_inspect_repo_classifies_dockerfile() -> None:
    manifest = inspect_repo(str(DOCKER_FIXTURES_DIR / "repo-root-user"))
    docker_files = [f for f in manifest.files if f.category == "docker"]
    assert any(f.path == "Dockerfile" for f in docker_files)


def test_inspect_repo_detects_kubernetes_by_content_outside_conventional_folder() -> None:
    """fixtures/K8s/repo-privileged puts deployment.yaml directly in the repo root
    (not under a k8s/kubernetes/manifests folder), so this only passes once
    classify_file's path-only heuristic is backed by a content-based fallback."""
    manifest = inspect_repo(str(FIXTURES_DIR / "K8s" / "repo-privileged"))
    k8s_files = [f for f in manifest.files if f.category == "kubernetes"]
    assert any(f.path == "deployment.yaml" for f in k8s_files)
    assert "kubernetes" in manifest.project_types


def test_inspect_repo_kubernetes_folder_heuristic_still_works(tmp_path: Path) -> None:
    (tmp_path / "k8s").mkdir()
    (tmp_path / "k8s" / "kustomization.yaml").write_text("resources:\n  - deployment.yaml\n")

    manifest = inspect_repo(str(tmp_path))

    k8s_files = [f for f in manifest.files if f.category == "kubernetes"]
    assert any(f.path == "k8s/kustomization.yaml" for f in k8s_files)


def test_inspect_repo_ignores_unrelated_yaml(tmp_path: Path) -> None:
    (tmp_path / "config.yaml").write_text("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

    manifest = inspect_repo(str(tmp_path))

    found = {f.path: f.category for f in manifest.files}
    assert found["config.yaml"] == "config"
