from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentHeartbeatRequest(BaseModel):
    agent_id: str
    platform: str
    hostname: str


class AgentCheckInRequest(BaseModel):
    agent_id: str
    platform: str
    hostname: str
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    execution_mode: str


class AgentInventoryRequest(BaseModel):
    agent_id: str
    platform: str
    hostname: str
    primary_ip: str
    package_manager: str
    installed_packages: int
    upgradable_packages: int
    reboot_required: bool
    installed_update_count: int | None = None
    pending_update_summary: str | None = None
    windows_update_source: str | None = None
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    execution_mode: str


class AgentJobClaimRequest(BaseModel):
    agent_id: str
    platform: str


class AgentCommandPollRequest(BaseModel):
    agent_id: str
    platform: str


class AgentJobResultRequest(BaseModel):
    agent_id: str
    result: str
    execution_mode: str | None = None
    reboot_required: bool | None = None
    reboot_scheduled: bool | None = None
    reboot_message: str | None = None
    error_message: str | None = None


class AgentCommandResultRequest(BaseModel):
    agent_id: str
    result: str
    message: str | None = None


class AgentJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    schedule_name: str
    machine_id: str
    machine_name: str
    patch_id: str
    platform: str
    severity: str
    execution_mode: str
    real_apply_enabled: bool = False
    allow_security_only: bool = False
    allowed_package_patterns: list[str] = []
    apt_apply_timeout_seconds: int = 900
    windows_scan_apply_enabled: bool = False
    windows_download_install_enabled: bool = False
    windows_command_timeout_seconds: int = 60
    reboot_policy: str = "manual"
    reboot_grace_minutes: int = 60
    status: str
    claimed_by_agent: str | None = None
    claimed_at: datetime | None = None


class AgentCommandResponse(BaseModel):
    id: str
    command_type: str
    target_agent_id: str
    payload: dict[str, str | int | bool | None] = {}
    created_at: datetime


class AgentCommandHistoryItem(BaseModel):
    id: str
    agent_id: str
    command_type: str
    status: str
    requested_by: str
    message: str | None = None
    created_at: datetime
    claimed_at: datetime | None = None
    finished_at: datetime | None = None


class AgentInventorySnapshotItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    platform: str
    hostname: str
    primary_ip: str
    package_manager: str
    installed_packages: int
    upgradable_packages: int
    reboot_required: bool
    installed_update_count: int | None = None
    pending_update_summary: str | None = None
    windows_update_source: str | None = None
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    execution_mode: str
    updated_at: datetime


class ConnectedAgentResponse(BaseModel):
    agent_id: str
    platform: str
    hostname: str
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    execution_mode: str | None = None
    primary_ip: str | None = None
    package_manager: str | None = None
    installed_packages: int | None = None
    upgradable_packages: int | None = None
    reboot_required: bool | None = None
    installed_update_count: int | None = None
    pending_update_summary: str | None = None
    windows_update_source: str | None = None
    last_seen_at: datetime


class AgentEnrollmentRequest(BaseModel):
    agent_id: str
    platform: str
    hostname: str
    primary_ip: str
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str


class AgentEnrollmentStatusResponse(BaseModel):
    status: str
    agent_id: str
    agent_key: str | None = None
    poll_interval_seconds: int = 15


class PendingAgentEnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    platform: str
    hostname: str
    primary_ip: str
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    status: str
    requested_at: datetime
    approved_at: datetime | None = None


class RejectedAgentEnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    platform: str
    hostname: str
    primary_ip: str
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    status: str
    requested_at: datetime
    approved_at: datetime | None = None


class RevokedAgentResponse(BaseModel):
    agent_id: str
    platform: str
    hostname: str | None = None
    primary_ip: str | None = None
    os_name: str | None = None
    os_version: str | None = None
    kernel_version: str | None = None
    agent_version: str | None = None
    status: str = "revoked"
    last_known_at: datetime | None = None


class StoppedAgentResponse(BaseModel):
    agent_id: str
    platform: str
    hostname: str | None = None
    primary_ip: str | None = None
    os_name: str | None = None
    os_version: str | None = None
    kernel_version: str | None = None
    agent_version: str | None = None
    execution_mode: str | None = None
    package_manager: str | None = None
    installed_packages: int | None = None
    upgradable_packages: int | None = None
    reboot_required: bool | None = None
    installed_update_count: int | None = None
    pending_update_summary: str | None = None
    windows_update_source: str | None = None
    status: str = "stopped"
    last_seen_at: datetime | None = None
