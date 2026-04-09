from datetime import date

from pydantic import BaseModel, ConfigDict


class PatchApproval(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    target: str
    severity: str
    machines: int
    release_date: date
