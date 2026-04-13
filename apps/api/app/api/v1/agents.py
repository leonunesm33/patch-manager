from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_agent_key, get_current_user, get_db
from app.models.execution_log import ExecutionLogModel
from app.models.machine import MachineModel
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.patch_job_repository import PatchJobRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_repository import PatchRepository
from app.schemas.agent import (
    AgentCheckInRequest,
    AgentHeartbeatRequest,
    AgentInventoryRequest,
    AgentJobClaimRequest,
    AgentJobResponse,
    AgentJobResultRequest,
    ConnectedAgentResponse,
)
from app.schemas.auth import UserResponse
from app.schemas.job import PatchJobItem
from app.schemas.worker import (
    PatchCycleRunResponse,
    PatchJobProcessResponse,
    SchedulerStatusResponse,
)
from app.services.agent_registry_service import agent_registry_service
from app.services.patch_cycle_service import PatchCycleService
from app.services.scheduler_service import scheduler_service
from app.services.settings_service import SettingsService
router = APIRouter()


@router.get("/status")
def agent_status(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> dict[str, object]:
    return {
        "connected_agents": agent_registry_service.count_connected(),
        "linux_ready": agent_registry_service.has_platform("linux"),
        "windows_ready": agent_registry_service.has_platform("windows"),
    }


@router.post("/run-cycle", response_model=PatchCycleRunResponse)
def run_patch_cycle(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> PatchCycleRunResponse:
    service = PatchCycleService(db)
    return service.enqueue_jobs()


@router.post("/process-jobs", response_model=PatchJobProcessResponse)
def process_patch_jobs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> PatchJobProcessResponse:
    service = PatchCycleService(db)
    return service.process_pending_jobs()


@router.get("/scheduler-status", response_model=SchedulerStatusResponse)
def get_scheduler_status(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> SchedulerStatusResponse:
    return scheduler_service.status()


@router.post("/scheduler/start", response_model=SchedulerStatusResponse)
def start_scheduler(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> SchedulerStatusResponse:
    return scheduler_service.start()


@router.post("/scheduler/stop", response_model=SchedulerStatusResponse)
def stop_scheduler(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> SchedulerStatusResponse:
    return scheduler_service.stop()


@router.get("/jobs", response_model=list[PatchJobItem])
def list_patch_jobs(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[PatchJobItem]:
    repository = PatchJobRepository(db)
    return [PatchJobItem.model_validate(job) for job in repository.list_recent()]


@router.get("/connected", response_model=list[ConnectedAgentResponse])
def list_connected_agents(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[ConnectedAgentResponse]:
    return agent_registry_service.list_connected()


@router.post("/check-in")
def check_in_agent(
    payload: AgentCheckInRequest,
    _: Annotated[str, Depends(get_agent_key)],
) -> dict[str, str]:
    agent_registry_service.check_in(
        payload.agent_id,
        payload.platform,
        payload.hostname,
        payload.os_name,
        payload.os_version,
        payload.kernel_version,
        payload.agent_version,
        payload.execution_mode,
    )
    return {"status": "ok"}


@router.post("/inventory")
def submit_agent_inventory(
    payload: AgentInventoryRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_agent_key)],
) -> dict[str, str]:
    agent_registry_service.update_inventory(
        payload.agent_id,
        payload.platform,
        payload.hostname,
        payload.primary_ip,
        payload.package_manager,
        payload.installed_packages,
        payload.upgradable_packages,
        payload.reboot_required,
        payload.os_name,
        payload.os_version,
        payload.kernel_version,
        payload.agent_version,
        payload.execution_mode,
    )

    machine_repository = MachineRepository(db)
    machine = machine_repository.get_by_name(payload.hostname)
    risk = "critical" if payload.upgradable_packages >= 10 else "important"
    if payload.upgradable_packages == 0:
        risk = "optional"

    if machine is None:
        machine_repository.add(
            MachineModel(
                id=f"agent-{payload.agent_id}",
                name=payload.hostname,
                ip=payload.primary_ip,
                platform="Ubuntu" if payload.platform.lower() == "linux" else payload.platform.title(),
                group="Agent Managed",
                status="online",
                pending_patches=payload.upgradable_packages,
                last_check_in=datetime.now(UTC),
                risk=risk,
            )
        )
    else:
        machine.ip = payload.primary_ip
        machine.platform = "Ubuntu" if payload.platform.lower() == "linux" else payload.platform.title()
        machine.group = "Agent Managed"
        machine.status = "online"
        machine.pending_patches = payload.upgradable_packages
        machine.last_check_in = datetime.now(UTC)
        machine.risk = risk
        machine_repository.update(machine)

    return {"status": "ok"}


@router.post("/heartbeat")
def heartbeat_agent(
    payload: AgentHeartbeatRequest,
    _: Annotated[str, Depends(get_agent_key)],
) -> dict[str, str]:
    agent_registry_service.heartbeat(payload.agent_id, payload.platform, payload.hostname)
    return {"status": "ok"}


@router.post("/claim-job", response_model=AgentJobResponse | None)
def claim_job_for_agent(
    payload: AgentJobClaimRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_agent_key)],
) -> AgentJobResponse | None:
    repository = PatchJobRepository(db)
    machine_repository = MachineRepository(db)
    job = repository.get_next_pending_for_platform(payload.platform)
    if job is None:
        return None

    job.status = "running"
    job.claimed_by_agent = payload.agent_id
    job.claimed_at = datetime.now(UTC)
    job.started_at = datetime.now(UTC)
    repository.update(job)
    agent_registry_service.heartbeat(payload.agent_id, payload.platform, payload.agent_id)
    settings_service = SettingsService(db)
    machine = machine_repository.get_by_id(job.machine_id)
    return AgentJobResponse(
        id=job.id,
        schedule_name=job.schedule_name,
        machine_id=job.machine_id,
        machine_name=job.machine_name,
        patch_id=job.patch_id,
        platform=job.platform,
        severity=job.severity,
        execution_mode=settings_service.resolve_linux_execution_mode(machine.group if machine else None)
        if payload.platform.lower() == "linux"
        else "apply",
        status=job.status,
        claimed_by_agent=job.claimed_by_agent,
        claimed_at=job.claimed_at,
    )


@router.post("/jobs/{job_id}/result")
def submit_agent_job_result(
    job_id: str,
    payload: AgentJobResultRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_agent_key)],
) -> dict[str, str]:
    job_repository = PatchJobRepository(db)
    job = job_repository.get_by_id(job_id)
    if job is None:
        return {"status": "missing"}

    patch_repository = PatchRepository(db)
    machine_repository = MachineRepository(db)
    execution_log_repository = ExecutionLogRepository(db)

    patch = patch_repository.get_by_id(job.patch_id)
    machine = machine_repository.get_by_id(job.machine_id)

    result = payload.result.lower()
    job.status = "completed" if result == "applied" else "failed"
    job.error_message = payload.error_message
    job.finished_at = datetime.now(UTC)
    job_repository.update(job)

    if machine is not None and result == "applied":
        machine.pending_patches = max(machine.pending_patches - 1, 0)
        machine.last_check_in = datetime.now(UTC)
        machine_repository.update(machine)

    execution_log_repository.add_many(
        [
            ExecutionLogModel(
                id=f"log-{job.id}",
                schedule_id=job.schedule_id,
                schedule_name=job.schedule_name,
                machine_id=job.machine_id,
                machine_name=job.machine_name,
                patch_id=job.patch_id,
                platform=job.platform,
                severity=job.severity if patch is None else patch.severity,
                result=result,
                duration_seconds=120,
                executed_at=datetime.now(UTC),
            )
        ]
    )

    agent_registry_service.heartbeat(payload.agent_id, job.platform, payload.agent_id)
    return {"status": "ok"}
