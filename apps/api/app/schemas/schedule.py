from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


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
    recurrence_weekday: int | None = None
    recurrence_ordinal: int | None = None
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
    recurrence_weekday: int | None = None
    recurrence_ordinal: int | None = None
    reboot_policy: str = "if-needed"
    is_active: bool = True

    @model_validator(mode="after")
    def _validate_monthly_weekday(self) -> "ScheduleCreate":
        if self.recurrence.strip().lower() != "monthly_weekday":
            return self
        if self.recurrence_weekday is None or self.recurrence_ordinal is None:
            raise ValueError(
                "recurrence_weekday and recurrence_ordinal are required when recurrence is 'monthly_weekday'"
            )
        if not (0 <= self.recurrence_weekday <= 6):
            raise ValueError("recurrence_weekday must be between 0 (Monday) and 6 (Sunday)")
        if self.recurrence_ordinal not in {1, 2, 3, 4, -1}:
            raise ValueError("recurrence_ordinal must be 1, 2, 3, 4, or -1 (last occurrence)")
        return self


class ScheduleToggle(BaseModel):
    is_active: bool
