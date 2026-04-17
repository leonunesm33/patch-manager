from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.machine import MachineModel
from app.repositories.agent_credential_repository import AgentCredentialRepository
from app.repositories.agent_command_repository import AgentCommandRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.patch_job_repository import PatchJobRepository
from app.repositories.agent_inventory_snapshot_repository import AgentInventorySnapshotRepository
from app.repositories.machine_repository import MachineRepository
from app.schemas.auth import UserResponse
from app.schemas.agent import AgentInventoryDetailItem, AgentInventoryDetailResponse
from app.repositories.agent_inventory_item_repository import AgentInventoryItemRepository
from app.schemas.machine import (
    Machine,
    MachineCommandSummary,
    MachineCreate,
    MachineExecutionSummary,
    MachineJobSummary,
    MachineOperationalDetails,
)
from app.services.agent_registry_service import agent_registry_service
from app.services.settings_service import SettingsService

router = APIRouter()
AGENT_CONNECTIVITY_MAX_AGE_SECONDS = 120

MOCK_MACHINES = [
    Machine(
        id="srv-web-01",
        name="SRV-WEB-01",
        ip="10.0.1.21",
        platform="Windows",
        group="Web Servers",
        status="online",
        pending_patches=4,
        last_check_in="2026-04-09T14:12:00Z",
        risk="critical",
    ),
    Machine(
        id="ubuntu-prod-03",
        name="ubuntu-prod-03",
        ip="10.1.4.33",
        platform="Ubuntu",
        group="Linux Production",
        status="online",
        pending_patches=3,
        last_check_in="2026-04-09T14:10:00Z",
        risk="important",
    ),
    Machine(
        id="srv-db-02",
        name="SRV-DB-02",
        ip="10.0.2.11",
        platform="Windows",
        group="Database",
        status="warning",
        pending_patches=7,
        last_check_in="2026-04-09T13:58:00Z",
        risk="critical",
    ),
]


