import { http, httpRaw } from "@/lib/http";
import type {
  PatchCycleRunResponse,
  PatchJobProcessResponse,
  PatchJobItem,
  ReportItem,
} from "@/features/reports/types";

export function fetchReports() {
  return http<ReportItem[]>("/reports");
}

export function exportReportsXlsx() {
  return httpRaw("/reports/export.xlsx");
}

export function runPatchCycle() {
  return http<PatchCycleRunResponse>("/agents/run-cycle", {
    method: "POST",
  });
}

export function processPatchJobs() {
  return http<PatchJobProcessResponse>("/agents/process-jobs", {
    method: "POST",
  });
}

export function fetchPatchJobs() {
  return http<PatchJobItem[]>("/agents/jobs");
}
