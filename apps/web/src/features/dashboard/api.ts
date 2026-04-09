import { http } from "@/lib/http";
import type { DashboardResponse } from "@/features/dashboard/types";

export function fetchDashboard() {
  return http<DashboardResponse>("/dashboard");
}
