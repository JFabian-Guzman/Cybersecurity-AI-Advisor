from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Finding:
    rule_id: str
    severity: str
    file: str
    line: int | None
    message: str
    remediation: str
