from pydantic import BaseModel


class ReportItem(BaseModel):
    date: str
    schedule: str
    machine: str
    patch: str
    platform: str
    severity: str
    category: str = "unknown"
    result: str
    duration: str
