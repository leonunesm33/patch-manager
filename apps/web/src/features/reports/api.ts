import { http } from "@/lib/http";
import type { ReportItem } from "@/features/reports/types";

export function fetchReports() {
  return http<ReportItem[]>("/reports");
}
