from pydantic import BaseModel


class ToggleSetting(BaseModel):
    label: str
    description: str
    enabled: bool


class SettingsResponse(BaseModel):
    policy: list[ToggleSetting]
    notifications: list[ToggleSetting]
