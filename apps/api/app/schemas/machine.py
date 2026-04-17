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
    post_patch_state: str | None = None
    post_patch_message: str | None = None
    last_apply_at: datetime | None = None
    reboot_scheduled_at: datetime | None = None


class MachineCreate(BaseModel):
    name: str
    ip: str
    platform: str
    group: str
    status: str = "online"
    pending_patches: int = 0
    risk: str = "important"
