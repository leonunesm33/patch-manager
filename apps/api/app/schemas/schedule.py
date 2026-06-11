from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class ScheduleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    scope: str
    scope_type: str = "group"
    scope_value: str = ""
    cron_label: str
    install_date: date | None = None
    install_time: str = "02:00"
    reboot_date: date | None = None
    reboot_time: str | None = None
    recurrence: str = "weekly"
    reboot_policy: str
    is_active: bool = True


class ScheduleCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scope_type: str = "group"
    scope_value: str
    install_date: date | None = None
    install_time: str = "02:00"
    reboot_date: date | None = None
    reboot_time: str | None = None
    recurrence: str = "weekly"
    reboot_policy: str = "if-needed"
    is_active: bool = True


class ScheduleToggle(BaseModel):
    is_active: bool
