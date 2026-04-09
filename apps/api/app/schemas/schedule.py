from pydantic import BaseModel, ConfigDict


class ScheduleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    scope: str
    cron_label: str
    reboot_policy: str


class ScheduleCreate(BaseModel):
    name: str
    scope: str
    cron_label: str
    reboot_policy: str
