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
    real_apply_enabled: bool = False
    allow_security_only: bool = False
    allowed_package_patterns: list[str] = []
    apt_apply_timeout_seconds: int = 900
    reboot_policy: str = "manual"
    reboot_grace_minutes: int = 60
    real_apply_last_enabled_by: str | None = None
    real_apply_last_enabled_at: str | None = None
    windows_scan_apply_enabled: bool = False
    windows_download_install_enabled: bool = False
    windows_command_timeout_seconds: int = 60
    windows_reboot_policy: str = "manual"
    windows_reboot_grace_minutes: int = 60


class BootstrapSetting(BaseModel):
    agent_bootstrap_token: str
    agent_install_server_url: str
    agent_bootstrap_token_rotated_at: str | None = None
    agent_bootstrap_token_expires_at: str | None = None
    agent_bootstrap_token_is_expired: bool = False


class OperationalEvent(BaseModel):
    event_type: str
    severity: str
    actor: str
    summary: str
    occurred_at: str


class SettingsResponse(BaseModel):
    policy: list[ToggleSetting]
    notifications: list[ToggleSetting]
    execution: ExecutionModeSetting
    bootstrap: BootstrapSetting
    events: list[OperationalEvent] = []
