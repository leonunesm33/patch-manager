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
    os_name: str
    os_version: str
    kernel_version: str
    agent_version: str
    execution_mode: str


class AgentJobClaimRequest(BaseModel):
    agent_id: str
    platform: str


class AgentJobResultRequest(BaseModel):
    agent_id: str
    result: str
    error_message: str | None = None


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
    status: str
    claimed_by_agent: str | None = None
    claimed_at: datetime | None = None


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
    last_seen_at: datetime
