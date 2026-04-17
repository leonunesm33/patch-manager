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
    group: str
    status: str
    pending_patches: int
    last_check_in: datetime
    risk: str
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
