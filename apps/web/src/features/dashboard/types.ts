export type DashboardSummary = {
  monitored_machines: number;
  pending_patches: number;
  compliance_rate: number;
  failed_jobs: number;
  reboot_pending_hosts: number;
  pending_agent_commands: number;
  windows_pending_updates: number;
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

export type RebootPendingItem = {
  agent_id: string;
  hostname: string;
  platform: string;
  primary_ip: string | null;
  last_seen_at: string;
};

export type PendingActionItem = {
  title: string;
  detail: string;
  action_type: string;
  severity: "info" | "warn" | "error";
};

export type DashboardResponse = {
  summary: DashboardSummary;
  activity: ActivityItem[];
  patch_volume: PatchVolumeItem[];
  platform_distribution: PlatformDistribution;
  reboot_pending: RebootPendingItem[];
  pending_actions: PendingActionItem[];
};
