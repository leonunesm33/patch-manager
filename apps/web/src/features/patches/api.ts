import { http } from "@/lib/http";
import type { PatchApproval, PatchCreate } from "@/features/patches/types";

export function fetchPatchApprovals() {
  return http<PatchApproval[]>("/patches");
}

export function approvePatch(patchId: string) {
  return http<PatchApproval>(`/patches/${patchId}/approve`, {
    method: "POST",
  });
}

export function rejectPatch(patchId: string) {
  return http<PatchApproval>(`/patches/${patchId}/reject`, {
    method: "POST",
  });
}

export function createPatch(payload: PatchCreate) {
  return http<PatchApproval>("/patches", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updatePatch(patchId: string, payload: PatchCreate) {
  return http<PatchApproval>(`/patches/${patchId}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export function deletePatch(patchId: string) {
  return http<void>(`/patches/${patchId}`, {
    method: "DELETE",
  });
}
