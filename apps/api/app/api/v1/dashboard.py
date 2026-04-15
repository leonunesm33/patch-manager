from collections import Counter
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.agent_command_repository import AgentCommandRepository
from app.repositories.agent_inventory_snapshot_repository import AgentInventorySnapshotRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_repository import PatchRepository
from app.repositories.agent_enrollment_repository import AgentEnrollmentRepository
from app.schemas.auth import UserResponse
from app.schemas.dashboard import (
    ActivityItem,
    DashboardResponse,
    DashboardSummary,
    PendingActionItem,
    PatchVolumeItem,
    PlatformDistribution,
    RebootPendingItem,
)
from app.services.agent_registry_service import agent_registry_service

router = APIRouter()


@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> DashboardResponse:
    machine_repository = MachineRepository(db)
    patch_repository = PatchRepository(db)
    execution_log_repository = ExecutionLogRepository(db)
    enrollment_repository = AgentEnrollmentRepository(db)
    command_repository = AgentCommandRepository(db)
    inventory_repository = AgentInventorySnapshotRepository(db)

    machines = machine_repository.list_all()
    patches = patch_repository.list_all()
    logs = execution_log_repository.list_recent(limit=20)

    monitored_machines = len(machines)
    pending_patches = sum(machine.pending_patches for machine in machines)
    total_logs = len(logs)
    successful_logs = len([log for log in logs if log.result == "applied"])
    compliance_rate = round((successful_logs / total_logs) * 100, 1) if total_logs else 100.0
    failed_jobs = len([log for log in logs if log.result == "failed"])
    reboot_pending_agents = [
        agent for agent in agent_registry_service.list_connected() if agent.reboot_required
    ]
    pending_enrollments = enrollment_repository.list_pending()
    recent_commands = command_repository.list_recent(limit=50)
    inventory_snapshots = inventory_repository.list_all()
    pending_commands = len([command for command in recent_commands if command.status in {"pending", "running"}])
    windows_pending_updates = sum(
        snapshot.upgradable_packages
        for snapshot in inventory_snapshots
        if snapshot.platform.lower() == "windows"
    )

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
            reboot_pending_hosts=len(reboot_pending_agents),
            pending_agent_commands=pending_commands,
            windows_pending_updates=windows_pending_updates,
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
        reboot_pending=[
            RebootPendingItem(
                agent_id=agent.agent_id,
                hostname=agent.hostname,
                platform=agent.platform,
                primary_ip=agent.primary_ip,
                last_seen_at=agent.last_seen_at.isoformat(),
            )
            for agent in reboot_pending_agents[:5]
        ],
        pending_actions=(
            [
                PendingActionItem(
                    title=f"{len(reboot_pending_agents)} hosts aguardando reboot",
                    detail="Hosts Linux exigem acao pos-patch conforme politica de reboot.",
                    action_type="reboot",
                    severity="warn",
                )
            ]
            if reboot_pending_agents
            else []
        )
        + (
            [
                PendingActionItem(
                    title=f"{pending_commands} comandos operacionais em andamento",
                    detail="Reboots e outras acoes administrativas aguardam consumo ou confirmacao dos agentes.",
                    action_type="agent_commands",
                    severity="warn",
                )
            ]
            if pending_commands
            else []
        )
        + (
            [
                PendingActionItem(
                    title=f"{windows_pending_updates} updates Windows pendentes",
                    detail="Pool Windows reportou atualizacoes aguardando scan, download ou instalacao.",
                    action_type="windows_updates",
                    severity="warn",
                )
            ]
            if windows_pending_updates
            else []
        )
        + (
            [
                PendingActionItem(
                    title=f"{len(pending_enrollments)} agentes aguardando aprovacao",
                    detail="Hosts novos ou reintegrados esperam aprovacao no console.",
                    action_type="agent_approval",
                    severity="warn",
                )
            ]
            if pending_enrollments
            else []
        )
        + (
            [
                PendingActionItem(
                    title=f"{failed_jobs} falhas recentes exigem revisao",
                    detail="Execucoes com erro ou bloqueio por guardrail requerem acompanhamento.",
                    action_type="failed_jobs",
                    severity="error",
                )
            ]
            if failed_jobs
            else []
        ),
    )
