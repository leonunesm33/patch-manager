import { http } from "@/lib/http";
import type { Machine, MachineCreate, MachineOperationalDetails } from "@/features/machines/types";

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

export function deleteMachine(machineId: string) {
  return http<void>(`/machines/${machineId}`, {
    method: "DELETE",
  });
}

export function fetchMachineOperationalDetails(machineId: string) {
  return http<MachineOperationalDetails>(`/machines/${machineId}/operational-details`);
}
