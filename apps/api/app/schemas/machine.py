from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Machine(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    ip: str
    platform: str
    group: str
    status: str
    pending_patches: int
    last_check_in: datetime
    risk: str


class MachineCreate(BaseModel):
    name: str
    ip: str
    platform: str
    group: str
    status: str = "online"
    pending_patches: int = 0
    risk: str = "important"
