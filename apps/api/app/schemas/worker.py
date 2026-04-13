from pydantic import BaseModel


class PatchCycleRunResponse(BaseModel):
    schedules_matched: int
    approved_patches: int
    jobs_enqueued: int
    jobs_processed: int
    executions_created: int
    failed_executions: int


class PatchJobProcessResponse(BaseModel):
    pending_jobs_before: int
    jobs_started: int
    jobs_processed: int
    executions_created: int
    failed_executions: int


class SchedulerStatusResponse(BaseModel):
    running: bool
    enqueue_interval_seconds: int
    worker_interval_seconds: int
    next_enqueue_run_at: str | None
    next_worker_run_at: str | None
    last_enqueue_run_at: str | None
    last_worker_run_at: str | None
    last_enqueue_result: PatchCycleRunResponse | None
    last_worker_result: PatchJobProcessResponse | None
