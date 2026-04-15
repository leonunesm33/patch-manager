from pydantic import BaseModel


class LinuxExecutionModeUpdate(BaseModel):
    linux_agent_mode: str
    machine_group: str | None = None
    real_apply_enabled: bool | None = None
    allow_security_only: bool | None = None
    allowed_package_patterns: list[str] | None = None
    apt_apply_timeout_seconds: int | None = None
    reboot_policy: str | None = None
    reboot_grace_minutes: int | None = None
    windows_scan_apply_enabled: bool | None = None
    windows_download_install_enabled: bool | None = None
    windows_command_timeout_seconds: int | None = None
    windows_reboot_policy: str | None = None
    windows_reboot_grace_minutes: int | None = None


class BootstrapTokenUpdate(BaseModel):
    agent_bootstrap_token: str
    agent_install_server_url: str | None = None
