from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class FindingResponse(BaseModel):
    id: uuid.UUID
    scan_id: uuid.UUID
    rule_id: str
    severity: str
    category: str
    file_path: str
    line_number: int | None
    message: str
    remediation: str
    created_at: datetime

    model_config = {"from_attributes": True}
