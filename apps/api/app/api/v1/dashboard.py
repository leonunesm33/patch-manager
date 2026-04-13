from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_repository import PatchRepository
from app.schemas.auth import UserResponse
from app.schemas.dashboard import (
    ActivityItem,
    DashboardResponse,
    DashboardSummary,
    PatchVolumeItem,
    PlatformDistribution,
)

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> DashboardResponse:
    machine_repository = MachineRepository(db)
    patch_repository = PatchRepository(db)
    execution_log_repository = ExecutionLogRepository(db)

    machines = machine_repository.list_all()
    patches = patch_repository.list_all()
    logs = execution_log_repository.list_recent(limit=20)

    monitored_machines = len(machines)
    pending_patches = sum(machine.pending_patches for machine in machines)
    total_logs = len(logs)
    successful_logs = len([log for log in logs if log.result == "applied"])
    compliance_rate = round((successful_logs / total_logs) * 100, 1) if total_logs else 100.0
    failed_jobs = len([log for log in logs if log.result == "failed"])

    platform_counter = Counter(machine.platform.lower() for machine in machines)
    windows_servers = len(
        [machine for machine in machines if machine.platform.lower() == "windows"]
    )
    linux_servers = len(
        [
            machine
            for machine in machines
            if machine.platform.lower() in {"ubuntu", "debian", "rhel", "linux"}
        ]
    )

    recent_activity = [
        ActivityItem(
            title=f"{log.patch_id} executado em {log.machine_name}",
            detail=f"{log.schedule_name} · {log.platform}",
            status="ok" if log.result == "applied" else "error",
        )
        for log in logs[:5]
    ]

    if not recent_activity:
        recent_activity = [
            ActivityItem(
                title="Nenhuma execucao registrada ainda",
                detail="Aprove patches e rode um ciclo para popular a atividade",
                status="warn",
            )
        ]

    return DashboardResponse(
        summary=DashboardSummary(
            monitored_machines=monitored_machines,
            pending_patches=pending_patches,
            compliance_rate=compliance_rate,
            failed_jobs=failed_jobs,
        ),
        activity=recent_activity,
        patch_volume=[
            PatchVolumeItem(
                label="Aprovados",
                windows=len(
                    [
                        patch
                        for patch in patches
                        if patch.approval_status == "approved"
                        and "windows" in patch.target.lower()
                    ]
                ),
                linux=len(
                    [
                        patch
                        for patch in patches
                        if patch.approval_status == "approved"
                        and "ubuntu" in patch.target.lower()
                    ]
                ),
            ),
            PatchVolumeItem(
                label="Pendentes",
                windows=len(
                    [
                        patch
                        for patch in patches
                        if patch.approval_status == "pending"
                        and "windows" in patch.target.lower()
                    ]
                ),
                linux=len(
                    [
                        patch
                        for patch in patches
                        if patch.approval_status == "pending"
                        and "ubuntu" in patch.target.lower()
                    ]
                ),
            ),
            PatchVolumeItem(
                label="Rejeitados",
                windows=len(
                    [
                        patch
                        for patch in patches
                        if patch.approval_status == "rejected"
                        and "windows" in patch.target.lower()
                    ]
                ),
                linux=len(
                    [
                        patch
                        for patch in patches
                        if patch.approval_status == "rejected"
                        and "ubuntu" in patch.target.lower()
                    ]
                ),
            ),
        ],
        platform_distribution=PlatformDistribution(
            windows_servers=windows_servers,
            windows_workstations=max(platform_counter.get("windows", 0) - windows_servers, 0),
            linux_servers=linux_servers,
        ),
    )
