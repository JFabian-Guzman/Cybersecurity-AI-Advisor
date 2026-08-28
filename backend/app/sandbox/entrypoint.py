from __future__ import annotations

import json
import os
from collections.abc import Callable

from analysis.common import Finding
from analysis.docker import inspect_files as inspect_docker
from analysis.k8s import inspect_files as inspect_k8s

REPO_PATH = "/repo"

_ANALYZERS: dict[str, Callable[[str], list[Finding]]] = {
    "docker": inspect_docker,
    "kubernetes": inspect_k8s,
}


def _requested_categories() -> list[str]:
    raw = os.environ.get("ANALYZERS")
    if raw is None:
        return list(_ANALYZERS)
    # Delete any empty strings from the list of categories
    return [category for category in raw.split(",") if category]


def main() -> None:
    payload = []

    for category in _requested_categories():
        analyzer = _ANALYZERS.get(category)
        if analyzer is None:
            continue

        for f in analyzer(REPO_PATH):
            payload.append(
                {
                    "rule_id": f.rule_id,
                    "severity": f.severity,
                    "file": f.file,
                    "line": f.line,
                    "message": f.message,
                    "remediation": f.remediation,
                    "category": category,
                }
            )

    print(json.dumps(payload))


if __name__ == "__main__":
    main()
