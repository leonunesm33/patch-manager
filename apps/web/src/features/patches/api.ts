import { http } from "@/lib/http";
import type { PatchApproval } from "@/features/patches/types";

export function fetchPatchApprovals() {
  return http<PatchApproval[]>("/patches");
}
