import { http } from "@/lib/http";
import type {
  BootstrapSettings,
  AgentCommandHistoryItem,
  ConnectedAgent,
  ExecutionSettings,
  PendingAgentEnrollment,
  RejectedAgentEnrollment,
  RevokedAgent,
  SchedulerStatusResponse,
  SettingsResponse,
  StoppedAgent,
} from "@/features/settings/types";

export function fetchSettings() {
  return http<SettingsResponse>("/settings");
}

export function fetchSchedulerStatus() {
  return http<SchedulerStatusResponse>("/agents/scheduler-status");
}

export function startScheduler() {
  return http<SchedulerStatusResponse>("/agents/scheduler/start", {
    method: "POST",
  });
}

export function stopScheduler() {
  return http<SchedulerStatusResponse>("/agents/scheduler/stop", {
    method: "POST",
  });
}

export function fetchConnectedAgents() {
  return http<ConnectedAgent[]>("/agents/connected");
}

export function fetchRevokedAgents() {
  return http<RevokedAgent[]>("/agents/revoked");
}

export function fetchStoppedAgents() {
  return http<StoppedAgent[]>("/agents/stopped");
}

export function fetchPendingEnrollments() {
  return http<PendingAgentEnrollment[]>("/agents/enrollments/pending");
}

export function fetchRejectedEnrollments() {
  return http<RejectedAgentEnrollment[]>("/agents/enrollments/rejected");
}

export function fetchRecentAgentCommands() {
  return http<AgentCommandHistoryItem[]>("/agents/commands/recent");
}

export function approvePendingEnrollment(agentId: string) {
  return http<PendingAgentEnrollment>(`/agents/enrollments/${agentId}/approve`, {
    method: "POST",
  });
}

export function rejectPendingEnrollment(agentId: string) {
  return http<PendingAgentEnrollment>(`/agents/enrollments/${agentId}/reject`, {
    method: "POST",
  });
}

export function reopenRejectedEnrollment(agentId: string) {
  return http<PendingAgentEnrollment>(`/agents/enrollments/${agentId}/reopen`, {
    method: "POST",
  });
}

export function revokeConnectedAgent(agentId: string) {
  return http<{ status: string }>(`/agents/connected/${agentId}/revoke`, {
    method: "POST",
  });
}

export function reintegrateConnectedAgent(agentId: string) {
  return http<PendingAgentEnrollment>(`/agents/connected/${agentId}/reintegrate`, {
    method: "POST",
  });
}

export function requeueRevokedAgent(agentId: string) {
  return http<PendingAgentEnrollment>(`/agents/revoked/${agentId}/requeue`, {
    method: "POST",
  });
}

export function requestConnectedAgentReboot(agentId: string) {
  return http<{ status: string }>(`/agents/connected/${agentId}/reboot`, {
    method: "POST",
  });
}

export function updateLinuxExecutionMode(
  linux_agent_mode: "dry-run" | "apply",
  machine_group?: string,
  options?: {
    real_apply_enabled?: boolean;
    allow_security_only?: boolean;
    allowed_package_patterns?: string[];
    apt_apply_timeout_seconds?: number;
    reboot_policy?: "manual" | "notify" | "maintenance-window";
    reboot_grace_minutes?: number;
    windows_scan_apply_enabled?: boolean;
    windows_download_install_enabled?: boolean;
    windows_command_timeout_seconds?: number;
    windows_reboot_policy?: "manual" | "notify" | "maintenance-window";
    windows_reboot_grace_minutes?: number;
  },
) {
  return http<ExecutionSettings>("/settings/execution-mode", {
    method: "PUT",
    body: JSON.stringify({ linux_agent_mode, machine_group, ...(options ?? {}) }),
  });
}

export function updateBootstrapToken(
  agent_bootstrap_token: string,
  agent_install_server_url?: string,
) {
  return http<BootstrapSettings>("/settings/bootstrap-token", {
    method: "PUT",
    body: JSON.stringify({ agent_bootstrap_token, agent_install_server_url }),
  });
}

export async function downloadOperationalEventsCsv() {
  const token = window.localStorage.getItem("patch-manager-token");
  const response = await fetch("/api/v1/settings/events/export.csv", {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.text();
}
