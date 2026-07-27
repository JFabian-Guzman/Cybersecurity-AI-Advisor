from __future__ import annotations

import os
import os.path
import re
from dataclasses import dataclass, field

_K8S_WORKLOAD_KINDS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob"}
_KIND_PATTERN = re.compile(r"^kind:\s*(\S+)", re.MULTILINE)
_CONTENT_SNIFF_BYTES = 8192


def _content_suggests_kubernetes(full_path: str) -> bool:
    try:
        with open(full_path, encoding="utf-8", errors="replace") as fh:
            head = fh.read(_CONTENT_SNIFF_BYTES)
    except OSError:
        return False

    match = _KIND_PATTERN.search(head)
    return match is not None and match.group(1) in _K8S_WORKLOAD_KINDS


def classify_file(path: str) -> str:
    name = os.path.basename(path)
    ext = os.path.splitext(name)[1].lower()
    parts = path.replace("\\", "/").split("/")

    if name == "Dockerfile" or ext == ".dockerfile":
        return "docker"
    if name == "docker-compose.yml" or name == "docker-compose.yaml":
        return "docker"

    if ext in (".tf", ".tfvars"):
        return "terraform"

    if ext in (".yaml", ".yml"):
        # First check if the file is in a directory that suggests Kubernetes manifests
        for part in parts[:-1]:
            if part in ("k8s", "kubernetes", "manifests"):
                return "kubernetes"
        return "config"

    if ext == ".py":
        return "python"
    if ext in (".js", ".ts", ".jsx", ".tsx"):
        return "javascript"
    if ext in (".json", ".toml", ".ini", ".cfg", ".conf"):
        return "config"

    lower_name = name.lower()
    if "secret" in lower_name or "credential" in lower_name or lower_name.startswith(".env"):
        return "secret"

    if ext in (".sh", ".bash", ".zsh"):
        return "script"
    if ext in (".md", ".rst", ".txt"):
        return "documentation"

    return "unknown"


@dataclass
class FileEntry:
    path: str
    category: str


@dataclass
class RepoManifest:
    project_types: list[str] = field(default_factory=list)
    files: list[FileEntry] = field(default_factory=list)


def _detect_project_types(files: list[FileEntry]) -> list[str]:
    types: list[str] = []
    seen = set()

    categories = {f.category for f in files}
    names = {os.path.basename(f.path) for f in files}
    paths = {f.path.replace("\\", "/") for f in files}

    if "docker" in categories:
        types.append("docker")
        seen.add("docker")

    if "terraform" in categories:
        types.append("terraform")
        seen.add("terraform")

    if "kubernetes" in categories:
        types.append("kubernetes")
        seen.add("kubernetes")

    if "python" in categories:
        types.append("python")
        seen.add("python")

    if "javascript" in categories:
        types.append("node")
        seen.add("node")

    if "secret" in categories:
        types.append("secret")

    if any(p.startswith(".github/workflows/") for p in paths):
        types.append("ci")

    if "pyproject.toml" in names or "requirements.txt" in names or "setup.py" in names:
        if "python" not in seen:
            types.append("python")
            seen.add("python")

    if "package.json" in names:
        if "node" not in seen:
            types.append("node")
            seen.add("node")

    return types


def inspect_repo(repo_path: str) -> RepoManifest:
    if not os.path.isdir(repo_path):
        return RepoManifest()

    files: list[FileEntry] = []
    for dirpath, _dirnames, filenames in os.walk(repo_path):
        for f in filenames:
            full_path = os.path.join(dirpath, f)
            relative_path = os.path.relpath(full_path, repo_path)
            relative_path = relative_path.replace("\\", "/")

            category = classify_file(relative_path)
            ext = os.path.splitext(f)[1].lower()
            # Double check for Kubernetes manifests in case the file is not in a directory that suggests Kubernetes
            if category == "config" and ext in (".yaml", ".yml") and _content_suggests_kubernetes(full_path):
                category = "kubernetes"

            files.append(FileEntry(path=relative_path, category=category))

    files.sort(key=lambda x: x.path)
    project_types = _detect_project_types(files)

    return RepoManifest(project_types=project_types, files=files)
