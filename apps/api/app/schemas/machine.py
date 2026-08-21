from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.agent import AgentInventoryDetailResponse


class Machine(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    ip: str
    platform: str
    environment: str
    os_release: str | None = None
    group: str
    status: str
    pending_patches: int
    pending_security_critical_patches: int = 0
    last_check_in: datetime
    risk: str
    hardware_fingerprint: str | None = None
    identity_conflict_fingerprint: str | None = None
    identity_conflict_detected_at: datetime | None = None
    identity_conflict_auto_resolved_at: datetime | None = None
    identity_conflict_previous_fingerprint: str | None = None
    identity_conflict_oscillation_detected_at: datetime | None = None
    post_patch_state: str | None = None
    post_patch_message: str | None = None
    last_apply_at: datetime | None = None
    reboot_scheduled_at: datetime | None = None


class MachineCreate(BaseModel):
    name: str
    ip: str
    platform: str
    environment: str = "production"
    group: str
    status: str = "online"
    pending_patches: int = 0
    pending_security_critical_patches: int = 0
    risk: str = "important"


class MachineJobSummary(BaseModel):
    id: str
    schedule_name: str
    patch_id: str
    platform: str
    severity: str
    status: str
    claimed_by_agent: str | None = None
    error_message: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class MachineExecutionSummary(BaseModel):
    id: str
    schedule_name: str
    patch_id: str
    platform: str
    severity: str
    result: str
    duration_seconds: int
    executed_at: datetime


class AgentIdentityHistoryItem(BaseModel):
    id: str
    agent_id: str
    new_agent_id: str | None = None
    command_id: str | None = None
    event_type: str
    status: str
    platform: str | None = None
    hostname: str | None = None
    hardware_fingerprint: str | None = None
    previous_fingerprint: str | None = None
    actor: str
    reason: str | None = None
    message: str | None = None
    occurred_at: datetime


class MachineCommandSummary(BaseModel):
    id: str
    command_type: str
    status: str
    requested_by: str
    message: str | None = None
    created_at: datetime
    finished_at: datetime | None = None


class MachineOperationalDetails(BaseModel):
    machine: Machine
    agent_id: str | None = None
    inventory: AgentInventoryDetailResponse | None = None
    recent_jobs: list[MachineJobSummary] = []
    recent_executions: list[MachineExecutionSummary] = []
    recent_commands: list[MachineCommandSummary] = []
    identity_history: list[AgentIdentityHistoryItem] = []
