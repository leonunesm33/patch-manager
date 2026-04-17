export type Machine = {
  id: string;
  name: string;
  ip: string;
  platform: string;
  group: string;
  status: "online" | "warning" | "offline";
  pending_patches: number;
  last_check_in: string;
  risk: "critical" | "important" | "optional";
  post_patch_state: string | null;
  post_patch_message: string | null;
  last_apply_at: string | null;
  reboot_scheduled_at: string | null;
};

export type MachineJobSummary = {
  id: string;
  schedule_name: string;
  patch_id: string;
  platform: string;
  severity: string;
  status: string;
  claimed_by_agent: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type MachineExecutionSummary = {
  id: string;
  schedule_name: string;
  patch_id: string;
  platform: string;
  severity: string;
  result: string;
  duration_seconds: number;
  executed_at: string;
};

export type MachineCommandSummary = {
  id: string;
  command_type: string;
  status: string;
  requested_by: string;
  message: string | null;
  created_at: string;
  finished_at: string | null;
};

export type MachineOperationalDetails = {
  machine: Machine;
  agent_id: string | null;
  inventory: import("@/features/agents/types").AgentInventoryDetail | null;
  recent_jobs: MachineJobSummary[];
  recent_executions: MachineExecutionSummary[];
  recent_commands: MachineCommandSummary[];
};

export type MachineCreate = {
  name: string;
  ip: string;
  platform: string;
  group: string;
  status: "online" | "warning" | "offline";
  pending_patches: number;
  risk: "critical" | "important" | "optional";
};
