from datetime import date
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PatchApproval(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target: str
    severity: str
    machines: int
    release_date: date
    approval_status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class PatchCreate(BaseModel):
    id: str
    target: str
    severity: str
    machines: int
    release_date: date
