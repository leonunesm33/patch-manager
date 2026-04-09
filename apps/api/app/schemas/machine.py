from pydantic import BaseModel


class Machine(BaseModel):
    id: str
    name: str
    ip: str
    platform: str
    group: str
    status: str
    pending_patches: int
    last_check_in: str
    risk: str
