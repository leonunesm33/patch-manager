from datetime import date
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PatchAffectedMachine(BaseModel):
    id: str
    name: str
    ip: str
    platform: str
    environment: str
    group: str
    status: str


class PatchApproval(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target: str
    severity: str
    category: str = "security"
    machines: int
    affected_machines: list[PatchAffectedMachine] = Field(default_factory=list)
    release_date: date
    approval_status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class PatchCreate(BaseModel):
    id: str
    target: str
    severity: str
    category: str = "security"
    machines: int
    release_date: date
