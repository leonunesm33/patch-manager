from pydantic import BaseModel


class ToggleSetting(BaseModel):
    label: str
    description: str
    enabled: bool


class LinuxGroupExecutionPolicy(BaseModel):
    group_name: str
    linux_agent_mode: str
    uses_default: bool


class ExecutionModeSetting(BaseModel):
    linux_agent_mode: str
    linux_group_modes: list[LinuxGroupExecutionPolicy] = []


class SettingsResponse(BaseModel):
    policy: list[ToggleSetting]
    notifications: list[ToggleSetting]
    execution: ExecutionModeSetting
