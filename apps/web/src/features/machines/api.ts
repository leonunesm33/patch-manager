import { http } from "@/lib/http";
import type { Machine } from "@/features/machines/types";

export function fetchMachines() {
  return http<Machine[]>("/machines");
}
