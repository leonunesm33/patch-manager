export type ToggleSetting = {
  label: string;
  description: string;
  enabled: boolean;
};

export type ExecutionSettings = {
  linux_agent_mode: "dry-run" | "apply";
  linux_group_modes: LinuxGroupExecutionPolicy[];
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
  last_seen_at: string;
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
};
