from pydantic import BaseModel


class ReportItem(BaseModel):
    date: str
    machine: str
    patch: str
    platform: str
    severity: str
    result: str
    duration: str
