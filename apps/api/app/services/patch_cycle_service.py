from datetime import UTC, date, datetime, time
from hashlib import sha1
import json
from uuid import uuid4
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.agent_command import AgentCommandModel
from app.models.execution_log import ExecutionLogModel
from app.models.machine import MachineModel
from app.models.patch import PatchModel
from app.models.patch_job import PatchJobModel
from app.models.schedule import ScheduleModel
from app.repositories.agent_command_repository import AgentCommandRepository
from app.repositories.agent_inventory_snapshot_repository import AgentInventorySnapshotRepository
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
        self.agent_command_repository = AgentCommandRepository(session)
        self.snapshot_repository = AgentInventorySnapshotRepository(session)

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
            reboot_commands_enqueued=enqueue_result.reboot_commands_enqueued,
        )

    def enqueue_jobs(self) -> PatchCycleRunResponse:
        approved_patches = [
            patch for patch in self.patch_repository.list_all() if patch.approval_status == "approved"
        ]
        schedules = self.schedule_repository.list_all()
        machines = self.machine_repository.list_all()
        now = datetime.now(ZoneInfo("America/Sao_Paulo"))

        matched_schedules = 0
        enqueued_jobs: list[PatchJobModel] = []

        for patch in approved_patches:
            related_schedules = [
                schedule
                for schedule in schedules
                if schedule.is_active
                and self._is_install_window_due(schedule, now)
                and self._select_job_machines(schedule, patch, machines)
            ]
            if related_schedules:
                matched_schedules += len(related_schedules)

            for schedule in related_schedules:
                for machine in self._select_job_machines(schedule, patch, machines):
                    # Block duplicates only for non-failed jobs created today.
                    # Failed jobs can be retried, but only up to MAX_RETRIES_PER_WINDOW times.
                    window_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo).astimezone(UTC)
                    if self.patch_job_repository.exists_active_or_completed_job_since(
                        schedule.id, machine.id, patch.id, window_start
                    ):
                        continue
                    if self.patch_job_repository.count_failed_jobs_since(
                        schedule.id, machine.id, patch.id, window_start
                    ) >= self.MAX_RETRIES_PER_WINDOW:
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

        reboot_commands_enqueued = self.enqueue_due_reboot_commands(
            schedules=schedules,
            machines=machines,
            now=now,
        )

        return PatchCycleRunResponse(
            schedules_matched=matched_schedules,
            approved_patches=len(approved_patches),
            jobs_enqueued=len(enqueued_jobs),
            jobs_processed=0,
            executions_created=0,
            failed_executions=0,
            reboot_commands_enqueued=reboot_commands_enqueued,
        )

    def enqueue_due_reboot_commands(
        self,
        *,
        schedules: list[ScheduleModel] | None = None,
        machines: list[MachineModel] | None = None,
        now: datetime | None = None,
    ) -> int:
        schedules = schedules if schedules is not None else self.schedule_repository.list_all()
        machines = machines if machines is not None else self.machine_repository.list_all()
        now = now or datetime.now(ZoneInfo("America/Sao_Paulo"))
        commands: list[AgentCommandModel] = []
        reboot_commands_reset = 0

        for schedule in schedules:
            if not schedule.is_active:
                continue
            reboot_policy = self._normalize_reboot_policy(schedule.reboot_policy)
            if reboot_policy == "never" or not self._is_reboot_window_due(schedule, now):
                continue

            period_key = self._schedule_period_key(schedule, now, use_reboot=True)
            for machine in self._select_schedule_machines(schedule, machines):
                agent_id = self._agent_id_from_machine(machine)
                if agent_id is None:
                    continue
                if not self._machine_has_completed_pm_cycle(agent_id):
                    # Máquina recém-enrollada (post_patch_state="idle"): nunca foi gerenciada
                    # pelo PM. Não envia reboot mesmo com policy "always" para evitar reboots
                    # inesperados logo após instalação do agente.
                    continue
                if reboot_policy == "if-needed" and not self._machine_needs_reboot(agent_id):
                    continue

                command_id = self._scheduled_reboot_command_id(schedule.id, agent_id, period_key)
                existing = self.agent_command_repository.get_by_id(command_id)
                if existing is not None:
                    if existing.status == "failed":
                        # Reset failed command so the agent retries
                        existing.status = "pending"
                        self.agent_command_repository.add(existing)
                        self.snapshot_repository.update_post_patch_state(
                            agent_id,
                            post_patch_state="reboot-scheduled",
                            post_patch_message=f"Reboot re-enfileirado pela janela {schedule.name} (tentativa anterior falhou).",
                            reboot_scheduled_at=datetime.now(UTC),
                        )
                        reboot_commands_reset += 1
                    continue

                commands.append(
                    AgentCommandModel(
                        id=command_id,
                        agent_id=agent_id,
                        command_type="scheduled_reboot",
                        status="pending",
                        requested_by="scheduler",
                        message=f"Reboot agendado pela janela {schedule.name}.",
                        payload_json=json.dumps(
                            {
                                "schedule_id": schedule.id,
                                "schedule_name": schedule.name,
                                "machine_id": machine.id,
                                "machine_name": machine.name,
                                "scheduled_for": period_key,
                                "reboot_policy": reboot_policy,
                            }
                        ),
                    )
                )
                self.snapshot_repository.update_post_patch_state(
                    agent_id,
                    post_patch_state="reboot-scheduled",
                    post_patch_message=f"Reboot enfileirado pela janela {schedule.name}.",
                    reboot_scheduled_at=datetime.now(UTC),
                )

        for command in commands:
            self.agent_command_repository.add(command)
        return len(commands) + reboot_commands_reset

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
        if target_normalized.startswith("machine:"):
            machine_id = target_normalized.removeprefix("machine:")
            return [machine for machine in machines if machine.id.lower() == machine_id]
        if "windows" in target_normalized:
            return [machine for machine in machines if machine.platform.lower() == "windows"]
        if "ubuntu" in target_normalized:
            return [machine for machine in machines if machine.platform.lower() == "ubuntu"]
        return machines

    def _select_schedule_machines(
        self,
        schedule: ScheduleModel,
        machines: list[MachineModel],
    ) -> list[MachineModel]:
        scope_type = (schedule.scope_type or "group").strip().lower()
        scope_value = (schedule.scope_value or schedule.scope).strip().lower()
        if scope_type == "machine":
            return [machine for machine in machines if machine.id.lower() == scope_value]
        if scope_type == "group":
            return [machine for machine in machines if machine.group.lower() == scope_value]
        if scope_type == "os":
            if scope_value == "windows":
                return [machine for machine in machines if machine.platform.lower() == "windows"]
            if scope_value == "linux":
                return [
                    machine
                    for machine in machines
                    if machine.platform.lower() in {"ubuntu", "debian", "rhel", "linux"}
                ]
        return self._select_target_machines(machines, schedule.scope)

    def _select_job_machines(
        self,
        schedule: ScheduleModel,
        patch: PatchModel,
        machines: list[MachineModel],
    ) -> list[MachineModel]:
        patch_machines = {machine.id for machine in self._select_target_machines(machines, patch.target)}
        schedule_machines = self._select_schedule_machines(schedule, machines)
        return [machine for machine in schedule_machines if machine.id in patch_machines]

    def _is_install_window_due(self, schedule: ScheduleModel, now: datetime) -> bool:
        return self._is_schedule_window_due(
            schedule.recurrence,
            schedule.install_date,
            schedule.install_time,
            now,
        )

    def _is_reboot_window_due(self, schedule: ScheduleModel, now: datetime) -> bool:
        if not schedule.reboot_time:
            return False
        return self._is_schedule_window_due(
            schedule.recurrence,
            schedule.reboot_date or schedule.install_date,
            schedule.reboot_time,
            now,
        )

    # Janela máxima de tolerância após o horário agendado. Após este período
    # o scheduler para de gerar novos comandos para aquela janela, evitando
    # que agentes recém-instalados recebam comandos de reboot de janelas já expiradas.
    WINDOW_MAX_AGE_SECONDS: int = 3600  # 60 minutos
    # Número máximo de tentativas por job dentro do mesmo dia antes de parar de retentar.
    MAX_RETRIES_PER_WINDOW: int = 3

    def _is_schedule_window_due(
        self,
        recurrence: str | None,
        anchor_date: date | None,
        scheduled_time: str | None,
        now: datetime,
    ) -> bool:
        if not scheduled_time:
            return False

        parsed_time = self._parse_time(scheduled_time)
        if parsed_time is None:
            return False

        recurrence_value = (recurrence or "weekly").strip().lower()
        anchor = anchor_date or now.date()
        scheduled_at = datetime.combine(now.date(), parsed_time, tzinfo=now.tzinfo)
        if scheduled_at > now:
            return False

        if (now - scheduled_at).total_seconds() > self.WINDOW_MAX_AGE_SECONDS:
            return False

        if recurrence_value == "once":
            return now.date() == anchor
        if recurrence_value == "daily":
            return now.date() >= anchor
        if recurrence_value == "weekly":
            return now.date() >= anchor and now.weekday() == anchor.weekday()
        if recurrence_value == "monthly":
            return now.date() >= anchor and now.day == anchor.day
        return False

    def _schedule_period_key(self, schedule: ScheduleModel, now: datetime, *, use_reboot: bool) -> str:
        scheduled_time = schedule.reboot_time if use_reboot else schedule.install_time
        recurrence_value = (schedule.recurrence or "weekly").strip().lower()
        if recurrence_value == "once":
            scheduled_date = schedule.reboot_date if use_reboot else schedule.install_date
            return f"{scheduled_date or now.date()}T{scheduled_time}"
        if recurrence_value == "monthly":
            return f"{now:%Y-%m}T{scheduled_time}"
        if recurrence_value == "weekly":
            return f"{now:%G-W%V}T{scheduled_time}"
        return f"{now:%Y-%m-%d}T{scheduled_time}"

    def _parse_time(self, value: str) -> time | None:
        try:
            return time.fromisoformat(value)
        except ValueError:
            return None

    def _normalize_reboot_policy(self, reboot_policy: str | None) -> str:
        normalized = (reboot_policy or "").strip().lower()
        if "nao" in normalized or "não" in normalized or normalized == "never":
            return "never"
        if "sempre" in normalized or normalized == "always":
            return "always"
        return "if-needed"

    def _agent_id_from_machine(self, machine: MachineModel) -> str | None:
        if not machine.id.startswith("agent-"):
            return None
        return machine.id.removeprefix("agent-")

    def _machine_has_completed_pm_cycle(self, agent_id: str) -> bool:
        """Retorna True apenas se a máquina passou por pelo menos um ciclo de patching do PM.
        Estado 'idle' indica máquina recém-enrollada que ainda não foi gerenciada pelo PM."""
        snapshot = self.snapshot_repository.get_by_agent_id(agent_id)
        if snapshot is None:
            return False
        return snapshot.post_patch_state not in {None, "idle"}

    def _machine_needs_reboot(self, agent_id: str) -> bool:
        snapshot = self.snapshot_repository.get_by_agent_id(agent_id)
        if snapshot is None:
            return False
        # Only consider reboots initiated by a Patch Manager patch cycle.
        # snapshot.reboot_required reflects the OS-level /var/run/reboot-required and
        # would trigger reboots on freshly enrolled hosts that already had that file.
        return snapshot.post_patch_state in {"reboot-required", "reboot-scheduled", "reboot-failed"}

    def _scheduled_reboot_command_id(self, schedule_id: str, agent_id: str, period_key: str) -> str:
        digest = sha1(f"{schedule_id}:{agent_id}:{period_key}:reboot".encode("utf-8")).hexdigest()[:18]
        return f"cmd-reboot-{digest}"

    def _estimate_duration_seconds(self, machine: MachineModel, patch: PatchModel) -> int:
        return 90 + ((len(machine.name) + len(patch.id)) % 6) * 37
