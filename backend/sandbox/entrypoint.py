from __future__ import annotations

import json

from analysis.docker import inspect_files

REPO_PATH = "/repo"


def main() -> None:
    findings = inspect_files(REPO_PATH)
    payload = [
        {
            "rule_id": f.rule_id,
            "severity": f.severity,
            "file": f.file,
            "line": f.line,
            "message": f.message,
            "remediation": f.remediation,
        }
        for f in findings
    ]
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
