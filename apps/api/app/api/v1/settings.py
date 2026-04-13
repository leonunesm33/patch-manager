from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.machine_repository import MachineRepository
from app.schemas.auth import UserResponse
from app.schemas.settings import ExecutionModeSetting, SettingsResponse, ToggleSetting
from app.schemas.settings_update import LinuxExecutionModeUpdate
from app.services.settings_service import SettingsService

router = APIRouter()


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> SettingsResponse:
    settings_service = SettingsService(db)
    machine_groups = MachineRepository(db).list_groups()
    return SettingsResponse(
        policy=[
            ToggleSetting(
                label="Patches criticos automaticos",
                description="Aplica patches criticos sem aprovacao manual.",
                enabled=True,
            ),
            ToggleSetting(
                label="Patches opcionais requerem aprovacao",
                description="Mantem o time no controle sobre updates nao obrigatorios.",
                enabled=True,
            ),
        ],
        notifications=[
            ToggleSetting(
                label="Notificar falhas",
                description="Envia alerta imediato quando uma execucao falha.",
                enabled=True,
            ),
            ToggleSetting(
                label="Relatorio semanal",
                description="Entrega uma visao executiva de conformidade.",
                enabled=False,
            ),
        ],
        execution=ExecutionModeSetting.model_validate(
            settings_service.build_execution_settings(machine_groups)
        ),
    )


@router.put("/execution-mode", response_model=ExecutionModeSetting)
def update_execution_mode(
    payload: LinuxExecutionModeUpdate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> ExecutionModeSetting:
    settings_service = SettingsService(db)
    if payload.machine_group:
        settings_service.set_linux_group_execution_mode(payload.machine_group, payload.linux_agent_mode)
    else:
        settings_service.set_linux_execution_mode(payload.linux_agent_mode)

    machine_groups = MachineRepository(db).list_groups()
    return ExecutionModeSetting.model_validate(settings_service.build_execution_settings(machine_groups))