@router.get("", response_model=list[Machine])
def list_machines(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[Machine]:
    try:
        repository = MachineRepository(db)
        snapshot_repository = AgentInventorySnapshotRepository(db)
        machines = repository.list_all()
        if machines:
            items: list[Machine] = []
            for machine in machines:
                machine_status = machine.status
                post_patch_state = None
                post_patch_message = None
                last_apply_at = None
                reboot_scheduled_at = None
                if machine.id.startswith("agent-"):
                    agent_id = machine.id.removeprefix("agent-")
                    snapshot = snapshot_repository.get_by_agent_id(agent_id)
                    if not agent_registry_service.is_connected(
                        agent_id,
                        max_age_seconds=AGENT_CONNECTIVITY_MAX_AGE_SECONDS,
                    ):
                        machine_status = "offline"
                    if snapshot is not None:
                        post_patch_state = snapshot.post_patch_state
                        post_patch_message = snapshot.post_patch_message
                        last_apply_at = snapshot.last_apply_at
                        reboot_scheduled_at = snapshot.reboot_scheduled_at
                items.append(
                    Machine.model_validate(machine).model_copy(
                        update={
                            "status": machine_status,
                            "post_patch_state": post_patch_state,
                            "post_patch_message": post_patch_message,
                            "last_apply_at": last_apply_at,
                            "reboot_scheduled_at": reboot_scheduled_at,
                        }
                    )
                )
            return items
    except SQLAlchemyError:
        pass

    return MOCK_MACHINES


@router.get("/{machine_id}", response_model=Machine)
def get_machine(
    machine_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Machine:
    try:
        repository = MachineRepository(db)
        machine = repository.get_by_id(machine_id)
        if machine is not None:
            return Machine.model_validate(machine)
    except SQLAlchemyError:
        pass

    for machine in MOCK_MACHINES:
        if machine.id == machine_id:
            return machine

    raise HTTPException(status_code=404, detail="Machine not found")


@router.get("/{machine_id}/operational-details", response_model=MachineOperationalDetails)
def get_machine_operational_details(
    machine_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> MachineOperationalDetails:
    machine_repository = MachineRepository(db)
    snapshot_repository = AgentInventorySnapshotRepository(db)
    inventory_item_repository = AgentInventoryItemRepository(db)
    job_repository = PatchJobRepository(db)
    execution_repository = ExecutionLogRepository(db)
    command_repository = AgentCommandRepository(db)

    machine = machine_repository.get_by_id(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    machine_status = machine.status
    inventory = None
    agent_id = None
    if machine.id.startswith("agent-"):
        agent_id = machine.id.removeprefix("agent-")
        if not agent_registry_service.is_connected(
            agent_id,
            max_age_seconds=AGENT_CONNECTIVITY_MAX_AGE_SECONDS,
        ):
            machine_status = "offline"

        snapshot = snapshot_repository.get_by_agent_id(agent_id)
        if snapshot is not None:
            inventory = AgentInventoryDetailResponse(
                agent_id=snapshot.agent_id,
                platform=snapshot.platform,
                hostname=snapshot.hostname,
                package_manager=snapshot.package_manager,
                pending_count=snapshot.upgradable_packages,
                installed_count=snapshot.installed_update_count or snapshot.installed_packages,
                updated_at=snapshot.updated_at,
                pending_updates=[
                    AgentInventoryDetailItem.model_validate(item)
                    for item in inventory_item_repository.list_pending_for_agent(agent_id)
                ],
                installed_updates=[
                    AgentInventoryDetailItem.model_validate(item)
                    for item in inventory_item_repository.list_installed_for_agent(agent_id)
                ],
            )

    machine_response = Machine.model_validate(machine).model_copy(
        update={"status": machine_status}
    )

    return MachineOperationalDetails(
        machine=machine_response,
        agent_id=agent_id,
        inventory=inventory,
        recent_jobs=[
            MachineJobSummary(
                id=item.id,
                schedule_name=item.schedule_name,
                patch_id=item.patch_id,
                platform=item.platform,
                severity=item.severity,
                status=item.status,
                claimed_by_agent=item.claimed_by_agent,
                error_message=item.error_message,
                created_at=item.created_at,
                started_at=item.started_at,
                finished_at=item.finished_at,
            )
            for item in job_repository.list_recent_for_machine(machine_id, limit=10)
        ],
        recent_executions=[
            MachineExecutionSummary(
                id=item.id,
                schedule_name=item.schedule_name,
                patch_id=item.patch_id,
                platform=item.platform,
                severity=item.severity,
                result=item.result,
                duration_seconds=item.duration_seconds,
                executed_at=item.executed_at,
            )
            for item in execution_repository.list_recent_for_machine(machine_id, limit=10)
        ],
        recent_commands=[
            MachineCommandSummary(
                id=item.id,
                command_type=item.command_type,
                status=item.status,
                requested_by=item.requested_by,
                message=item.message,
                created_at=item.created_at,
                finished_at=item.finished_at,
            )
            for item in (
                command_repository.list_recent_for_agent(agent_id, limit=10) if agent_id else []
            )
        ],
    )


@router.post("", response_model=Machine, status_code=201)
def create_machine(
    payload: MachineCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Machine:
    repository = MachineRepository(db)
    machine = repository.add(
        MachineModel(
            id=f"machine-{uuid4().hex[:8]}",
            name=payload.name,
            ip=payload.ip,
            platform=payload.platform,
            group=payload.group,
            status=payload.status,
            pending_patches=payload.pending_patches,
            last_check_in=datetime.now(UTC),
            risk=payload.risk,
        )
    )
    return Machine.model_validate(machine)


@router.put("/{machine_id}", response_model=Machine)
def update_machine(
    machine_id: str,
    payload: MachineCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Machine:
    repository = MachineRepository(db)
    machine = repository.get_by_id(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    machine.name = payload.name
    machine.ip = payload.ip
    machine.platform = payload.platform
    machine.group = payload.group
    machine.status = payload.status
    machine.pending_patches = payload.pending_patches
    machine.risk = payload.risk
    machine.last_check_in = datetime.now(UTC)

    machine = repository.update(machine)
    return Machine.model_validate(machine)


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(
    machine_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> Response:
    repository = MachineRepository(db)
    machine = repository.get_by_id(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    if machine.id.startswith("agent-"):
        agent_id = machine.id.removeprefix("agent-")
        credential_repository = AgentCredentialRepository(db)
        settings_service = SettingsService(db)
        credential = credential_repository.get_by_agent_id(agent_id)
        if credential is not None:
            credential.is_active = False
            credential_repository.update(credential)
            settings_service.record_operational_event(
                "agent_revoked_by_machine_delete",
                current_user.username,
                f"Revogou o agente {agent_id} ao remover a maquina {machine.name}.",
            )
        agent_registry_service.disconnect(agent_id)

    repository.delete(machine)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
