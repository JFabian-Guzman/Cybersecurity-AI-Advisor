from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

class ReportFinding(BaseModel):
    total_findings: int
    severity_counts: dict[str, int]
    rule_counts: dict[str, int]
    category_counts: dict[str, int]


class ReportResponse(BaseModel):
    scan_id: uuid.UUID
    total_findings: int
    severity_counts: dict[str, int]
    rule_counts: dict[str, int]
    category_counts: dict[str, int]
    created_at: datetime

    model_config = {"from_attributes": True}
