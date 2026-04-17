from pydantic import BaseModel


class DashboardSummary(BaseModel):
    monitored_machines: int
    pending_patches: int
    compliance_rate: float
    failed_jobs: int
    reboot_pending_hosts: int
    reboot_scheduled_hosts: int
    pending_agent_commands: int
    windows_pending_updates: int


class ActivityItem(BaseModel):
    title: str
    detail: str
    status: str


class PatchVolumeItem(BaseModel):
    label: str
    windows: int
    linux: int


class PlatformDistribution(BaseModel):
    windows_servers: int
    windows_workstations: int
    linux_servers: int


class RebootPendingItem(BaseModel):
    agent_id: str
    hostname: str
    platform: str
    primary_ip: str | None = None
    post_patch_state: str | None = None
    post_patch_message: str | None = None
    reboot_scheduled_at: str | None = None
    last_seen_at: str


class PendingActionItem(BaseModel):
    title: str
    detail: str
    action_type: str
    severity: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    activity: list[ActivityItem]
    patch_volume: list[PatchVolumeItem]
    platform_distribution: PlatformDistribution
    reboot_pending: list[RebootPendingItem]
    pending_actions: list[PendingActionItem]
