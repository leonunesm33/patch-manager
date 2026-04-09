export type DashboardSummary = {
  monitored_machines: number;
  pending_patches: number;
  compliance_rate: number;
  failed_jobs: number;
};

export type ActivityItem = {
  title: string;
  detail: string;
  status: "ok" | "warn" | "error";
};

export type PatchVolumeItem = {
  label: string;
  windows: number;
  linux: number;
};

export type PlatformDistribution = {
  windows_servers: number;
  windows_workstations: number;
  linux_servers: number;
};

export type DashboardResponse = {
  summary: DashboardSummary;
  activity: ActivityItem[];
  patch_volume: PatchVolumeItem[];
  platform_distribution: PlatformDistribution;
};
