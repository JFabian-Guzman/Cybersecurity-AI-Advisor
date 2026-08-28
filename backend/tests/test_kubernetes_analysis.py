from __future__ import annotations

from pathlib import Path

from app.analysis.k8s import inspect_files

_BASE_DEPLOYMENT = """\
apiVersion: apps/v1
kind: Deployment
metadata:
  name: app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: app
  template:
    metadata:
      labels:
        app: app
    spec:
      containers:
        - name: app
          image: app:1.0.0
          securityContext:
{security_context}
          resources:
{resources}
"""

_COMPLIANT_SECURITY_CONTEXT = """\
            privileged: false
            allowPrivilegeEscalation: false
            runAsNonRoot: true
"""

_COMPLIANT_RESOURCES = """\
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "250m"
              memory: "256Mi"
"""

_SERVICE_MANIFEST = """\
apiVersion: v1
kind: Service
metadata:
  name: app
spec:
  selector:
    app: app
  ports:
    - port: 80
      targetPort: 8080
"""


def _write_manifest(tmp_path: Path, content: str, name: str = "deployment.yaml") -> str:
    (tmp_path / name).write_text(content)
    return str(tmp_path)


def _deployment(security_context: str = _COMPLIANT_SECURITY_CONTEXT, resources: str = _COMPLIANT_RESOURCES) -> str:
    return _BASE_DEPLOYMENT.format(security_context=security_context, resources=resources)


def test_inspect_files_empty_path() -> None:
    assert inspect_files("/tmp/nonexistent-path-12345") == []


def test_inspect_files_ignores_non_manifest_files(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("kind: Deployment\n")
    repo = _write_manifest(tmp_path, _deployment())

    findings = inspect_files(repo)

    assert findings == []


def test_inspect_files_ignores_non_workload_kind(tmp_path: Path) -> None:
    repo = _write_manifest(tmp_path, _SERVICE_MANIFEST, name="service.yaml")
    findings = inspect_files(repo)
    assert findings == []


def test_check_privileged_flags_true(tmp_path: Path) -> None:
    security_context = (
        "            privileged: true\n"
        "            allowPrivilegeEscalation: false\n"
        "            runAsNonRoot: true\n"
    )
    repo = _write_manifest(tmp_path, _deployment(security_context=security_context))
    findings = inspect_files(repo)
    assert any(f.rule_id == "K8S001" for f in findings)


def test_check_privileged_ignores_false(tmp_path: Path) -> None:
    repo = _write_manifest(tmp_path, _deployment())
    findings = inspect_files(repo)
    assert not any(f.rule_id == "K8S001" for f in findings)


def test_check_host_namespaces_flags_hostnetwork(tmp_path: Path) -> None:
    content = _deployment().replace(
        "    spec:\n      containers:",
        "    spec:\n      hostNetwork: true\n      containers:",
    )
    repo = _write_manifest(tmp_path, content)
    findings = inspect_files(repo)
    assert any(f.rule_id == "K8S002" for f in findings)


def test_check_host_namespaces_ignores_when_absent(tmp_path: Path) -> None:
    repo = _write_manifest(tmp_path, _deployment())
    findings = inspect_files(repo)
    assert not any(f.rule_id == "K8S002" for f in findings)


def test_check_missing_resource_limits_flags_missing(tmp_path: Path) -> None:
    content = _BASE_DEPLOYMENT.format(security_context=_COMPLIANT_SECURITY_CONTEXT, resources="            {}\n")
    repo = _write_manifest(tmp_path, content)
    findings = inspect_files(repo)
    assert any(f.rule_id == "K8S003" for f in findings)


def test_check_missing_resource_limits_ignores_when_present(tmp_path: Path) -> None:
    repo = _write_manifest(tmp_path, _deployment())
    findings = inspect_files(repo)
    assert not any(f.rule_id == "K8S003" for f in findings)


def test_check_privilege_escalation_flags_missing(tmp_path: Path) -> None:
    security_context = "            privileged: false\n            runAsNonRoot: true\n"
    repo = _write_manifest(tmp_path, _deployment(security_context=security_context))
    findings = inspect_files(repo)
    assert any(f.rule_id == "K8S004" for f in findings)


def test_check_privilege_escalation_ignores_explicit_false(tmp_path: Path) -> None:
    repo = _write_manifest(tmp_path, _deployment())
    findings = inspect_files(repo)
    assert not any(f.rule_id == "K8S004" for f in findings)


def test_check_run_as_non_root_flags_missing(tmp_path: Path) -> None:
    security_context = "            privileged: false\n            allowPrivilegeEscalation: false\n"
    repo = _write_manifest(tmp_path, _deployment(security_context=security_context))
    findings = inspect_files(repo)
    assert any(f.rule_id == "K8S005" for f in findings)


def test_check_run_as_non_root_ignores_explicit_true(tmp_path: Path) -> None:
    repo = _write_manifest(tmp_path, _deployment())
    findings = inspect_files(repo)
    assert not any(f.rule_id == "K8S005" for f in findings)
