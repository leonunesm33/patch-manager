export type ToggleSetting = {
  label: string;
  description: string;
  enabled: boolean;
};

export type ExecutionSettings = {
  linux_agent_mode: "dry-run" | "apply";
  linux_group_modes: LinuxGroupExecutionPolicy[];
  real_apply_enabled: boolean;
  allow_security_only: boolean;
  allowed_package_patterns: string[];
  apt_apply_timeout_seconds: number;
  reboot_policy: "manual" | "notify" | "maintenance-window";
  reboot_grace_minutes: number;
  real_apply_last_enabled_by: string | null;
  real_apply_last_enabled_at: string | null;
  windows_scan_apply_enabled: boolean;
  windows_download_install_enabled: boolean;
  windows_command_timeout_seconds: number;
  windows_reboot_policy: "manual" | "notify" | "maintenance-window";
  windows_reboot_grace_minutes: number;
};

export type BootstrapSettings = {
  agent_bootstrap_token: string;
  agent_install_server_url: string;
};

export type OperationalEvent = {
  event_type: string;
  severity: "info" | "warn" | "error";
  actor: string;
  summary: string;
  occurred_at: string;
};

export type LinuxGroupExecutionPolicy = {
  group_name: string;
  linux_agent_mode: "dry-run" | "apply";
  uses_default: boolean;
};

export type PatchCycleRunResponse = {
  schedules_matched: number;
  approved_patches: number;
  jobs_enqueued: number;
  jobs_processed: number;
  executions_created: number;
  failed_executions: number;
};

export type PatchJobProcessResponse = {
  pending_jobs_before: number;
  jobs_started: number;
  jobs_processed: number;
  executions_created: number;
  failed_executions: number;
};

export type ConnectedAgent = {
  agent_id: string;
  platform: string;
  hostname: string;
  os_name: string;
  os_version: string;
  kernel_version: string;
  agent_version: string;
  execution_mode: string | null;
  primary_ip: string | null;
  package_manager: string | null;
  installed_packages: number | null;
  upgradable_packages: number | null;
  reboot_required: boolean | null;
  installed_update_count: number | null;
  pending_update_summary: string | null;
  windows_update_source: string | null;
  last_seen_at: string;
};

export type RevokedAgent = {
  agent_id: string;
  platform: string;
  hostname: string | null;
  primary_ip: string | null;
  os_name: string | null;
  os_version: string | null;
  kernel_version: string | null;
  agent_version: string | null;
  status: "revoked";
  last_known_at: string | null;
};

export type StoppedAgent = {
  agent_id: string;
  platform: string;
  hostname: string | null;
  primary_ip: string | null;
  os_name: string | null;
  os_version: string | null;
  kernel_version: string | null;
  agent_version: string | null;
  execution_mode: string | null;
  package_manager: string | null;
  installed_packages: number | null;
  upgradable_packages: number | null;
  reboot_required: boolean | null;
  installed_update_count: number | null;
  pending_update_summary: string | null;
  windows_update_source: string | null;
  status: "stopped";
  last_seen_at: string | null;
};

export type PendingAgentEnrollment = {
  agent_id: string;
  platform: string;
  hostname: string;
  primary_ip: string;
  os_name: string;
  os_version: string;
  kernel_version: string;
  agent_version: string;
  status: string;
  requested_at: string;
  approved_at: string | null;
};

export type RejectedAgentEnrollment = {
  agent_id: string;
  platform: string;
  hostname: string;
  primary_ip: string;
  os_name: string;
  os_version: string;
  kernel_version: string;
  agent_version: string;
  status: "rejected";
  requested_at: string;
  approved_at: string | null;
};

export type SchedulerStatusResponse = {
  running: boolean;
  enqueue_interval_seconds: number;
  worker_interval_seconds: number;
  next_enqueue_run_at: string | null;
  next_worker_run_at: string | null;
  last_enqueue_run_at: string | null;
  last_worker_run_at: string | null;
  last_enqueue_result: PatchCycleRunResponse | null;
  last_worker_result: PatchJobProcessResponse | null;
};

export type SettingsResponse = {
  policy: ToggleSetting[];
  notifications: ToggleSetting[];
  execution: ExecutionSettings;
  bootstrap: BootstrapSettings;
  events: OperationalEvent[];
};

export type AgentCommandHistoryItem = {
  id: string;
  agent_id: string;
  command_type: string;
  status: "pending" | "running" | "completed" | "failed";
  requested_by: string;
  message: string | null;
  created_at: string;
  claimed_at: string | null;
  finished_at: string | null;
};
