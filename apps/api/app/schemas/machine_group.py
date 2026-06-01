from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MachineGroup(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str | None = None
    created_at: datetime | None = None


class MachineGroupCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
