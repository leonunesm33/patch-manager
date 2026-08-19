import { http } from "@/lib/http";
import type {
  Machine,
  MachineCreate,
  MachineGroup,
  MachineGroupCreate,
  MachineOperationalDetails,
} from "@/features/machines/types";

export function fetchMachines() {
  return http<Machine[]>("/machines");
}

export function createMachine(payload: MachineCreate) {
  return http<Machine>("/machines", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateMachine(machineId: string, payload: MachineCreate) {
  return http<Machine>(`/machines/${machineId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function resolveIdentityConflict(machineId: string) {
  return http<Machine>(`/machines/${machineId}/resolve-identity-conflict`, {
    method: "POST",
  });
}

export function deleteMachine(machineId: string) {
  return http<void>(`/machines/${machineId}`, {
    method: "DELETE",
  });
}

export function fetchMachineOperationalDetails(machineId: string) {
  return http<MachineOperationalDetails>(`/machines/${machineId}/operational-details`);
}

export function fetchMachineGroups() {
  return http<MachineGroup[]>("/machines/groups");
}

export function createMachineGroup(payload: MachineGroupCreate) {
  return http<MachineGroup>("/machines/groups", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function deleteMachineGroup(groupId: string) {
  return http<void>(`/machines/groups/${groupId}`, {
    method: "DELETE",
  });
}
