import csv
from io import StringIO
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.machine_repository import MachineRepository
from app.schemas.auth import UserResponse
from app.schemas.settings import BootstrapSetting, ExecutionModeSetting, SettingsResponse, ToggleSetting
from app.schemas.settings_update import BootstrapTokenUpdate, LinuxExecutionModeUpdate
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
        bootstrap=BootstrapSetting(
            agent_bootstrap_token=settings_service.get_agent_bootstrap_token(),
            agent_install_server_url=settings_service.get_agent_install_server_url(),
        ),
        events=settings_service.list_operational_events(),
    )


@router.put("/execution-mode", response_model=ExecutionModeSetting)
def update_execution_mode(
    payload: LinuxExecutionModeUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> ExecutionModeSetting:
    settings_service = SettingsService(db)
    if payload.machine_group:
        settings_service.set_linux_group_execution_mode(payload.machine_group, payload.linux_agent_mode)
    else:
        previous_windows_scan_apply = settings_service.get_windows_scan_apply_enabled()
        previous_windows_timeout = settings_service.get_windows_command_timeout_seconds()
        settings_service.set_linux_execution_mode(payload.linux_agent_mode)
        if payload.real_apply_enabled is not None:
            was_enabled = settings_service.get_linux_real_apply_enabled()
            settings_service.set_linux_real_apply_enabled(payload.real_apply_enabled)
            if payload.real_apply_enabled and not was_enabled:
                settings_service.record_linux_real_apply_enabled_by(current_user.username)
                settings_service.record_operational_event(
                    "linux_real_apply_enabled",
                    current_user.username,
                    "Habilitou apply real para agentes Linux.",
                )
            if not payload.real_apply_enabled and was_enabled:
                settings_service.record_operational_event(
                    "linux_real_apply_disabled",
                    current_user.username,
                    "Desabilitou apply real para agentes Linux.",
                )
        if payload.allow_security_only is not None:
            settings_service.set_linux_allow_security_only(payload.allow_security_only)
        if payload.allowed_package_patterns is not None:
            settings_service.set_linux_allowed_package_patterns(payload.allowed_package_patterns)
        if payload.apt_apply_timeout_seconds is not None:
            settings_service.set_linux_apt_apply_timeout_seconds(payload.apt_apply_timeout_seconds)
        if payload.reboot_policy is not None:
            settings_service.set_linux_reboot_policy(payload.reboot_policy)
        if payload.reboot_grace_minutes is not None:
            settings_service.set_linux_reboot_grace_minutes(payload.reboot_grace_minutes)
        if payload.windows_scan_apply_enabled is not None:
            settings_service.set_windows_scan_apply_enabled(payload.windows_scan_apply_enabled)
            if payload.windows_scan_apply_enabled != previous_windows_scan_apply:
                settings_service.record_operational_event(
                    "windows_scan_apply_updated",
                    current_user.username,
                    (
                        "Habilitou StartScan controlado para agentes Windows."
                        if payload.windows_scan_apply_enabled
                        else "Desabilitou StartScan controlado para agentes Windows."
                    ),
                )
        if payload.windows_download_install_enabled is not None:
            previous_download_install = settings_service.get_windows_download_install_enabled()
            settings_service.set_windows_download_install_enabled(payload.windows_download_install_enabled)
            if payload.windows_download_install_enabled != previous_download_install:
                settings_service.record_operational_event(
                    "windows_download_install_updated",
                    current_user.username,
                    (
                        "Habilitou StartDownload e StartInstall controlados para agentes Windows."
                        if payload.windows_download_install_enabled
                        else "Desabilitou StartDownload e StartInstall controlados para agentes Windows."
                    ),
                )
        if payload.windows_command_timeout_seconds is not None:
            settings_service.set_windows_command_timeout_seconds(payload.windows_command_timeout_seconds)
            if payload.windows_command_timeout_seconds != previous_windows_timeout:
                settings_service.record_operational_event(
                    "windows_command_timeout_updated",
                    current_user.username,
                    f"Atualizou o timeout operacional do agente Windows para {payload.windows_command_timeout_seconds}s.",
                )
        if payload.windows_reboot_policy is not None:
            previous_windows_reboot_policy = settings_service.get_windows_reboot_policy()
            settings_service.set_windows_reboot_policy(payload.windows_reboot_policy)
            if payload.windows_reboot_policy != previous_windows_reboot_policy:
                settings_service.record_operational_event(
                    "windows_reboot_policy_updated",
                    current_user.username,
                    f"Atualizou a politica de reboot Windows para {payload.windows_reboot_policy}.",
                )
        if payload.windows_reboot_grace_minutes is not None:
            previous_windows_reboot_grace = settings_service.get_windows_reboot_grace_minutes()
            settings_service.set_windows_reboot_grace_minutes(payload.windows_reboot_grace_minutes)
            if payload.windows_reboot_grace_minutes != previous_windows_reboot_grace:
                settings_service.record_operational_event(
                    "windows_reboot_policy_updated",
                    current_user.username,
                    f"Atualizou a janela de reboot Windows para {payload.windows_reboot_grace_minutes} minutos.",
                )

    machine_groups = MachineRepository(db).list_groups()
    return ExecutionModeSetting.model_validate(settings_service.build_execution_settings(machine_groups))


@router.put("/bootstrap-token", response_model=BootstrapSetting)
def update_bootstrap_token(
    payload: BootstrapTokenUpdate,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> BootstrapSetting:
    settings_service = SettingsService(db)
    previous_token = settings_service.get_agent_bootstrap_token()
    previous_server_url = settings_service.get_agent_install_server_url()
    token = settings_service.set_agent_bootstrap_token(payload.agent_bootstrap_token)
    server_url = settings_service.get_agent_install_server_url()
    if payload.agent_install_server_url is not None:
        server_url = settings_service.set_agent_install_server_url(payload.agent_install_server_url)
    if token != previous_token:
        settings_service.record_operational_event(
            "bootstrap_token_updated",
            current_user.username,
            "Atualizou o bootstrap token do agente.",
        )
    if server_url != previous_server_url:
        settings_service.record_operational_event(
            "install_server_url_updated",
            current_user.username,
            f"Atualizou a URL publica do servidor para {server_url}.",
        )
    return BootstrapSetting(
        agent_bootstrap_token=token,
        agent_install_server_url=server_url,
    )


@router.get("/events/export.csv")
def export_operational_events_csv(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Response:
    settings_service = SettingsService(db)
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["occurred_at", "severity", "event_type", "actor", "summary"])
    for event in settings_service.list_operational_events(limit=200):
        writer.writerow(
            [
                event["occurred_at"],
                event["severity"],
                event["event_type"],
                event["actor"],
                event["summary"],
            ]
        )

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="patch-manager-operational-events.csv"'},
    )
