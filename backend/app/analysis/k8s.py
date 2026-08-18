from __future__ import annotations

import os
import os.path
from typing import Any

import yaml

from .common import Finding


_WORKLOAD_KINDS = {"Pod", "Deployment", "StatefulSet", "DaemonSet", "ReplicaSet", "Job", "CronJob"}
_CONTAINER_FIELDS = ("containers", "initContainers")
_HOST_NAMESPACE_FIELDS = ("hostNetwork", "hostPID", "hostIPC")


class _LineDict(dict):
    __line__: int
    __key_lines__: dict[str, int]


class _LineLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.SafeLoader, node: yaml.MappingNode) -> _LineDict:
    mapping = _LineDict()
    key_lines: dict[str, int] = {}

    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        mapping[key] = loader.construct_object(value_node)
        key_lines[key] = key_node.start_mark.line + 1

    mapping.__line__ = node.start_mark.line + 1
    mapping.__key_lines__ = key_lines
    return mapping


_LineLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def _mapping_line(mapping: dict[str, Any]) -> int | None:
    return getattr(mapping, "__line__", None)


def _key_line(mapping: dict[str, Any], key: str) -> int | None:
    key_lines: dict[str, int] = getattr(mapping, "__key_lines__", {})
    return key_lines.get(key)


def _is_manifest(name: str) -> bool:
    return name.lower().endswith((".yaml", ".yml"))


def _load_documents(text: str) -> list[dict[str, Any]]:
    try:
        return [doc for doc in yaml.load_all(text, Loader=_LineLoader) if isinstance(doc, dict)]
    except yaml.YAMLError:
        return []


def _pod_spec(document: dict[str, Any]) -> dict[str, Any] | None:
    kind = document.get("kind")
    if kind not in _WORKLOAD_KINDS:
        return None

    if kind == "Pod":
        spec = document.get("spec")
    elif kind == "CronJob":
        spec = document.get("spec", {}).get("jobTemplate", {}).get("spec", {}).get("template", {}).get("spec")
    else:
        spec = document.get("spec", {}).get("template", {}).get("spec")

    return spec if isinstance(spec, dict) else None


def _iter_containers(pod_spec: dict[str, Any]) -> list[dict[str, Any]]:
    containers: list[dict[str, Any]] = []
    for field in _CONTAINER_FIELDS:
        value = pod_spec.get(field)
        if isinstance(value, list):
            containers.extend(c for c in value if isinstance(c, dict))
    return containers


def _security_context(container: dict[str, Any]) -> dict[str, Any] | None:
    security_context = container.get("securityContext")
    return security_context if isinstance(security_context, dict) else None


def _check_privileged(path: str, pod_spec: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for container in _iter_containers(pod_spec):
        security_context = _security_context(container)
        if security_context is None or security_context.get("privileged") is not True:
            continue

        name = container.get("name", "unknown")
        findings.append(
            Finding(
                rule_id="K8S001",
                severity="HIGH",
                file=path,
                line=_key_line(security_context, "privileged"),
                message=(
                    f"Container '{name}' runs with securityContext.privileged: true, granting it "
                    "full access to the host's devices and kernel capabilities."
                ),
                remediation=(
                    "Remove privileged: true (or set it to false) and grant only the specific "
                    "Linux capabilities the workload actually needs."
                ),
            )
        )

    return findings


def _check_host_namespaces(path: str, pod_spec: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for field in _HOST_NAMESPACE_FIELDS:
        if pod_spec.get(field) is not True:
            continue

        findings.append(
            Finding(
                rule_id="K8S002",
                severity="HIGH",
                file=path,
                line=_key_line(pod_spec, field),
                message=(
                    f"Pod uses {field}: true, giving it direct access to the host's "
                    f"{field.removeprefix('host').lower()} namespace."
                ),
                remediation=(
                    "Remove hostNetwork/hostPID/hostIPC unless the workload has a specific, "
                    "reviewed need for host namespace access."
                ),
            )
        )

    return findings


def _has_cpu_and_memory(section: Any) -> bool:
    return isinstance(section, dict) and "cpu" in section and "memory" in section


def _check_missing_resource_limits(path: str, pod_spec: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for container in _iter_containers(pod_spec):
        resources = container.get("resources")
        requests_ok = _has_cpu_and_memory(resources.get("requests")) if isinstance(resources, dict) else False
        limits_ok = _has_cpu_and_memory(resources.get("limits")) if isinstance(resources, dict) else False
        if requests_ok and limits_ok:
            continue

        name = container.get("name", "unknown")
        findings.append(
            Finding(
                rule_id="K8S003",
                severity="MEDIUM",
                file=path,
                line=_mapping_line(container),
                message=(
                    f"Container '{name}' has no resources.requests/limits for cpu or memory — "
                    "without them it can starve or be starved by other workloads on the same node."
                ),
                remediation="Set explicit resources.requests and resources.limits for cpu and memory.",
            )
        )

    return findings


def _check_privilege_escalation(path: str, pod_spec: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for container in _iter_containers(pod_spec):
        security_context = _security_context(container)
        if security_context is not None and security_context.get("allowPrivilegeEscalation") is False:
            continue

        name = container.get("name", "unknown")
        findings.append(
            Finding(
                rule_id="K8S004",
                severity="HIGH",
                file=path,
                line=_mapping_line(container),
                message=(
                    f"Container '{name}' does not explicitly set "
                    "securityContext.allowPrivilegeEscalation: false, so a process inside it may "
                    "gain more privileges than its parent."
                ),
                remediation="Explicitly set allowPrivilegeEscalation: false.",
            )
        )

    return findings


def _check_run_as_non_root(path: str, pod_spec: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []

    for container in _iter_containers(pod_spec):
        security_context = _security_context(container)
        if security_context is not None and security_context.get("runAsNonRoot") is True:
            continue

        name = container.get("name", "unknown")
        findings.append(
            Finding(
                rule_id="K8S005",
                severity="MEDIUM",
                file=path,
                line=_mapping_line(container),
                message=(
                    f"Container '{name}' does not set securityContext.runAsNonRoot: true, so it "
                    "may run as root inside the container if the image doesn't drop privileges."
                ),
                remediation="Set runAsNonRoot: true (and a non-zero runAsUser) to enforce non-root execution.",
            )
        )

    return findings


def _analyze_manifest(path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []

    for document in _load_documents(text):
        pod_spec = _pod_spec(document)
        if pod_spec is None:
            continue

        findings.extend(_check_privileged(path, pod_spec))
        findings.extend(_check_host_namespaces(path, pod_spec))
        findings.extend(_check_missing_resource_limits(path, pod_spec))
        findings.extend(_check_privilege_escalation(path, pod_spec))
        findings.extend(_check_run_as_non_root(path, pod_spec))

    return findings


def inspect_files(repo_path: str) -> list[Finding]:
    if not os.path.isdir(repo_path):
        return []

    manifest_paths: list[str] = []
    for dirpath, _dirnames, filenames in os.walk(repo_path):
        for f in filenames:
            if not _is_manifest(f):
                continue
            full_path = os.path.join(dirpath, f)
            relative_path = os.path.relpath(full_path, repo_path).replace("\\", "/")
            manifest_paths.append(relative_path)

    findings: list[Finding] = []
    for relative_path in sorted(manifest_paths):
        full_path = os.path.join(repo_path, relative_path)
        try:
            with open(full_path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue

        findings.extend(_analyze_manifest(relative_path, text))

    return findings
