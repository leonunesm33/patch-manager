export type ReportItem = {
  date: string;
  schedule: string;
  machine: string;
  patch: string;
  platform: string;
  severity: string;
  result: string;
  duration: string;
};

export type PatchCycleRunResponse = {
  schedules_matched: number;
  approved_patches: number;
  jobs_enqueued: number;
  jobs_processed: number;
  executions_created: number;
  failed_executions: number;
};

export type PatchJobProcessResponse = {
  pending_jobs_before: number;
  jobs_started: number;
  jobs_processed: number;
  executions_created: number;
  failed_executions: number;
};

export type PatchJobItem = {
  id: string;
  schedule_name: string;
  machine_name: string;
  patch_id: string;
  platform: string;
  severity: string;
  status: "pending" | "running" | "completed" | "failed";
  claimed_by_agent: string | null;
  claimed_at: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};
