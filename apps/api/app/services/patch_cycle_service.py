from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.execution_log import ExecutionLogModel
from app.models.machine import MachineModel
from app.models.patch import PatchModel
from app.models.patch_job import PatchJobModel
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_job_repository import PatchJobRepository
from app.repositories.patch_repository import PatchRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.worker import PatchCycleRunResponse, PatchJobProcessResponse


class PatchCycleService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.machine_repository = MachineRepository(session)
        self.patch_job_repository = PatchJobRepository(session)
        self.patch_repository = PatchRepository(session)
        self.schedule_repository = ScheduleRepository(session)
        self.execution_log_repository = ExecutionLogRepository(session)

    def run_once(self) -> PatchCycleRunResponse:
        enqueue_result = self.enqueue_jobs()
        process_result = self.process_pending_jobs()
        return PatchCycleRunResponse(
            schedules_matched=enqueue_result.schedules_matched,
            approved_patches=enqueue_result.approved_patches,
            jobs_enqueued=enqueue_result.jobs_enqueued,
            jobs_processed=process_result.jobs_processed,
            executions_created=process_result.executions_created,
            failed_executions=process_result.failed_executions,
        )

    def enqueue_jobs(self) -> PatchCycleRunResponse:
        approved_patches = [
            patch for patch in self.patch_repository.list_all() if patch.approval_status == "approved"
        ]
        schedules = self.schedule_repository.list_all()
        machines = self.machine_repository.list_all()

        matched_schedules = 0
        enqueued_jobs: list[PatchJobModel] = []

        for patch in approved_patches:
            related_schedules = [
                schedule
                for schedule in schedules
                if schedule.scope.strip().lower() == patch.target.strip().lower()
            ]
            if related_schedules:
                matched_schedules += len(related_schedules)

            for schedule in related_schedules:
                for machine in self._select_target_machines(machines, patch.target):
                    if self.patch_job_repository.exists_open_job(schedule.id, machine.id, patch.id):
                        continue
                    enqueued_jobs.append(
                        PatchJobModel(
                            id=f"job-{uuid4().hex[:10]}",
                            schedule_id=schedule.id,
                            schedule_name=schedule.name,
                            machine_id=machine.id,
                            machine_name=machine.name,
                            patch_id=patch.id,
                            platform=machine.platform,
                            severity=patch.severity,
                            status="pending",
                        )
                    )

        if enqueued_jobs:
            self.patch_job_repository.add_many(enqueued_jobs)

        return PatchCycleRunResponse(
            schedules_matched=matched_schedules,
            approved_patches=len(approved_patches),
            jobs_enqueued=len(enqueued_jobs),
            jobs_processed=0,
            executions_created=0,
            failed_executions=0,
        )

    def process_pending_jobs(self) -> PatchJobProcessResponse:
        machines = self.machine_repository.list_all()
        approved_patches = [
            patch for patch in self.patch_repository.list_all() if patch.approval_status == "approved"
        ]
        pending_jobs = self.patch_job_repository.list_pending()
        running_jobs = self.patch_job_repository.list_running()

        if running_jobs:
            backend_job = next(
                (job for job in running_jobs if not job.claimed_by_agent),
                None,
            )
            if backend_job is not None:
                return self._complete_running_job(
                    backend_job,
                    pending_jobs_before=len(pending_jobs),
                    machines=machines,
                    approved_patches=approved_patches,
                )
            return PatchJobProcessResponse(
                pending_jobs_before=len(pending_jobs),
                jobs_started=0,
                jobs_processed=0,
                executions_created=0,
                failed_executions=0,
            )

        if not pending_jobs:
            return PatchJobProcessResponse(
                pending_jobs_before=0,
                jobs_started=0,
                jobs_processed=0,
                executions_created=0,
                failed_executions=0,
            )

        next_job = next(
            (
                job
                for job in pending_jobs
                if job.platform.lower() not in {"ubuntu", "debian", "rhel", "linux"}
            ),
            None,
        )
        if next_job is None:
            return PatchJobProcessResponse(
                pending_jobs_before=len(pending_jobs),
                jobs_started=0,
                jobs_processed=0,
                executions_created=0,
                failed_executions=0,
            )
        next_job.status = "running"
        next_job.started_at = datetime.now(UTC)
        next_job.error_message = None
        self.patch_job_repository.update(next_job)

        return PatchJobProcessResponse(
            pending_jobs_before=len(pending_jobs),
            jobs_started=1,
            jobs_processed=0,
            executions_created=0,
            failed_executions=0,
        )

    def _complete_running_job(
        self,
        job: PatchJobModel,
        pending_jobs_before: int,
        machines: list[MachineModel],
        approved_patches: list[PatchModel],
    ) -> PatchJobProcessResponse:
        machine = next((item for item in machines if item.id == job.machine_id), None)
        patch = next((item for item in approved_patches if item.id == job.patch_id), None)

        if machine is None or patch is None:
            job.status = "failed"
            job.error_message = "Machine or patch context not found."
            job.finished_at = datetime.now(UTC)
            self.patch_job_repository.update(job)
            return PatchJobProcessResponse(
                pending_jobs_before=pending_jobs_before,
                jobs_started=0,
                jobs_processed=1,
                executions_created=0,
                failed_executions=1,
            )

        result = "failed" if machine.status == "offline" else "applied"
        failed_executions = 0

        if result == "failed":
            failed_executions = 1
            job.status = "failed"
            job.error_message = "Machine offline during execution."
        else:
            machine.pending_patches = max(machine.pending_patches - 1, 0)
            machine.last_check_in = datetime.now(UTC)
            self.machine_repository.update(machine)
            job.status = "completed"
            job.error_message = None

        job.finished_at = datetime.now(UTC)
        self.patch_job_repository.update(job)

        self.execution_log_repository.add_many(
            [
                ExecutionLogModel(
                    id=f"log-{uuid4().hex[:10]}",
                    schedule_id=job.schedule_id,
                    schedule_name=job.schedule_name,
                    machine_id=job.machine_id,
                    machine_name=job.machine_name,
                    patch_id=job.patch_id,
                    platform=job.platform,
                    severity=job.severity,
                    result=result,
                    duration_seconds=self._estimate_duration_seconds(machine, patch),
                    executed_at=datetime.now(UTC),
                )
            ]
        )

        return PatchJobProcessResponse(
            pending_jobs_before=pending_jobs_before,
            jobs_started=0,
            jobs_processed=1,
            executions_created=1,
            failed_executions=failed_executions,
        )

    def _select_target_machines(
        self,
        machines: list[MachineModel],
        target: str,
    ) -> list[MachineModel]:
        target_normalized = target.strip().lower()
        if "windows" in target_normalized:
            return [machine for machine in machines if machine.platform.lower() == "windows"]
        if "ubuntu" in target_normalized:
            return [machine for machine in machines if machine.platform.lower() == "ubuntu"]
        return machines

    def _estimate_duration_seconds(self, machine: MachineModel, patch: PatchModel) -> int:
        return 90 + ((len(machine.name) + len(patch.id)) % 6) * 37
