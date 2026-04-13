import { http } from "@/lib/http";
import type {
  ConnectedAgent,
  ExecutionSettings,
  SchedulerStatusResponse,
  SettingsResponse,
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

export function updateLinuxExecutionMode(
  linux_agent_mode: "dry-run" | "apply",
  machine_group?: string,
) {
  return http<ExecutionSettings>("/settings/execution-mode", {
    method: "PUT",
    body: JSON.stringify({ linux_agent_mode, machine_group }),
  });
}
