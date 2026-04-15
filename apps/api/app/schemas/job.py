from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PatchJobItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    schedule_name: str
    machine_name: str
    patch_id: str
    platform: str
    severity: str
    status: str
    claimed_by_agent: str | None = None
    claimed_at: datetime | None = None
    failure_reason: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
