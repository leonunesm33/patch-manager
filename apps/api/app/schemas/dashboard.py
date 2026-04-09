from pydantic import BaseModel


class DashboardSummary(BaseModel):
    monitored_machines: int
    pending_patches: int
    compliance_rate: float
    failed_jobs: int


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


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    activity: list[ActivityItem]
    patch_volume: list[PatchVolumeItem]
    platform_distribution: PlatformDistribution
