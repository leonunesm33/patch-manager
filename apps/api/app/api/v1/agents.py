from base64 import b64encode
import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.api.deps import get_agent_identity, get_bootstrap_token, get_current_user, get_db
from app.core.security import hash_password
from app.models.agent_credential import AgentCredentialModel
from app.models.agent_command import AgentCommandModel
from app.models.agent_enrollment import AgentEnrollmentModel
from app.models.agent_inventory_snapshot import AgentInventorySnapshotModel
from app.models.execution_log import ExecutionLogModel
from app.models.machine import MachineModel
from app.repositories.agent_command_repository import AgentCommandRepository
from app.repositories.agent_credential_repository import AgentCredentialRepository
from app.repositories.agent_enrollment_repository import AgentEnrollmentRepository
from app.repositories.agent_inventory_snapshot_repository import AgentInventorySnapshotRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.patch_job_repository import PatchJobRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_repository import PatchRepository
from app.schemas.agent import (
    AgentCommandPollRequest,
    AgentCommandHistoryItem,
    AgentInventorySnapshotItem,
    AgentCommandResponse,
    AgentCommandResultRequest,
    AgentCheckInRequest,
    AgentEnrollmentRequest,
    AgentEnrollmentStatusResponse,
    AgentHeartbeatRequest,
    AgentInventoryRequest,
    AgentJobClaimRequest,
    AgentJobResponse,
    AgentJobResultRequest,
    ConnectedAgentResponse,
    PendingAgentEnrollmentResponse,
    RejectedAgentEnrollmentResponse,
    RevokedAgentResponse,
    StoppedAgentResponse,
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


def _classify_job_failure(error_message: str | None) -> str | None:
    if not error_message:
        return None

    normalized = error_message.lower()
    if "real apply is disabled" in normalized:
        return "guardrail_real_apply_disabled"
    if "did not pass safety validation" in normalized:
        return "guardrail_invalid_package_name"
    if "is not allowed by local guardrails" in normalized:
        return "guardrail_package_not_allowed"
    if "is not currently upgradable" in normalized:
        return "guardrail_not_upgradable"
    if "does not have a security-tagged candidate" in normalized:
        return "guardrail_security_only_blocked"
    if "windows apply path is disabled" in normalized:
        return "guardrail_windows_apply_disabled"
    return "execution_error"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[5]


def _read_agent_linux_file(relative_path: str) -> str:
    return (_repo_root() / "apps" / "agent-linux" / relative_path).read_text(encoding="utf-8")


def _read_agent_windows_file(relative_path: str) -> str:
    return (_repo_root() / "apps" / "agent-windows" / relative_path).read_text(encoding="utf-8")


def _collect_agent_windows_payloads(subdir: str) -> list[tuple[str, str]]:
    root = _repo_root() / "apps" / "agent-windows" / subdir
    if not root.exists() or not root.is_dir():
        return []

    payloads: list[tuple[str, str]] = []
    for file_path in sorted(root.rglob("*")):
        if not file_path.is_file():
            continue
        relative_path = file_path.relative_to((_repo_root() / "apps" / "agent-windows")).as_posix()
        encoded = b64encode(file_path.read_bytes()).decode("ascii")
        payloads.append((relative_path, encoded))
    return payloads


def _build_linux_installer_script(server_url: str, bootstrap_token: str) -> str:
    files_to_write = {
        "agent/config.py": _read_agent_linux_file("agent/config.py"),
        "agent/logger.py": _read_agent_linux_file("agent/logger.py"),
        "agent/api_client.py": _read_agent_linux_file("agent/api_client.py"),
        "agent/inventory.py": _read_agent_linux_file("agent/inventory.py"),
        "agent/executor.py": _read_agent_linux_file("agent/executor.py"),
        "agent/main.py": _read_agent_linux_file("agent/main.py"),
        "deploy/patch-manager-agent-linux.service": _read_agent_linux_file(
            "deploy/patch-manager-agent-linux.service"
        ),
    }

    file_blocks = []
    for relative_path, content in files_to_write.items():
        file_blocks.append(
            "\n".join(
                [
                    f"mkdir -p \"${{INSTALL_ROOT}}/{Path(relative_path).parent.as_posix()}\"",
                    f"cat > \"${{INSTALL_ROOT}}/{relative_path}\" <<'EOF_{relative_path.replace('/', '_').replace('.', '_')}'",
                    content.rstrip(),
                    f"EOF_{relative_path.replace('/', '_').replace('.', '_')}",
                ]
            )
        )

    joined_blocks = "\n\n".join(file_blocks)
    return f"""#!/usr/bin/env bash
set -euo pipefail

SERVER_URL="{server_url.rstrip('/')}"
BOOTSTRAP_TOKEN="{bootstrap_token}"
INSTALL_ROOT="/opt/patch-manager/agent-linux"
ENV_TARGET="/etc/patch-manager/agent-linux.env"
SERVICE_NAME="patch-manager-agent-linux.service"
SERVICE_TARGET="/etc/systemd/system/${{SERVICE_NAME}}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found."
  exit 1
fi

HOSTNAME_VALUE="$(hostname -s 2>/dev/null || hostname)"
AGENT_ID="linux-$(echo "${{HOSTNAME_VALUE}}" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
AGENT_ID="${{AGENT_ID%-}}"

sudo mkdir -p "${{INSTALL_ROOT}}" /etc/patch-manager /var/log/patch-manager

{joined_blocks}

if ! id patchmanager >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin patchmanager
fi

sudo tee "${{ENV_TARGET}}" >/dev/null <<EOF
PATCH_MANAGER_API=${{SERVER_URL}}/api/v1/agents
PATCH_MANAGER_AGENT_KEY=
PATCH_MANAGER_AGENT_ID=${{AGENT_ID}}
PATCH_MANAGER_BOOTSTRAP_TOKEN=${{BOOTSTRAP_TOKEN}}
PATCH_MANAGER_AGENT_VERSION=0.2.0
PATCH_MANAGER_EXECUTION_MODE=dry-run
PATCH_MANAGER_ENABLE_REAL_APPLY=false
PATCH_MANAGER_ALLOW_SECURITY_ONLY=false
PATCH_MANAGER_ALLOWED_PACKAGE_PATTERNS=
PATCH_MANAGER_APT_APPLY_TIMEOUT=900
PATCH_MANAGER_HEARTBEAT_INTERVAL=10
PATCH_MANAGER_IDLE_SLEEP=5
PATCH_MANAGER_INVENTORY_INTERVAL=60
PATCH_MANAGER_FAILURE_BACKOFF=10
PATCH_MANAGER_REQUEST_TIMEOUT=10
PATCH_MANAGER_LOG_LEVEL=INFO
PATCH_MANAGER_LOG_TO_STDOUT=true
PATCH_MANAGER_LOG_FILE=/var/log/patch-manager/agent-linux.log
EOF

sudo chown root:patchmanager "${{ENV_TARGET}}"
sudo chmod 660 "${{ENV_TARGET}}"
sudo install -m 644 "${{INSTALL_ROOT}}/deploy/patch-manager-agent-linux.service" "${{SERVICE_TARGET}}"
sudo chown -R patchmanager:patchmanager "${{INSTALL_ROOT}}" /var/log/patch-manager
sudo systemctl daemon-reload
sudo systemctl enable --now "${{SERVICE_NAME}}"

echo "Instalacao concluida."
echo "Agent ID: ${{AGENT_ID}}"
echo "Aguardando aprovacao no painel do Patch Manager."
echo "Logs:"
echo "  sudo journalctl -u ${{SERVICE_NAME}} -f"
"""


def _build_linux_upgrade_script(server_url: str) -> str:
    files_to_write = {
        "agent/config.py": _read_agent_linux_file("agent/config.py"),
        "agent/logger.py": _read_agent_linux_file("agent/logger.py"),
        "agent/api_client.py": _read_agent_linux_file("agent/api_client.py"),
        "agent/inventory.py": _read_agent_linux_file("agent/inventory.py"),
        "agent/executor.py": _read_agent_linux_file("agent/executor.py"),
        "agent/main.py": _read_agent_linux_file("agent/main.py"),
        "deploy/patch-manager-agent-linux.service": _read_agent_linux_file(
            "deploy/patch-manager-agent-linux.service"
        ),
    }

    file_blocks = []
    for relative_path, content in files_to_write.items():
        file_blocks.append(
            "\n".join(
                [
                    f"mkdir -p \"${{INSTALL_ROOT}}/{Path(relative_path).parent.as_posix()}\"",
                    f"cat > \"${{INSTALL_ROOT}}/{relative_path}\" <<'EOF_{relative_path.replace('/', '_').replace('.', '_')}'",
                    content.rstrip(),
                    f"EOF_{relative_path.replace('/', '_').replace('.', '_')}",
                ]
            )
        )

    joined_blocks = "\n\n".join(file_blocks)
    return f"""#!/usr/bin/env bash
set -euo pipefail

SERVER_URL="{server_url.rstrip('/')}"
INSTALL_ROOT="/opt/patch-manager/agent-linux"
ENV_TARGET="/etc/patch-manager/agent-linux.env"
SERVICE_NAME="patch-manager-agent-linux.service"
SERVICE_TARGET="/etc/systemd/system/${{SERVICE_NAME}}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: python3 not found."
  exit 1
fi

if [[ ! -f "${{ENV_TARGET}}" ]]; then
  echo "Error: ${{ENV_TARGET}} not found. Use the install flow first."
  exit 1
fi

sudo mkdir -p "${{INSTALL_ROOT}}" /var/log/patch-manager

{joined_blocks}

if ! id patchmanager >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin patchmanager
fi

CURRENT_API="$(grep '^PATCH_MANAGER_API=' "${{ENV_TARGET}}" | head -n1 | cut -d'=' -f2- || true)"
if [[ -z "${{CURRENT_API}}" ]]; then
  sudo tee -a "${{ENV_TARGET}}" >/dev/null <<EOF
PATCH_MANAGER_API=${{SERVER_URL}}/api/v1/agents
EOF
fi

for REQUIRED_KEY in \
  PATCH_MANAGER_ENABLE_REAL_APPLY=false \
  PATCH_MANAGER_ALLOW_SECURITY_ONLY=false \
  PATCH_MANAGER_ALLOWED_PACKAGE_PATTERNS= \
  PATCH_MANAGER_APT_APPLY_TIMEOUT=900; do
  KEY_NAME="${{REQUIRED_KEY%%=*}}"
  if ! grep -q "^${{KEY_NAME}}=" "${{ENV_TARGET}}"; then
    sudo tee -a "${{ENV_TARGET}}" >/dev/null <<EOF
${{REQUIRED_KEY}}
EOF
  fi
done

sudo chown root:patchmanager "${{ENV_TARGET}}"
sudo chmod 660 "${{ENV_TARGET}}"
sudo install -m 644 "${{INSTALL_ROOT}}/deploy/patch-manager-agent-linux.service" "${{SERVICE_TARGET}}"
sudo chown -R patchmanager:patchmanager "${{INSTALL_ROOT}}" /var/log/patch-manager
sudo systemctl daemon-reload
sudo systemctl restart "${{SERVICE_NAME}}"

echo "Atualizacao concluida."
echo "Servico reiniciado: ${{SERVICE_NAME}}"
echo "Logs:"
echo "  sudo journalctl -u ${{SERVICE_NAME}} -f"
"""


def _build_windows_installer_script(server_url: str, bootstrap_token: str) -> str:
    files_to_write = {
        "agent/config.py": _read_agent_windows_file("agent/config.py"),
        "agent/logger.py": _read_agent_windows_file("agent/logger.py"),
        "agent/api_client.py": _read_agent_windows_file("agent/api_client.py"),
        "agent/inventory.py": _read_agent_windows_file("agent/inventory.py"),
        "agent/executor.py": _read_agent_windows_file("agent/executor.py"),
        "agent/main.py": _read_agent_windows_file("agent/main.py"),
        "agent/run-agent.ps1": _read_agent_windows_file("agent/run-agent.ps1"),
    }

    file_blocks = []
    for relative_path, content in files_to_write.items():
        file_blocks.append(
            "\n".join(
                [
                    f'$target = Join-Path $InstallRoot "{relative_path.replace("/", "\\")}"',
                    "$null = New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($target))",
                    f"@'\n{content.rstrip()}\n'@ | Set-Content -Path $target -Encoding UTF8",
                ]
            )
        )

    joined_blocks = "\n\n".join(file_blocks)
    payload_blocks = []
    for relative_path, encoded in _collect_agent_windows_payloads("runtime") + _collect_agent_windows_payloads("dist"):
        payload_blocks.append(
            "\n".join(
                [
                    f'$target = Join-Path $InstallRoot "{relative_path.replace("/", "\\")}"',
                    "$null = New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($target))",
                    f'[System.IO.File]::WriteAllBytes($target, [System.Convert]::FromBase64String("{encoded}"))',
                ]
            )
        )
    joined_payload_blocks = "\n\n".join(payload_blocks)
    return f"""param()
$ErrorActionPreference = 'Stop'

$ServerUrl = "{server_url.rstrip('/')}"
$BootstrapToken = "{bootstrap_token}"
$InstallRoot = "C:\\ProgramData\\PatchManager\\agent-windows"
$EnvTarget = "C:\\ProgramData\\PatchManager\\agent-windows.env"
$TaskName = "PatchManagerAgentWindows"
$LogFile = "C:\\ProgramData\\PatchManager\\agent-windows.log"
$AgentId = "windows-$($env:COMPUTERNAME.ToLower() -replace '[^a-z0-9]+','-')"
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$PowerShellExecutable = Join-Path $env:SystemRoot "System32\\WindowsPowerShell\\v1.0\\powershell.exe"

function Test-IsAdministrator {{
  $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}}

$null = New-Item -ItemType Directory -Force -Path $InstallRoot
$null = New-Item -ItemType Directory -Force -Path "C:\\ProgramData\\PatchManager"

{joined_blocks}

{joined_payload_blocks}

@"
PATCH_MANAGER_API=$ServerUrl/api/v1/agents
PATCH_MANAGER_AGENT_ID=$AgentId
PATCH_MANAGER_AGENT_KEY=
PATCH_MANAGER_BOOTSTRAP_TOKEN=$BootstrapToken
PATCH_MANAGER_AGENT_VERSION=0.2.0
PATCH_MANAGER_EXECUTION_MODE=dry-run
PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=false
PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=false
PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT=60
PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=false
PATCH_MANAGER_WINDOWS_REBOOT_COMMAND_TIMEOUT=30
PATCH_MANAGER_HEARTBEAT_INTERVAL=10
PATCH_MANAGER_IDLE_SLEEP=5
PATCH_MANAGER_INVENTORY_INTERVAL=60
PATCH_MANAGER_FAILURE_BACKOFF=10
PATCH_MANAGER_REQUEST_TIMEOUT=10
PATCH_MANAGER_LOG_LEVEL=INFO
PATCH_MANAGER_LOG_TO_STDOUT=true
PATCH_MANAGER_LOG_FILE=$LogFile
"@ | Set-Content -Path $EnvTarget -Encoding UTF8

$action = New-ScheduledTaskAction -Execute $PowerShellExecutable -Argument "-ExecutionPolicy Bypass -File agent\\run-agent.ps1" -WorkingDirectory $InstallRoot
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

if (Test-IsAdministrator) {{
  $trigger = New-ScheduledTaskTrigger -AtStartup
  $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -RunLevel Highest -LogonType ServiceAccount
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
  Write-Host "Task registrada para SYSTEM com inicio no boot."
}} else {{
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $CurrentUser
  Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -User $CurrentUser -Force | Out-Null
  Write-Host "PowerShell sem privilegio administrativo detectado."
  Write-Host "Task registrada para o usuario atual ($CurrentUser) com inicio no logon."
}}

Start-ScheduledTask -TaskName $TaskName

Write-Host "Instalacao concluida."
Write-Host "Agent ID: $AgentId"
Write-Host "Launcher da task: agent\\run-agent.ps1"
Write-Host "Aguardando aprovacao no painel do Patch Manager."
Write-Host "Arquivo de ambiente: $EnvTarget"
Write-Host "Task agendada: $TaskName"
"""


def _build_windows_upgrade_script(server_url: str) -> str:
    files_to_write = {
        "agent/config.py": _read_agent_windows_file("agent/config.py"),
        "agent/logger.py": _read_agent_windows_file("agent/logger.py"),
        "agent/api_client.py": _read_agent_windows_file("agent/api_client.py"),
        "agent/inventory.py": _read_agent_windows_file("agent/inventory.py"),
        "agent/executor.py": _read_agent_windows_file("agent/executor.py"),
        "agent/main.py": _read_agent_windows_file("agent/main.py"),
        "agent/run-agent.ps1": _read_agent_windows_file("agent/run-agent.ps1"),
    }

    file_blocks = []
    for relative_path, content in files_to_write.items():
        file_blocks.append(
            "\n".join(
                [
                    f'$target = Join-Path $InstallRoot "{relative_path.replace("/", "\\")}"',
                    "$null = New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($target))",
                    f"@'\n{content.rstrip()}\n'@ | Set-Content -Path $target -Encoding UTF8",
                ]
            )
        )

    joined_blocks = "\n\n".join(file_blocks)
    payload_blocks = []
    for relative_path, encoded in _collect_agent_windows_payloads("runtime") + _collect_agent_windows_payloads("dist"):
        payload_blocks.append(
            "\n".join(
                [
                    f'$target = Join-Path $InstallRoot "{relative_path.replace("/", "\\")}"',
                    "$null = New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($target))",
                    f'[System.IO.File]::WriteAllBytes($target, [System.Convert]::FromBase64String("{encoded}"))',
                ]
            )
        )
    joined_payload_blocks = "\n\n".join(payload_blocks)
    return f"""param()
$ErrorActionPreference = 'Stop'

$ServerUrl = "{server_url.rstrip('/')}"
$InstallRoot = "C:\\ProgramData\\PatchManager\\agent-windows"
$EnvTarget = "C:\\ProgramData\\PatchManager\\agent-windows.env"
$TaskName = "PatchManagerAgentWindows"
$PowerShellExecutable = Join-Path $env:SystemRoot "System32\\WindowsPowerShell\\v1.0\\powershell.exe"

if (-not (Test-Path $InstallRoot)) {{
  throw "InstallRoot nao encontrado. Rode a instalacao inicial primeiro."
}}

try {{
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
}} catch {{}}

Start-Sleep -Seconds 2

Get-Process -Name "PatchManagerAgentWindows" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

Get-CimInstance Win32_Process -Filter "Name = 'powershell.exe'" -ErrorAction SilentlyContinue |
  Where-Object {{
    $_.CommandLine -like "*PatchManagerAgentWindows*" -or
    $_.CommandLine -like "*run-agent.ps1*"
  }} |
  ForEach-Object {{
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
  }}

Start-Sleep -Seconds 1

{joined_blocks}

{joined_payload_blocks}

if (-not (Test-Path $EnvTarget)) {{
@"
PATCH_MANAGER_API=$ServerUrl/api/v1/agents
"@ | Set-Content -Path $EnvTarget -Encoding UTF8
}}

$existing = Get-Content $EnvTarget -Raw
if ($existing -notmatch 'PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=false"
}}
if ($existing -notmatch 'PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=false"
}}
if ($existing -notmatch 'PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT=60"
}}
if ($existing -notmatch 'PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=false"
}}
if ($existing -notmatch 'PATCH_MANAGER_WINDOWS_REBOOT_COMMAND_TIMEOUT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_WINDOWS_REBOOT_COMMAND_TIMEOUT=30"
}}
if ($existing -notmatch 'PATCH_MANAGER_LOG_LEVEL=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_LOG_LEVEL=INFO"
}}
if ($existing -notmatch 'PATCH_MANAGER_LOG_TO_STDOUT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_LOG_TO_STDOUT=true"
}}
if ($existing -notmatch 'PATCH_MANAGER_LOG_FILE=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_LOG_FILE=C:\\ProgramData\\PatchManager\\agent-windows.log"
}}

$action = New-ScheduledTaskAction -Execute $PowerShellExecutable -Argument "-ExecutionPolicy Bypass -File agent\\run-agent.ps1" -WorkingDirectory $InstallRoot
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Set-ScheduledTask -TaskName $TaskName -Action $action -Settings $settings | Out-Null

try {{
  Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
}} catch {{}}
try {{
  Start-ScheduledTask -TaskName $TaskName
}} catch {{
  Write-Host "Nao foi possivel iniciar a task automaticamente. Tente iniciar manualmente ou faca logoff/logon."
}}

Write-Host "Atualizacao concluida."
Write-Host "Launcher da task: agent\\run-agent.ps1"
Write-Host "Task reiniciada: $TaskName"
"""


@router.get("/install/linux.sh", response_class=PlainTextResponse)
def download_linux_installer(
    server_url: str,
    bootstrap_token: str,
) -> str:
    return _build_linux_installer_script(server_url, bootstrap_token)


@router.get("/install/linux-upgrade.sh", response_class=PlainTextResponse)
def download_linux_upgrade_script(server_url: str) -> str:
    return _build_linux_upgrade_script(server_url)


@router.get("/install/windows.ps1", response_class=PlainTextResponse)
def download_windows_installer(
    server_url: str,
    bootstrap_token: str,
) -> str:
    return _build_windows_installer_script(server_url, bootstrap_token)


@router.get("/install/windows-upgrade.ps1", response_class=PlainTextResponse)
def download_windows_upgrade_script(server_url: str) -> str:
    return _build_windows_upgrade_script(server_url)


@router.post("/enroll", response_model=AgentEnrollmentStatusResponse)
def enroll_agent(
    payload: AgentEnrollmentRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[str, Depends(get_bootstrap_token)],
) -> AgentEnrollmentStatusResponse:
    repository = AgentEnrollmentRepository(db)
    enrollment = repository.upsert_request(
        agent_id=payload.agent_id,
        platform=payload.platform,
        hostname=payload.hostname,
        primary_ip=payload.primary_ip,
        os_name=payload.os_name,
        os_version=payload.os_version,
        kernel_version=payload.kernel_version,
        agent_version=payload.agent_version,
    )
    if enrollment.status == "approved" and enrollment.issued_key:
        issued_key = enrollment.issued_key
        repository.mark_active(enrollment)
        return AgentEnrollmentStatusResponse(
            status="approved",
            agent_id=enrollment.agent_id,
            agent_key=issued_key,
            poll_interval_seconds=5,
        )
    return AgentEnrollmentStatusResponse(
        status=enrollment.status,
        agent_id=enrollment.agent_id,
        poll_interval_seconds=15,
    )


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
    return [
        PatchJobItem.model_validate(job).model_copy(
            update={"failure_reason": _classify_job_failure(job.error_message)}
        )
        for job in repository.list_recent()
    ]


@router.get("/connected", response_model=list[ConnectedAgentResponse])
def list_connected_agents(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[ConnectedAgentResponse]:
    return agent_registry_service.list_connected()


@router.get("/revoked", response_model=list[RevokedAgentResponse])
def list_revoked_agents(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[RevokedAgentResponse]:
    credential_repository = AgentCredentialRepository(db)
    enrollment_repository = AgentEnrollmentRepository(db)
    items: list[RevokedAgentResponse] = []
    for credential in credential_repository.list_inactive():
        enrollment = enrollment_repository.get_by_agent_id(credential.agent_id)
        items.append(
            RevokedAgentResponse(
                agent_id=credential.agent_id,
                platform=credential.platform,
                hostname=enrollment.hostname if enrollment else None,
                primary_ip=enrollment.primary_ip if enrollment else None,
                os_name=enrollment.os_name if enrollment else None,
                os_version=enrollment.os_version if enrollment else None,
                kernel_version=enrollment.kernel_version if enrollment else None,
                agent_version=enrollment.agent_version if enrollment else None,
                last_known_at=(
                    enrollment.approved_at
                    if enrollment and enrollment.approved_at is not None
                    else enrollment.requested_at if enrollment else credential.created_at
                ),
            )
        )
    return items


@router.get("/stopped", response_model=list[StoppedAgentResponse])
def list_stopped_agents(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[StoppedAgentResponse]:
    credential_repository = AgentCredentialRepository(db)
    enrollment_repository = AgentEnrollmentRepository(db)
    snapshot_repository = AgentInventorySnapshotRepository(db)

    snapshots = {item.agent_id: item for item in snapshot_repository.list_all()}
    items: list[StoppedAgentResponse] = []

    for credential in credential_repository.list_all():
        if not credential.is_active:
            continue
        if agent_registry_service.is_connected(credential.agent_id):
            continue

        enrollment = enrollment_repository.get_by_agent_id(credential.agent_id)
        if enrollment is not None and enrollment.status in {"pending", "rejected"}:
            continue

        snapshot = snapshots.get(credential.agent_id)
        items.append(
            StoppedAgentResponse(
                agent_id=credential.agent_id,
                platform=credential.platform,
                hostname=snapshot.hostname if snapshot else enrollment.hostname if enrollment else None,
                primary_ip=snapshot.primary_ip if snapshot else enrollment.primary_ip if enrollment else None,
                os_name=snapshot.os_name if snapshot else enrollment.os_name if enrollment else None,
                os_version=snapshot.os_version if snapshot else enrollment.os_version if enrollment else None,
                kernel_version=snapshot.kernel_version if snapshot else enrollment.kernel_version if enrollment else None,
                agent_version=snapshot.agent_version if snapshot else enrollment.agent_version if enrollment else None,
                execution_mode=snapshot.execution_mode if snapshot else None,
                package_manager=snapshot.package_manager if snapshot else None,
                installed_packages=snapshot.installed_packages if snapshot else None,
                upgradable_packages=snapshot.upgradable_packages if snapshot else None,
                reboot_required=snapshot.reboot_required if snapshot else None,
                installed_update_count=snapshot.installed_update_count if snapshot else None,
                pending_update_summary=snapshot.pending_update_summary if snapshot else None,
                windows_update_source=snapshot.windows_update_source if snapshot else None,
                last_seen_at=(
                    snapshot.updated_at
                    if snapshot is not None
                    else enrollment.approved_at if enrollment and enrollment.approved_at is not None
                    else enrollment.requested_at if enrollment else credential.created_at
                ),
            )
        )

    return sorted(
        items,
        key=lambda item: item.last_seen_at.timestamp() if item.last_seen_at is not None else 0,
        reverse=True,
    )


@router.post("/revoked/{agent_id}/requeue", response_model=PendingAgentEnrollmentResponse)
def requeue_revoked_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> PendingAgentEnrollmentResponse:
    credential_repository = AgentCredentialRepository(db)
    enrollment_repository = AgentEnrollmentRepository(db)
    settings_service = SettingsService(db)

    credential = credential_repository.get_by_agent_id(agent_id)
    if credential is None or credential.is_active:
        raise HTTPException(status_code=404, detail="Revoked agent not found")

    enrollment = enrollment_repository.get_by_agent_id(agent_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment history not found")

    pending = enrollment_repository.reopen_pending(enrollment)
    settings_service.record_operational_event(
        "agent_requeue_from_revoked",
        current_user.username,
        f"Reabriu a aprovacao do agente revogado {pending.agent_id} ({pending.hostname}).",
    )
    return PendingAgentEnrollmentResponse.model_validate(pending)


@router.post("/connected/{agent_id}/revoke")
def revoke_connected_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> dict[str, str]:
    credential_repository = AgentCredentialRepository(db)
    settings_service = SettingsService(db)
    credential = credential_repository.get_by_agent_id(agent_id)
    if credential is None:
        raise HTTPException(status_code=404, detail="Agent credential not found")

    credential.is_active = False
    credential_repository.update(credential)
    agent_registry_service.disconnect(agent_id)
    settings_service.record_operational_event(
        "agent_revoked_manual",
        current_user.username,
        f"Revogou manualmente o agente {agent_id}.",
    )
    return {"status": "revoked"}


@router.post("/connected/{agent_id}/reintegrate")
def reintegrate_connected_agent(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> PendingAgentEnrollmentResponse:
    connected_agent = agent_registry_service.get_connected(agent_id)
    if connected_agent is None:
        raise HTTPException(status_code=404, detail="Connected agent not found")

    credential_repository = AgentCredentialRepository(db)
    enrollment_repository = AgentEnrollmentRepository(db)
    settings_service = SettingsService(db)

    credential = credential_repository.get_by_agent_id(agent_id)
    if credential is not None:
        credential.is_active = False
        credential_repository.update(credential)

    enrollment = enrollment_repository.upsert_request(
        agent_id=connected_agent.agent_id,
        platform=connected_agent.platform,
        hostname=connected_agent.hostname,
        primary_ip=connected_agent.primary_ip or "",
        os_name=connected_agent.os_name,
        os_version=connected_agent.os_version,
        kernel_version=connected_agent.kernel_version,
        agent_version=connected_agent.agent_version,
    )
    agent_registry_service.disconnect(agent_id)
    settings_service.record_operational_event(
        "agent_reintegrated_manual",
        current_user.username,
        f"Forcou reintegracao do agente {connected_agent.agent_id} ({connected_agent.hostname}).",
    )
    return PendingAgentEnrollmentResponse.model_validate(enrollment)


@router.post("/connected/{agent_id}/reboot")
def request_connected_agent_reboot(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> dict[str, str]:
    connected_agent = agent_registry_service.get_connected(agent_id)
    if connected_agent is None:
        raise HTTPException(status_code=404, detail="Connected agent not found")
    if connected_agent.platform.lower() != "linux":
        raise HTTPException(status_code=400, detail="Manual reboot is available only for Linux agents")

    AgentCommandRepository(db).add(
        AgentCommandModel(
            id=f"cmd-{secrets.token_hex(8)}",
            agent_id=agent_id,
            command_type="reboot_now",
            status="pending",
            requested_by=current_user.username,
            payload_json=json.dumps(
                {"requested_by": current_user.username, "reason": "manual_console_action"}
            ),
        )
    )
    SettingsService(db).record_operational_event(
        "linux_manual_reboot_requested",
        current_user.username,
        f"Solicitou reboot manual para o agente {agent_id}.",
    )
    return {"status": "queued"}


@router.get("/commands/recent", response_model=list[AgentCommandHistoryItem])
def list_recent_agent_commands(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[AgentCommandHistoryItem]:
    repository = AgentCommandRepository(db)
    return [
        AgentCommandHistoryItem(
            id=item.id,
            agent_id=item.agent_id,
            command_type=item.command_type,
            status=item.status,
            requested_by=item.requested_by,
            message=item.message,
            created_at=item.created_at,
            claimed_at=item.claimed_at,
            finished_at=item.finished_at,
        )
        for item in repository.list_recent()
    ]


@router.get("/inventory-snapshots", response_model=list[AgentInventorySnapshotItem])
def list_agent_inventory_snapshots(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[AgentInventorySnapshotItem]:
    repository = AgentInventorySnapshotRepository(db)
    return [AgentInventorySnapshotItem.model_validate(item) for item in repository.list_recent()]


@router.get("/enrollments/pending", response_model=list[PendingAgentEnrollmentResponse])
def list_pending_enrollments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[PendingAgentEnrollmentResponse]:
    repository = AgentEnrollmentRepository(db)
    return [PendingAgentEnrollmentResponse.model_validate(item) for item in repository.list_pending()]


@router.get("/enrollments/rejected", response_model=list[RejectedAgentEnrollmentResponse])
def list_rejected_enrollments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[RejectedAgentEnrollmentResponse]:
    repository = AgentEnrollmentRepository(db)
    return [RejectedAgentEnrollmentResponse.model_validate(item) for item in repository.list_rejected()]


@router.post("/enrollments/{agent_id}/approve", response_model=PendingAgentEnrollmentResponse)
def approve_pending_enrollment(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> PendingAgentEnrollmentResponse:
    enrollment_repository = AgentEnrollmentRepository(db)
    credential_repository = AgentCredentialRepository(db)
    settings_service = SettingsService(db)
    enrollment = enrollment_repository.get_by_agent_id(agent_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    issued_key = secrets.token_urlsafe(24)
    credential = credential_repository.get_by_agent_id(agent_id)
    if credential is None:
        credential_repository.add(
            AgentCredentialModel(
                agent_id=agent_id,
                platform=enrollment.platform,
                description=f"Approved enrollment for {enrollment.hostname}",
                key_hash=hash_password(issued_key),
                is_active=True,
            )
        )
    else:
        credential.platform = enrollment.platform
        credential.description = f"Approved enrollment for {enrollment.hostname}"
        credential.key_hash = hash_password(issued_key)
        credential.is_active = True
        db.add(credential)
        db.commit()
        db.refresh(credential)

    approved = enrollment_repository.approve(enrollment, issued_key)
    settings_service.record_operational_event(
        "agent_enrollment_approved",
        current_user.username,
        f"Aprovou o agente {approved.agent_id} ({approved.hostname}).",
    )
    return PendingAgentEnrollmentResponse.model_validate(approved)


@router.post("/enrollments/{agent_id}/reject", response_model=PendingAgentEnrollmentResponse)
def reject_pending_enrollment(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> PendingAgentEnrollmentResponse:
    enrollment_repository = AgentEnrollmentRepository(db)
    settings_service = SettingsService(db)
    enrollment = enrollment_repository.get_by_agent_id(agent_id)
    if enrollment is None:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    rejected = enrollment_repository.reject(enrollment)
    settings_service.record_operational_event(
        "agent_enrollment_rejected",
        current_user.username,
        f"Rejeitou o agente {rejected.agent_id} ({rejected.hostname}).",
    )
    return PendingAgentEnrollmentResponse.model_validate(rejected)


@router.post("/enrollments/{agent_id}/reopen", response_model=PendingAgentEnrollmentResponse)
def reopen_rejected_enrollment(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> PendingAgentEnrollmentResponse:
    enrollment_repository = AgentEnrollmentRepository(db)
    settings_service = SettingsService(db)
    enrollment = enrollment_repository.get_by_agent_id(agent_id)
    if enrollment is None or enrollment.status != "rejected":
        raise HTTPException(status_code=404, detail="Rejected enrollment not found")

    reopened = enrollment_repository.reopen_pending(enrollment)
    settings_service.record_operational_event(
        "agent_requeue_from_rejected",
        current_user.username,
        f"Reabriu a aprovacao do agente rejeitado {reopened.agent_id} ({reopened.hostname}).",
    )
    return PendingAgentEnrollmentResponse.model_validate(reopened)


@router.post("/check-in")
def check_in_agent(
    payload: AgentCheckInRequest,
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> dict[str, str]:
    if payload.agent_id != agent.agent_id:
        return {"status": "invalid-agent"}
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
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> dict[str, str]:
    if payload.agent_id != agent.agent_id:
        return {"status": "invalid-agent"}
    agent_registry_service.update_inventory(
        payload.agent_id,
        payload.platform,
        payload.hostname,
        payload.primary_ip,
        payload.package_manager,
        payload.installed_packages,
        payload.upgradable_packages,
        payload.reboot_required,
        payload.installed_update_count,
        payload.pending_update_summary,
        payload.windows_update_source,
        payload.os_name,
        payload.os_version,
        payload.kernel_version,
        payload.agent_version,
        payload.execution_mode,
    )
    AgentInventorySnapshotRepository(db).upsert(
        AgentInventorySnapshotModel(
            agent_id=payload.agent_id,
            platform=payload.platform,
            hostname=payload.hostname,
            primary_ip=payload.primary_ip,
            package_manager=payload.package_manager,
            installed_packages=payload.installed_packages,
            upgradable_packages=payload.upgradable_packages,
            reboot_required=payload.reboot_required,
            installed_update_count=payload.installed_update_count,
            pending_update_summary=payload.pending_update_summary,
            windows_update_source=payload.windows_update_source,
            os_name=payload.os_name,
            os_version=payload.os_version,
            kernel_version=payload.kernel_version,
            agent_version=payload.agent_version,
            execution_mode=payload.execution_mode,
        )
    )

    machine_repository = MachineRepository(db)
    managed_machine_id = f"agent-{payload.agent_id}"
    machine = machine_repository.get_by_id(managed_machine_id)
    risk = "critical" if payload.upgradable_packages >= 10 else "important"
    if payload.upgradable_packages == 0:
        risk = "optional"

    if machine is None:
        machine_repository.add(
            MachineModel(
                id=managed_machine_id,
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
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> dict[str, str]:
    if payload.agent_id != agent.agent_id:
        return {"status": "invalid-agent"}
    agent_registry_service.heartbeat(payload.agent_id, payload.platform, payload.hostname)
    return {"status": "ok"}


@router.post("/claim-job", response_model=AgentJobResponse | None)
def claim_job_for_agent(
    payload: AgentJobClaimRequest,
    db: Annotated[Session, Depends(get_db)],
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> AgentJobResponse | None:
    if payload.agent_id != agent.agent_id:
        return None
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
        real_apply_enabled=settings_service.get_linux_real_apply_enabled(),
        allow_security_only=settings_service.get_linux_allow_security_only(),
        allowed_package_patterns=settings_service.get_linux_allowed_package_patterns(),
        apt_apply_timeout_seconds=settings_service.get_linux_apt_apply_timeout_seconds(),
        windows_scan_apply_enabled=settings_service.get_windows_scan_apply_enabled(),
        windows_download_install_enabled=settings_service.get_windows_download_install_enabled(),
        windows_command_timeout_seconds=settings_service.get_windows_command_timeout_seconds(),
        reboot_policy=(
            settings_service.get_linux_reboot_policy()
            if payload.platform.lower() == "linux"
            else settings_service.get_windows_reboot_policy()
        ),
        reboot_grace_minutes=(
            settings_service.get_linux_reboot_grace_minutes()
            if payload.platform.lower() == "linux"
            else settings_service.get_windows_reboot_grace_minutes()
        ),
        status=job.status,
        claimed_by_agent=job.claimed_by_agent,
        claimed_at=job.claimed_at,
    )


@router.post("/commands/next", response_model=AgentCommandResponse | None)
def poll_next_command(
    payload: AgentCommandPollRequest,
    db: Annotated[Session, Depends(get_db)],
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> AgentCommandResponse | None:
    if payload.agent_id != agent.agent_id:
        return None
    command = AgentCommandRepository(db).claim_next_for_agent(payload.agent_id)
    if command is None:
        return None
    payload_data: dict[str, str | int | bool | None] = {}
    if command.payload_json:
        try:
            parsed = json.loads(command.payload_json)
            if isinstance(parsed, dict):
                payload_data = parsed
        except json.JSONDecodeError:
            payload_data = {}
    return AgentCommandResponse(
        id=command.id,
        command_type=command.command_type,
        target_agent_id=command.agent_id,
        payload=payload_data,
        created_at=command.created_at,
    )


@router.post("/commands/{command_id}/result")
def submit_command_result(
    command_id: str,
    payload: AgentCommandResultRequest,
    db: Annotated[Session, Depends(get_db)],
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> dict[str, str]:
    if payload.agent_id != agent.agent_id:
        raise HTTPException(status_code=403, detail="Invalid agent for command result")

    settings_service = SettingsService(db)
    command_repository = AgentCommandRepository(db)
    command = command_repository.get_by_id(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")
    if command.agent_id != payload.agent_id:
        raise HTTPException(status_code=403, detail="Invalid agent for command result")

    normalized_result = payload.result.strip().lower()
    command_repository.complete(command, normalized_result, payload.message)
    if normalized_result == "applied":
        settings_service.record_operational_event(
            "linux_manual_reboot_completed",
            payload.agent_id,
            payload.message or f"Reboot manual aceito pelo agente {payload.agent_id}.",
        )
    else:
        settings_service.record_operational_event(
            "linux_manual_reboot_failed",
            payload.agent_id,
            payload.message or f"Falha ao executar reboot manual no agente {payload.agent_id}.",
        )
    return {"status": "acknowledged", "command_id": command_id}


@router.post("/jobs/{job_id}/result")
def submit_agent_job_result(
    job_id: str,
    payload: AgentJobResultRequest,
    db: Annotated[Session, Depends(get_db)],
    agent: Annotated[AgentCredentialModel, Depends(get_agent_identity)],
) -> dict[str, str]:
    if payload.agent_id != agent.agent_id:
        return {"status": "invalid-agent"}
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

    execution_mode = (payload.execution_mode or "").strip().lower()
    if job.platform.lower() == "linux" and execution_mode == "apply":
        settings_service = SettingsService(db)
        if result == "applied":
            settings_service.record_operational_event(
                "linux_apply_completed",
                payload.agent_id,
                f"Apply Linux concluido em {job.machine_name} para o patch {job.patch_id}.",
            )
            if payload.reboot_required:
                reboot_policy = settings_service.get_linux_reboot_policy()
                grace_minutes = settings_service.get_linux_reboot_grace_minutes()
                settings_service.record_operational_event(
                    "linux_reboot_required",
                    payload.agent_id,
                    f"Host {job.machine_name} requer reboot apos apply do patch {job.patch_id}. Politica ativa: {reboot_policy} com janela de {grace_minutes} minutos.",
                )
                if payload.reboot_scheduled:
                    settings_service.record_operational_event(
                        "linux_reboot_scheduled",
                        payload.agent_id,
                        payload.reboot_message
                        or f"Reboot agendado para {job.machine_name} apos apply do patch {job.patch_id}.",
                    )
        else:
            summary = f"Apply Linux falhou em {job.machine_name} para o patch {job.patch_id}."
            if payload.error_message:
                summary = f"{summary} {payload.error_message}"
            settings_service.record_operational_event(
                "linux_apply_failed",
                payload.agent_id,
                summary,
            )
    elif job.platform.lower() == "windows" and execution_mode == "apply":
        settings_service = SettingsService(db)
        if result == "applied":
            settings_service.record_operational_event(
                "windows_apply_completed",
                payload.agent_id,
                f"Apply Windows concluido em {job.machine_name} para o patch {job.patch_id}.",
            )
            if payload.reboot_required:
                reboot_policy = settings_service.get_windows_reboot_policy()
                grace_minutes = settings_service.get_windows_reboot_grace_minutes()
                settings_service.record_operational_event(
                    "windows_reboot_required",
                    payload.agent_id,
                    f"Host {job.machine_name} requer reboot apos apply do patch {job.patch_id}. Politica ativa: {reboot_policy} com janela de {grace_minutes} minutos.",
                )
                if payload.reboot_scheduled:
                    settings_service.record_operational_event(
                        "windows_reboot_scheduled",
                        payload.agent_id,
                        payload.reboot_message
                        or f"Reboot agendado para {job.machine_name} apos apply do patch {job.patch_id}.",
                    )
        else:
            summary = f"Apply Windows falhou em {job.machine_name} para o patch {job.patch_id}."
            if payload.error_message:
                summary = f"{summary} {payload.error_message}"
            settings_service.record_operational_event(
                "windows_apply_failed",
                payload.agent_id,
                summary,
            )

    agent_registry_service.heartbeat(payload.agent_id, job.platform, payload.agent_id)
    return {"status": "ok"}
