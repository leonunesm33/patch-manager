import logging
from hashlib import sha1
import json
import re
import secrets
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import urlparse
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import (
    get_agent_identity,
    get_bootstrap_token,
    get_current_user,
    get_db,
    require_operator,
    require_viewer,
)
from app.core.security import hash_password
from app.models.agent_credential import AgentCredentialModel
from app.models.agent_command import AgentCommandModel
from app.models.agent_identity_history import AgentIdentityHistoryModel
from app.models.agent_enrollment import AgentEnrollmentModel
from app.models.agent_inventory_item import AgentInventoryItemModel
from app.models.agent_inventory_snapshot import AgentInventorySnapshotModel
from app.models.execution_log import ExecutionLogModel
from app.models.machine import MachineModel
from app.models.patch import PatchModel
from app.repositories.agent_command_repository import AgentCommandRepository
from app.repositories.agent_identity_history_repository import AgentIdentityHistoryRepository
from app.repositories.agent_credential_repository import AgentCredentialRepository
from app.repositories.agent_enrollment_repository import AgentEnrollmentRepository
from app.repositories.agent_inventory_item_repository import AgentInventoryItemRepository
from app.repositories.agent_inventory_snapshot_repository import AgentInventorySnapshotRepository
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.patch_job_repository import PatchJobRepository
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_repository import PatchRepository
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.agent import (
    AgentCommandPollRequest,
    AgentCommandHistoryItem,
    AgentInventorySnapshotItem,
    AgentInventoryDetailItem,
    AgentInventoryDetailResponse,
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
    ForceReidentifyRequest,
    ForceReidentifyResponse,
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

logger = logging.getLogger(__name__)
router = APIRouter()


def _record_identity_event(
    db: Session,
    *,
    agent_id: str,
    event_type: str,
    status: str,
    actor: str,
    new_agent_id: str | None = None,
    command_id: str | None = None,
    platform: str | None = None,
    hostname: str | None = None,
    hardware_fingerprint: str | None = None,
    previous_fingerprint: str | None = None,
    reason: str | None = None,
    message: str | None = None,
) -> AgentIdentityHistoryModel:
    return AgentIdentityHistoryRepository(db).add_once_for_command(
        AgentIdentityHistoryModel(
            id=f"identity-{secrets.token_hex(12)}",
            agent_id=agent_id,
            new_agent_id=new_agent_id,
            command_id=command_id,
            event_type=event_type,
            status=status,
            platform=platform,
            hostname=hostname,
            hardware_fingerprint=hardware_fingerprint,
            previous_fingerprint=previous_fingerprint,
            actor=actor,
            reason=reason,
            message=message,
        )
    )


def _validated_install_server_url(settings_service: SettingsService) -> str:
    server_url = settings_service.get_agent_install_server_url().rstrip("/")
    parsed = urlparse(server_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise HTTPException(
            status_code=409,
            detail="Agent install server URL must be an absolute HTTP(S) URL",
        )
    if parsed.scheme == "http" and parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        raise HTTPException(
            status_code=409,
            detail="Force reidentification requires HTTPS outside localhost",
        )
    return server_url


def _validate_installer_agent_id(agent_id: str | None, platform: str) -> str | None:
    if agent_id is None:
        return None
    if not re.fullmatch(rf"{platform}-[A-Za-z0-9-]{{16,80}}", agent_id):
        raise HTTPException(status_code=422, detail=f"Invalid {platform} agent_id")
    return agent_id


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
    if "does not have a security-tagged or critical-severity" in normalized:
        return "guardrail_security_and_critical_blocked"
    if "does not have a security-tagged" in normalized:
        return "guardrail_security_only_blocked"
    if "windows apply path is disabled" in normalized:
        return "guardrail_windows_apply_disabled"
    return "execution_error"


def _inventory_patch_id(agent_id: str, item: AgentInventoryItemModel) -> str:
    raw_identifier = (item.kb_id or item.identifier or item.title).strip()
    safe_identifier = raw_identifier.replace("/", "-").replace("\\", "-").replace(" ", "-")
    safe_agent_id = agent_id.replace("/", "-").replace("\\", "-")
    candidate = f"{safe_identifier}@{safe_agent_id}"
    if len(candidate) <= 120:
        return candidate

    digest = sha1(candidate.encode("utf-8")).hexdigest()[:10]
    return f"{safe_identifier[:80]}-{digest}@{safe_agent_id[:24]}"


def _inventory_patch_category(item: AgentInventoryItemModel) -> str:
    # Prefer agent-provided value (Cockpit/PackageKit standard: security|bugfix|enhancement|unknown)
    if item.category:
        return item.category
    # Fallback heuristic for agents that don't send category
    if item.security_only:
        return "security"
    source = (item.source or "").lower()
    summary = (item.summary or "").lower()
    title = item.title.lower()
    if "driver" in source or "driver" in summary or "driver" in title:
        return "driver"
    if "firmware" in source or "firmware" in summary or "firmware" in title:
        return "firmware"
    return "unknown"


def _inventory_patch_severity(item: AgentInventoryItemModel) -> str:
    # Prefer agent-provided value (Cockpit/PackageKit standard: critical|important|moderate|low|unknown)
    if item.severity:
        return item.severity
    # Fallback heuristic for agents that don't send severity
    if item.security_only:
        return "important"
    return "low"


# Janela em que uma volta ao fingerprint anterior e tratada como oscilacao (possivel
# identidade duplicada, ex.: dois hosts compartilhando o mesmo agent_id) em vez de um
# reprovisionamento legitimo.
IDENTITY_CONFLICT_OSCILLATION_WINDOW = timedelta(hours=1)
FORCE_REIDENTIFY_CLAIM_TIMEOUT = timedelta(minutes=15)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    # SQLite (usado nos testes) nao preserva tzinfo mesmo em colunas DateTime(timezone=True):
    # o valor volta naive do banco. Trata naive como UTC e normaliza timestamps aware para UTC.
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _handle_identity_conflict(
    machine: MachineModel,
    new_fingerprint: str,
    managed_machine_id: str,
) -> tuple[str, str] | None:
    """Atualiza o estado de identidade e retorna o evento de auditoria a persistir.

    O helper nao grava no banco. Assim, a maquina e confirmada primeiro pelo endpoint e a
    auditoria nao provoca um commit implicito no meio da decisao de identidade.
    """
    now = datetime.now(UTC)

    if machine.identity_conflict_oscillation_detected_at is not None:
        # Ja sinalizado como possivel identidade duplicada; permanece em revisao manual
        # (ver resolve_machine_identity_conflict) em vez de auto-resolver de novo.
        machine.identity_conflict_fingerprint = new_fingerprint
        machine.identity_conflict_detected_at = now
        logger.warning(
            "Identity conflict (awaiting manual review) for machine %s: expected %s, saw %s",
            managed_machine_id,
            machine.hardware_fingerprint,
            new_fingerprint,
        )
        return None

    last_auto_resolved_at = _as_aware_utc(machine.identity_conflict_auto_resolved_at)
    elapsed_since_auto_resolve = (
        now - last_auto_resolved_at if last_auto_resolved_at is not None else None
    )
    is_oscillation = (
        elapsed_since_auto_resolve is not None
        and timedelta(0) <= elapsed_since_auto_resolve <= IDENTITY_CONFLICT_OSCILLATION_WINDOW
        and machine.identity_conflict_previous_fingerprint == new_fingerprint
    )

    if is_oscillation:
        machine.identity_conflict_fingerprint = new_fingerprint
        machine.identity_conflict_detected_at = now
        machine.identity_conflict_oscillation_detected_at = now
        logger.warning(
            "Identity oscillation detected for machine %s: fingerprint alternating between %s and %s",
            managed_machine_id,
            machine.hardware_fingerprint,
            new_fingerprint,
        )
        return (
            "machine_identity_conflict_oscillation_detected",
            f"Possivel identidade duplicada na maquina {managed_machine_id}: fingerprint "
            f"alternando entre {machine.hardware_fingerprint!r} e {new_fingerprint!r}. "
            "Requer revisao manual.",
        )

    previous_fingerprint = machine.hardware_fingerprint
    machine.identity_conflict_previous_fingerprint = previous_fingerprint
    machine.hardware_fingerprint = new_fingerprint
    machine.identity_conflict_auto_resolved_at = now
    machine.identity_conflict_fingerprint = None
    machine.identity_conflict_detected_at = None
    logger.warning(
        "Identity conflict auto-resolved for machine %s: fingerprint changed from %s to %s",
        managed_machine_id,
        previous_fingerprint,
        new_fingerprint,
    )
    return (
        "machine_identity_conflict_auto_resolved",
        f"Conflito de identidade resolvido automaticamente na maquina {managed_machine_id}: "
        f"fingerprint anterior {previous_fingerprint!r} substituido por {new_fingerprint!r}.",
    )


def _sync_inventory_patches(
    db: Session,
    agent_id: str,
    managed_machine_id: str,
    pending_items: list[AgentInventoryItemModel],
) -> None:
    patch_repository = PatchRepository(db)
    target = f"machine:{managed_machine_id}"
    expected_patch_ids: set[str] = set()

    for item in pending_items:
        patch_id = _inventory_patch_id(agent_id, item)
        expected_patch_ids.add(patch_id)
        severity = _inventory_patch_severity(item)
        category = _inventory_patch_category(item)
        # Patches do arquivo de seguranca nao devem ter severity abaixo de moderate
        if category == "security" and severity in {"low", "unknown"}:
            severity = "moderate"
        existing = patch_repository.get_by_id(patch_id)
        patch = existing or PatchModel(
            id=patch_id,
            display_name=item.title,
            target=target,
            severity=severity,
            category=category,
            machines=1,
            release_date=date.today(),
            approval_status="pending",
            reviewed_by=None,
            reviewed_at=None,
        )
        patch.display_name = item.title or patch_id
        patch.target = target
        patch.severity = severity
        patch.category = category
        patch.machines = 1
        patch.release_date = date.today()
        patch_repository.update(patch)

    for stale_patch in patch_repository.list_by_target(target):
        if stale_patch.id not in expected_patch_ids:
            # Patch sumiu do inventario — pacote foi instalado ou nao e mais elegivel.
            # Removemos independente do approval_status: o historico de execucao fica
            # no ExecutionLog e nos jobs concluidos. Se o pacote voltar a precisar de
            # atualizacao, o proximo inventario recriaras o patch como "pending".
            patch_repository.delete(stale_patch)


def _repo_root() -> Path:
    current_path = Path(__file__).resolve()
    for candidate in (current_path.parent, *current_path.parents):
        if (
            (candidate / "apps" / "agent-linux" / "agent" / "main.py").exists()
            and (candidate / "apps" / "agent-windows" / "agent" / "main.py").exists()
        ):
            return candidate
    raise RuntimeError("Unable to locate agent source files")


def _read_agent_linux_file(relative_path: str) -> str:
    return (_repo_root() / "apps" / "agent-linux" / relative_path).read_text(encoding="utf-8")


def _read_agent_windows_file(relative_path: str) -> str:
    return (_repo_root() / "apps" / "agent-windows" / relative_path).read_text(encoding="utf-8")


def _windows_agent_exe_path() -> Path:
    exe_path = _repo_root() / "apps" / "agent-windows" / "dist" / "PatchManagerAgentWindows.exe"
    if not exe_path.exists() or not exe_path.is_file():
        raise RuntimeError("Windows agent standalone executable not found")
    return exe_path


def _windows_agent_download_block(server_url: str) -> str:
    agent_exe_url = f"{server_url.rstrip('/')}/api/v1/agents/install/windows-agent.exe"
    return f"""
$AgentExeUrl = "{agent_exe_url}"
$DistRoot = Join-Path $InstallRoot "dist"
$AgentExeTarget = Join-Path $DistRoot "PatchManagerAgentWindows.exe"

function Save-UrlFile {{
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$Target
  )

  $null = New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($Target))
  try {{
    Invoke-WebRequest -Uri $Url -OutFile $Target -UseBasicParsing
  }} catch {{
    $client = New-Object System.Net.WebClient
    $client.DownloadFile($Url, $Target)
  }}

  if (-not (Test-Path $Target)) {{
    throw "Falha ao baixar $Url para $Target."
  }}
  if ((Get-Item $Target).Length -lt 1000000) {{
    throw "Arquivo baixado parece incompleto: $Target."
  }}
}}

Save-UrlFile -Url $AgentExeUrl -Target $AgentExeTarget
"""


def _build_linux_installer_script(
    server_url: str,
    bootstrap_token: str,
    agent_id: str | None = None,
) -> str:
    agent_id_assignment = (
        agent_id
        or "linux-$(cat /proc/sys/kernel/random/uuid 2>/dev/null || uuidgen)"
    )
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

AGENT_ID="{agent_id_assignment}"

sudo mkdir -p "${{INSTALL_ROOT}}" /etc/patch-manager /var/log/patch-manager

{joined_blocks}

if ! id patchmanager >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin patchmanager
fi

sudo tee "${{ENV_TARGET}}" >/dev/null <<EOF
PATCH_MANAGER_ENV_FILE=${{ENV_TARGET}}
PATCH_MANAGER_API=${{SERVER_URL}}/api/v1/agents
PATCH_MANAGER_AGENT_KEY=
PATCH_MANAGER_AGENT_ID=${{AGENT_ID}}
PATCH_MANAGER_BOOTSTRAP_TOKEN=${{BOOTSTRAP_TOKEN}}
PATCH_MANAGER_AGENT_VERSION=0.2.0
PATCH_MANAGER_EXECUTION_MODE=apply
PATCH_MANAGER_ENABLE_REAL_APPLY=true
PATCH_MANAGER_ALLOW_SECURITY_ONLY=false
PATCH_MANAGER_ALLOW_SECURITY_AND_CRITICAL=false
PATCH_MANAGER_ALLOWED_PACKAGE_PATTERNS=
PATCH_MANAGER_APT_APPLY_TIMEOUT=900
PATCH_MANAGER_ENABLE_HOST_REBOOT=true
PATCH_MANAGER_SIMULATE_HOST_REBOOT=false
PATCH_MANAGER_REBOOT_COMMAND_TIMEOUT=30
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

# Allow patchmanager to install packages, schedule reboots, run upgrade scripts and read the hardware fingerprint without password prompt
sudo tee /etc/sudoers.d/patch-manager > /dev/null <<'SUDOERS_EOF'
patchmanager ALL=(root) NOPASSWD: /usr/sbin/shutdown
patchmanager ALL=(root) NOPASSWD: /usr/bin/apt-get
patchmanager ALL=(root) NOPASSWD: /bin/cat /sys/class/dmi/id/product_uuid
patchmanager ALL=(root) NOPASSWD: /usr/bin/bash
SUDOERS_EOF
sudo chmod 440 /etc/sudoers.d/patch-manager
sudo rm -f /etc/sudoers.d/patch-manager-shutdown

sudo systemctl daemon-reload
sudo systemctl enable "${{SERVICE_NAME}}"
sudo systemctl restart "${{SERVICE_NAME}}"

echo "Instalacao concluida."
echo "Agent ID: ${{AGENT_ID}}"
echo "AVISO: se este host ja foi instalado/enrollado antes com um Agent ID diferente, o registro antigo dessa maquina no painel ficara orfao e devera ser removido manualmente."
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
  "PATCH_MANAGER_ENV_FILE=${{ENV_TARGET}}" \
  PATCH_MANAGER_ENABLE_REAL_APPLY=true \
  PATCH_MANAGER_ALLOW_SECURITY_ONLY=false \
  PATCH_MANAGER_ALLOW_SECURITY_AND_CRITICAL=false \
  PATCH_MANAGER_ALLOWED_PACKAGE_PATTERNS= \
  PATCH_MANAGER_APT_APPLY_TIMEOUT=900 \
  PATCH_MANAGER_ENABLE_HOST_REBOOT=true \
  PATCH_MANAGER_SIMULATE_HOST_REBOOT=false \
  PATCH_MANAGER_REBOOT_COMMAND_TIMEOUT=30; do
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

# Ensure sudoers covers apt-get, shutdown, bash for upgrade scripts, and the hardware fingerprint read (idempotent rewrite)
sudo tee /etc/sudoers.d/patch-manager > /dev/null <<'SUDOERS_EOF'
patchmanager ALL=(root) NOPASSWD: /usr/sbin/shutdown
patchmanager ALL=(root) NOPASSWD: /usr/bin/apt-get
patchmanager ALL=(root) NOPASSWD: /bin/cat /sys/class/dmi/id/product_uuid
patchmanager ALL=(root) NOPASSWD: /usr/bin/bash
SUDOERS_EOF
sudo chmod 440 /etc/sudoers.d/patch-manager
sudo rm -f /etc/sudoers.d/patch-manager-shutdown

sudo chown -R patchmanager:patchmanager "${{INSTALL_ROOT}}" /var/log/patch-manager
sudo systemctl daemon-reload
sudo systemctl enable "${{SERVICE_NAME}}"
sudo systemctl restart "${{SERVICE_NAME}}"

echo "Atualizacao concluida."
echo "Servico reiniciado: ${{SERVICE_NAME}}"
echo "Logs:"
echo "  sudo journalctl -u ${{SERVICE_NAME}} -f"
"""


def _build_windows_installer_script(
    server_url: str,
    bootstrap_token: str,
    agent_id: str | None = None,
) -> str:
    agent_id_assignment = (
        f'"{agent_id}"'
        if agent_id
        else '"windows-$([guid]::NewGuid().ToString(\'N\'))"'
    )
    files_to_write = {
        "agent/config.py": _read_agent_windows_file("agent/config.py"),
        "agent/logger.py": _read_agent_windows_file("agent/logger.py"),
        "agent/api_client.py": _read_agent_windows_file("agent/api_client.py"),
        "agent/inventory.py": _read_agent_windows_file("agent/inventory.py"),
        "agent/executor.py": _read_agent_windows_file("agent/executor.py"),
        "agent/main.py": _read_agent_windows_file("agent/main.py"),
        "agent/service.py": _read_agent_windows_file("agent/service.py"),
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
    agent_download_block = _windows_agent_download_block(server_url)
    return f"""param()
$ErrorActionPreference = 'Stop'

$ServerUrl = "{server_url.rstrip('/')}"
$BootstrapToken = "{bootstrap_token}"
$FinalInstallRoot = "C:\\ProgramData\\PatchManager\\agent-windows"
$OperationId = [guid]::NewGuid().ToString('N')
$StagingRoot = "$FinalInstallRoot.reidentify-staging-$OperationId"
$BackupRoot = "$FinalInstallRoot.reidentify-backup-$OperationId"
$EnvTarget = "C:\\ProgramData\\PatchManager\\agent-windows.env"
$EnvBackup = "$EnvTarget.reidentify-backup-$OperationId"
$InstallRoot = $StagingRoot
$ServiceName = "PatchManagerAgent"
$LogFile = "C:\\ProgramData\\PatchManager\\agent-windows.log"
$AgentId = {agent_id_assignment}
$OriginalMoved = $false
$NewInstalled = $false
$EnvReplaced = $false
$NewServiceInstallStarted = $false

function Test-IsAdministrator {{
  $identity = [System.Security.Principal.WindowsIdentity]::GetCurrent()
  $principal = New-Object System.Security.Principal.WindowsPrincipal($identity)
  return $principal.IsInRole([System.Security.Principal.WindowsBuiltInRole]::Administrator)
}}

if (-not (Test-IsAdministrator)) {{
  throw "A instalacao do servico requer privilegio administrativo. Execute o PowerShell como Administrador."
}}

$ExistingService = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
$HadFinalInstall = Test-Path $FinalInstallRoot
$HadEnv = Test-Path $EnvTarget
trap {{
  $Failure = $_
  if ($null -eq $ExistingService -and $NewServiceInstallStarted) {{
    sc.exe delete $ServiceName | Out-Null
  }}
  if ($NewInstalled -and (Test-Path $FinalInstallRoot)) {{
    Remove-Item -Path $FinalInstallRoot -Recurse -Force -ErrorAction SilentlyContinue
  }}
  if ($OriginalMoved -and (Test-Path $BackupRoot)) {{
    Move-Item -Path $BackupRoot -Destination $FinalInstallRoot -Force
  }}
  if ($EnvReplaced) {{
    if ($HadEnv -and (Test-Path $EnvBackup)) {{
      Copy-Item -Path $EnvBackup -Destination $EnvTarget -Force
    }} else {{
      Remove-Item -Path $EnvTarget -Force -ErrorAction SilentlyContinue
    }}
  }}
  Remove-Item -Path $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
  Remove-Item -Path $EnvBackup -Force -ErrorAction SilentlyContinue
  if ($null -ne $ExistingService) {{
    Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
  }}
  throw $Failure
}}

Remove-Item -Path $StagingRoot -Recurse -Force -ErrorAction SilentlyContinue
$null = New-Item -ItemType Directory -Force -Path $InstallRoot
$null = New-Item -ItemType Directory -Force -Path "C:\\ProgramData\\PatchManager"

{joined_blocks}

{agent_download_block}

# O runtime novo foi totalmente preparado e o executavel validado em staging.
# Somente agora interrompemos o servico e fazemos a troca no mesmo volume.
if ($HadEnv) {{
  Copy-Item -Path $EnvTarget -Destination $EnvBackup -Force
}}
if ($null -ne $ExistingService) {{
  Stop-Service -Name $ServiceName -Force
  Start-Sleep -Seconds 2
}}
if ($HadFinalInstall) {{
  Move-Item -Path $FinalInstallRoot -Destination $BackupRoot -Force
  $OriginalMoved = $true
}}
Move-Item -Path $StagingRoot -Destination $FinalInstallRoot -Force
$NewInstalled = $true
$InstallRoot = $FinalInstallRoot
$AgentExeTarget = Join-Path $InstallRoot "dist\\PatchManagerAgentWindows.exe"

$EnvContent = @"
PATCH_MANAGER_API=$ServerUrl/api/v1/agents
PATCH_MANAGER_AGENT_ID=$AgentId
PATCH_MANAGER_AGENT_KEY=
PATCH_MANAGER_BOOTSTRAP_TOKEN=$BootstrapToken
PATCH_MANAGER_AGENT_VERSION=0.2.0
PATCH_MANAGER_EXECUTION_MODE=apply
PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=true
PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=true
PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT=1800
PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=true
PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=false
PATCH_MANAGER_WINDOWS_REBOOT_COMMAND_TIMEOUT=30
PATCH_MANAGER_HEARTBEAT_INTERVAL=10
PATCH_MANAGER_IDLE_SLEEP=5
PATCH_MANAGER_INVENTORY_INTERVAL=60
PATCH_MANAGER_FAILURE_BACKOFF=10
PATCH_MANAGER_REQUEST_TIMEOUT=10
PATCH_MANAGER_LOG_LEVEL=INFO
PATCH_MANAGER_LOG_TO_STDOUT=true
PATCH_MANAGER_LOG_FILE=$LogFile
"@
[System.IO.File]::WriteAllText($EnvTarget, $EnvContent, (New-Object System.Text.UTF8Encoding($false)))
$EnvReplaced = $true

[System.Environment]::SetEnvironmentVariable("PATCH_MANAGER_ENV_FILE", $EnvTarget, "Machine")

if ($null -eq $ExistingService) {{
  $NewServiceInstallStarted = $true
  & $AgentExeTarget install | Out-Null
  if ($LASTEXITCODE -ne 0) {{
    throw "Falha ao registrar o servico $ServiceName (exit code $LASTEXITCODE)."
  }}
}}
sc.exe config $ServiceName start= auto | Out-Null
sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/30000/restart/60000 | Out-Null
Start-Service -Name $ServiceName

$NewInstalled = $false
$EnvReplaced = $false
Remove-Item -Path $BackupRoot -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Path $EnvBackup -Force -ErrorAction SilentlyContinue

Write-Host "Instalacao concluida."
Write-Host "Agent ID: $AgentId"
Write-Host "AVISO: se este host ja foi instalado/enrollado antes com um Agent ID diferente, o registro antigo dessa maquina no painel ficara orfao e devera ser removido manualmente."
Write-Host "Aguardando aprovacao no painel do Patch Manager."
Write-Host "Arquivo de ambiente: $EnvTarget"
Write-Host "Servico registrado: $ServiceName"
"""


def _build_windows_upgrade_script(server_url: str) -> str:
    files_to_write = {
        "agent/config.py": _read_agent_windows_file("agent/config.py"),
        "agent/logger.py": _read_agent_windows_file("agent/logger.py"),
        "agent/api_client.py": _read_agent_windows_file("agent/api_client.py"),
        "agent/inventory.py": _read_agent_windows_file("agent/inventory.py"),
        "agent/executor.py": _read_agent_windows_file("agent/executor.py"),
        "agent/main.py": _read_agent_windows_file("agent/main.py"),
        "agent/service.py": _read_agent_windows_file("agent/service.py"),
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
    agent_download_block = _windows_agent_download_block(server_url)
    return f"""param()
$ErrorActionPreference = 'Stop'

$ServerUrl = "{server_url.rstrip('/')}"
$InstallRoot = "C:\\ProgramData\\PatchManager\\agent-windows"
$EnvTarget = "C:\\ProgramData\\PatchManager\\agent-windows.env"
$ServiceName = "PatchManagerAgent"
$OldTaskName = "PatchManagerAgentWindows"

if (-not (Test-Path $InstallRoot)) {{
  throw "InstallRoot nao encontrado. Rode a instalacao inicial primeiro."
}}

# Parar e remover task agendada antiga (migracao de versoes anteriores)
try {{
  Stop-ScheduledTask -TaskName $OldTaskName -ErrorAction SilentlyContinue | Out-Null
}} catch {{}}
Unregister-ScheduledTask -TaskName $OldTaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

# Parar o servico para permitir substituicao dos arquivos
Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue | Out-Null
Start-Sleep -Seconds 3

{joined_blocks}

{agent_download_block}

if (-not (Test-Path $EnvTarget)) {{
@"
PATCH_MANAGER_API=$ServerUrl/api/v1/agents
"@ | Set-Content -Path $EnvTarget -Encoding UTF8
}}

$existing = Get-Content $EnvTarget -Raw
if ($existing -notmatch 'PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=true"
}}
if ($existing -notmatch 'PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=true"
}}
if ($existing -notmatch 'PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT=1800"
}}
if ($existing -notmatch 'PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=true"
}} else {{
  (Get-Content $EnvTarget) -replace '^PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=.*$', 'PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=true' |
    Set-Content -Path $EnvTarget -Encoding UTF8
}}
if ($existing -notmatch 'PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=') {{
  Add-Content -Path $EnvTarget -Value "PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=false"
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

# Registrar servico se ainda nao estiver instalado
$svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
if ($null -eq $svc) {{
  & $AgentExeTarget install | Out-Null
  sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/30000/restart/60000 | Out-Null
}}

sc.exe config $ServiceName start= auto | Out-Null
Start-Service -Name $ServiceName

Write-Host "Atualizacao concluida."
Write-Host "Servico reiniciado: $ServiceName"
"""


@router.get("/install/linux.sh", response_class=PlainTextResponse)
def download_linux_installer(
    server_url: str,
    bootstrap_token: str,
    agent_id: str | None = None,
) -> str:
    return _build_linux_installer_script(
        server_url,
        bootstrap_token,
        _validate_installer_agent_id(agent_id, "linux"),
    )


@router.get("/install/linux-upgrade.sh", response_class=PlainTextResponse)
def download_linux_upgrade_script(server_url: str) -> str:
    return _build_linux_upgrade_script(server_url)


@router.get("/install/windows.ps1", response_class=PlainTextResponse)
def download_windows_installer(
    server_url: str,
    bootstrap_token: str,
    agent_id: str | None = None,
) -> str:
    return _build_windows_installer_script(
        server_url,
        bootstrap_token,
        _validate_installer_agent_id(agent_id, "windows"),
    )


@router.get("/install/windows-upgrade.ps1", response_class=PlainTextResponse)
def download_windows_upgrade_script(server_url: str) -> str:
    return _build_windows_upgrade_script(server_url)


@router.get("/install/windows-agent.exe")
def download_windows_agent_executable() -> FileResponse:
    try:
        exe_path = _windows_agent_exe_path()
    except RuntimeError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FileResponse(
        exe_path,
        media_type="application/octet-stream",
        filename="PatchManagerAgentWindows.exe",
    )


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
    transition = AgentIdentityHistoryRepository(db).get_requested_transition_by_new_agent_id(
        payload.agent_id
    )
    if transition is not None:
        _record_identity_event(
            db,
            agent_id=transition.agent_id,
            new_agent_id=payload.agent_id,
            command_id=transition.command_id,
            event_type="force_reidentify_enrollment_detected",
            status=enrollment.status,
            actor=payload.agent_id,
            platform=payload.platform,
            hostname=payload.hostname,
            reason=transition.reason,
            message=(
                f"Novo enrollment {payload.agent_id} detectado para {payload.hostname}; "
                "aguardando o fluxo normal de aprovacao."
            ),
        )
    if enrollment.status == "approved":
        if not enrollment.issued_key:
            # Previously active agent lost its key — generate a new one automatically
            issued_key = secrets.token_urlsafe(24)
            credential_repository = AgentCredentialRepository(db)
            credential = credential_repository.get_by_agent_id(enrollment.agent_id)
            if credential is None:
                credential_repository.add(
                    AgentCredentialModel(
                        agent_id=enrollment.agent_id,
                        platform=enrollment.platform,
                        description=f"Auto-renewed key for {enrollment.hostname}",
                        key_hash=hash_password(issued_key),
                        is_active=True,
                    )
                )
            else:
                credential.key_hash = hash_password(issued_key)
                credential.is_active = True
                db.add(credential)
                db.commit()
            enrollment = repository.approve(enrollment, issued_key)
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
    patch_category: dict[str, str] = {
        p.id: p.category for p in PatchRepository(db).list_all()
    }
    return [
        PatchJobItem.model_validate(job).model_copy(
            update={
                "failure_reason": _classify_job_failure(job.error_message),
                "category": patch_category.get(job.patch_id, "unknown"),
            }
        )
        for job in repository.list_recent()
    ]


@router.get("/connected", response_model=list[ConnectedAgentResponse])
def list_connected_agents(
    _: Annotated[UserResponse, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> list[ConnectedAgentResponse]:
    snapshot_repository = AgentInventorySnapshotRepository(db)
    enriched_agents: list[ConnectedAgentResponse] = []
    for agent in agent_registry_service.list_connected():
        snapshot = snapshot_repository.get_by_agent_id(agent.agent_id)
        if snapshot is None:
            enriched_agents.append(agent)
            continue
        enriched_agents.append(
            agent.model_copy(
                update={
                    "post_patch_state": snapshot.post_patch_state,
                    "post_patch_message": snapshot.post_patch_message,
                    "last_apply_result": snapshot.last_apply_result,
                    "last_apply_at": snapshot.last_apply_at,
                    "reboot_scheduled_at": snapshot.reboot_scheduled_at,
                }
            )
        )
    return enriched_agents


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
                post_patch_state=snapshot.post_patch_state if snapshot else None,
                post_patch_message=snapshot.post_patch_message if snapshot else None,
                last_apply_result=snapshot.last_apply_result if snapshot else None,
                last_apply_at=snapshot.last_apply_at if snapshot else None,
                reboot_scheduled_at=snapshot.reboot_scheduled_at if snapshot else None,
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
    current_user: Annotated[UserResponse, Depends(require_operator)],
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
    current_user: Annotated[UserResponse, Depends(require_operator)],
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
    current_user: Annotated[UserResponse, Depends(require_operator)],
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


@router.post("/connected/{agent_id}/upgrade")
def request_connected_agent_upgrade(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> dict[str, str]:
    connected_agent = agent_registry_service.get_connected(agent_id)
    if connected_agent is None:
        raise HTTPException(status_code=404, detail="Connected agent not found")

    AgentCommandRepository(db).add(
        AgentCommandModel(
            id=f"cmd-{secrets.token_hex(8)}",
            agent_id=agent_id,
            command_type="upgrade_agent",
            status="pending",
            requested_by=current_user.username,
            payload_json=json.dumps({"requested_by": current_user.username}),
        )
    )
    SettingsService(db).record_operational_event(
        "agent_upgrade_requested",
        current_user.username,
        f"Solicitou upgrade do agente {agent_id}.",
    )
    return {"status": "queued"}


@router.post(
    "/connected/{agent_id}/force-reidentify",
    response_model=ForceReidentifyResponse,
)
def request_connected_agent_force_reidentify(
    agent_id: str,
    payload: ForceReidentifyRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(require_operator)],
) -> ForceReidentifyResponse:
    connected_agent = agent_registry_service.get_connected(agent_id)
    if connected_agent is None:
        raise HTTPException(status_code=404, detail="Connected agent not found")

    platform = connected_agent.platform.strip().lower()
    if platform not in {"linux", "windows"}:
        raise HTTPException(
            status_code=400,
            detail="Force reidentification is supported only for Linux and Windows agents",
        )

    settings_service = SettingsService(db)
    if settings_service.get_agent_bootstrap_token_is_expired():
        raise HTTPException(
            status_code=409,
            detail="Agent bootstrap token is expired; rotate it before forcing reidentification",
        )
    bootstrap_token = settings_service.get_agent_bootstrap_token().strip()
    if not bootstrap_token:
        raise HTTPException(status_code=409, detail="Agent bootstrap token is not configured")
    server_url = _validated_install_server_url(settings_service)

    command_repository = AgentCommandRepository(db)
    expired_command = command_repository.expire_stale_force_reidentify(
        agent_id,
        datetime.now(UTC) - FORCE_REIDENTIFY_CLAIM_TIMEOUT,
    )
    if expired_command is not None:
        expired_payload: dict[str, object] = {}
        try:
            parsed_expired_payload = json.loads(expired_command.payload_json or "{}")
            if isinstance(parsed_expired_payload, dict):
                expired_payload = parsed_expired_payload
        except json.JSONDecodeError:
            pass
        _record_identity_event(
            db,
            agent_id=agent_id,
            new_agent_id=str(expired_payload.get("new_agent_id") or "") or None,
            command_id=expired_command.id,
            event_type="force_reidentify_claim_expired",
            status="failed",
            actor="system",
            platform=platform,
            reason=str(expired_payload.get("reason") or "") or None,
            message=expired_command.message,
        )
        settings_service.record_operational_event(
            "agent_force_reidentify_claim_expired",
            "system",
            f"Expirou claim sem confirmacao do comando {expired_command.id} para {agent_id}.",
        )
    if command_repository.has_active_force_reidentify(agent_id):
        raise HTTPException(
            status_code=409,
            detail="A force reidentification command is already pending or running for this agent_id",
        )
    if command_repository.list_pending_for_agent(agent_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "Another command is pending for this agent_id; wait for it to be claimed "
                "before forcing reidentification"
            ),
        )

    command_id = f"cmd-{secrets.token_hex(8)}"
    new_agent_id = f"{platform}-{uuid4().hex}"
    reason = (payload.reason or "shared_agent_id_remediation").strip()[:255]
    command = AgentCommandModel(
        id=command_id,
        agent_id=agent_id,
        command_type="force_reidentify",
        status="pending",
        requested_by=current_user.username,
        payload_json=json.dumps(
            {
                "server_url": server_url,
                "bootstrap_token": bootstrap_token,
                "new_agent_id": new_agent_id,
                "old_agent_id": agent_id,
                "requested_by": current_user.username,
                "reason": reason,
                "target_semantics": "next_claimant",
            }
        ),
    )
    try:
        command_repository.add(command)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A force reidentification command is already pending or running for this agent_id",
        ) from exc

    machine = MachineRepository(db).get_by_id(f"agent-{agent_id}")
    _record_identity_event(
        db,
        agent_id=agent_id,
        new_agent_id=new_agent_id,
        command_id=command_id,
        event_type="force_reidentify_requested",
        status="pending",
        actor=current_user.username,
        platform=platform,
        hostname=machine.name if machine else connected_agent.hostname,
        hardware_fingerprint=machine.hardware_fingerprint if machine else None,
        reason=reason,
        message=(
            "Reidentificacao enfileirada para o host que reivindicar o comando compartilhado; "
            "a credencial antiga permanece ativa para os demais clones."
        ),
    )
    settings_service.record_operational_event(
        "agent_force_reidentify_requested",
        current_user.username,
        f"Enfileirou reidentificacao de {agent_id} para o proximo host a conectar; "
        f"nova identidade reservada: {new_agent_id}.",
    )
    return ForceReidentifyResponse(
        status="queued",
        command_id=command_id,
        old_agent_id=agent_id,
        new_agent_id=new_agent_id,
        target_semantics="next_claimant",
    )


@router.post("/connected/upgrade-batch")
def request_connected_agents_upgrade_batch(
    payload: dict[str, list[str]],
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> dict[str, int]:
    agent_ids = payload.get("agent_ids", [])
    command_repository = AgentCommandRepository(db)
    settings_service = SettingsService(db)
    queued = 0
    for agent_id in agent_ids:
        if agent_registry_service.get_connected(agent_id) is None:
            continue
        command_repository.add(
            AgentCommandModel(
                id=f"cmd-{secrets.token_hex(8)}",
                agent_id=agent_id,
                command_type="upgrade_agent",
                status="pending",
                requested_by=current_user.username,
                payload_json=json.dumps({"requested_by": current_user.username}),
            )
        )
        queued += 1
    if queued:
        settings_service.record_operational_event(
            "agent_upgrade_batch_requested",
            current_user.username,
            f"Upgrade em lote solicitado para {queued} agente(s).",
        )
    return {"queued": queued}


@router.get("/commands/recent", response_model=list[AgentCommandHistoryItem])
def list_recent_agent_commands(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
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
    _: Annotated[UserResponse, Depends(require_viewer)],
) -> list[AgentInventorySnapshotItem]:
    repository = AgentInventorySnapshotRepository(db)
    return [AgentInventorySnapshotItem.model_validate(item) for item in repository.list_recent()]


@router.get("/inventory-details/{agent_id}", response_model=AgentInventoryDetailResponse)
def get_agent_inventory_details(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
) -> AgentInventoryDetailResponse:
    snapshot_repository = AgentInventorySnapshotRepository(db)
    item_repository = AgentInventoryItemRepository(db)
    snapshot = snapshot_repository.get_by_agent_id(agent_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Agent inventory not found")

    pending_updates = [
        AgentInventoryDetailItem.model_validate(item)
        for item in item_repository.list_pending_for_agent(agent_id)
    ]
    installed_updates = [
        AgentInventoryDetailItem.model_validate(item)
        for item in item_repository.list_installed_for_agent(agent_id)
    ]

    return AgentInventoryDetailResponse(
        agent_id=snapshot.agent_id,
        platform=snapshot.platform,
        hostname=snapshot.hostname,
        package_manager=snapshot.package_manager,
        pending_count=snapshot.upgradable_packages,
        installed_count=snapshot.installed_update_count or snapshot.installed_packages,
        updated_at=snapshot.updated_at,
        pending_updates=pending_updates,
        installed_updates=installed_updates,
    )


@router.get("/enrollments/pending", response_model=list[PendingAgentEnrollmentResponse])
def list_pending_enrollments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
) -> list[PendingAgentEnrollmentResponse]:
    repository = AgentEnrollmentRepository(db)
    return [PendingAgentEnrollmentResponse.model_validate(item) for item in repository.list_pending()]


@router.get("/enrollments/rejected", response_model=list[RejectedAgentEnrollmentResponse])
def list_rejected_enrollments(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
) -> list[RejectedAgentEnrollmentResponse]:
    repository = AgentEnrollmentRepository(db)
    return [RejectedAgentEnrollmentResponse.model_validate(item) for item in repository.list_rejected()]


@router.post("/enrollments/{agent_id}/approve", response_model=PendingAgentEnrollmentResponse)
def approve_pending_enrollment(
    agent_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(require_operator)],
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
    current_user: Annotated[UserResponse, Depends(require_operator)],
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
    current_user: Annotated[UserResponse, Depends(require_operator)],
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
    snapshot_repository = AgentInventorySnapshotRepository(db)
    existing_snapshot = snapshot_repository.get_by_agent_id(payload.agent_id)
    preserved_post_patch_state = existing_snapshot.post_patch_state if existing_snapshot else "idle"
    preserved_post_patch_message = existing_snapshot.post_patch_message if existing_snapshot else None
    preserved_last_apply_result = existing_snapshot.last_apply_result if existing_snapshot else None
    preserved_last_apply_at = existing_snapshot.last_apply_at if existing_snapshot else None
    preserved_reboot_scheduled_at = existing_snapshot.reboot_scheduled_at if existing_snapshot else None

    if not payload.reboot_required and preserved_post_patch_state in {"reboot-required", "reboot-scheduled"}:
        preserved_post_patch_state = "reboot-cleared"
        preserved_post_patch_message = "Host voltou sem reboot pendente apos o ultimo ciclo."
        preserved_reboot_scheduled_at = None
        agent_registry_service.update_post_patch_state(
            payload.agent_id,
            post_patch_state=preserved_post_patch_state,
            post_patch_message=preserved_post_patch_message,
            last_apply_result=preserved_last_apply_result,
            last_apply_at=preserved_last_apply_at,
            reboot_scheduled_at=preserved_reboot_scheduled_at,
        )

    snapshot_repository.upsert(
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
            post_patch_state=preserved_post_patch_state,
            post_patch_message=preserved_post_patch_message,
            last_apply_result=preserved_last_apply_result,
            last_apply_at=preserved_last_apply_at,
            reboot_scheduled_at=preserved_reboot_scheduled_at,
        )
    )
    pending_inventory_items = [
        AgentInventoryItemModel(
            agent_id=payload.agent_id,
            platform=payload.platform,
            item_type="pending",
            identifier=item.identifier,
            title=item.title,
            current_version=item.current_version,
            target_version=item.target_version,
            source=item.source,
            summary=item.summary,
            kb_id=item.kb_id,
            security_only=item.security_only,
            category=item.category,
            severity=item.severity,
            installed_at=item.installed_at,
            sort_order=index,
        )
        for index, item in enumerate(payload.pending_updates)
    ]
    installed_inventory_items = [
        AgentInventoryItemModel(
            agent_id=payload.agent_id,
            platform=payload.platform,
            item_type="installed",
            identifier=item.identifier,
            title=item.title,
            current_version=item.current_version,
            target_version=item.target_version,
            source=item.source,
            summary=item.summary,
            kb_id=item.kb_id,
            security_only=item.security_only,
            category=item.category,
            severity=item.severity,
            installed_at=item.installed_at,
            sort_order=index,
        )
        for index, item in enumerate(payload.installed_updates)
    ]
    AgentInventoryItemRepository(db).replace_for_agent(
        payload.agent_id,
        [*pending_inventory_items, *installed_inventory_items],
    )

    machine_repository = MachineRepository(db)
    managed_machine_id = f"agent-{payload.agent_id}"
    # Lock pessimista no PostgreSQL para serializar inventários concorrentes do mesmo agent_id.
    machine = machine_repository.get_by_id_for_update(managed_machine_id)
    identity_audit_event: tuple[str, str] | None = None
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
                environment="production",
                group="Agent Managed",
                status="online",
                pending_patches=payload.upgradable_packages,
                last_check_in=datetime.now(UTC),
                risk=risk,
                hardware_fingerprint=payload.hardware_fingerprint,
                os_release=payload.os_release,
            )
        )
    else:
        machine.name = payload.hostname
        machine.ip = payload.primary_ip
        machine.platform = "Ubuntu" if payload.platform.lower() == "linux" else payload.platform.title()
        machine.environment = machine.environment or "production"
        if payload.os_release:
            machine.os_release = payload.os_release
        machine.group = machine.group or "Agent Managed"
        machine.status = "online"
        machine.pending_patches = payload.upgradable_packages
        machine.last_check_in = datetime.now(UTC)
        machine.risk = risk
        if payload.hardware_fingerprint:
            if machine.hardware_fingerprint is None:
                machine.hardware_fingerprint = payload.hardware_fingerprint
            elif machine.hardware_fingerprint != payload.hardware_fingerprint:
                identity_audit_event = _handle_identity_conflict(
                    machine,
                    payload.hardware_fingerprint,
                    managed_machine_id,
                )
        machine_repository.update(machine)
        if identity_audit_event is not None:
            event_type, summary = identity_audit_event
            SettingsService(db).record_operational_event(event_type, "system", summary)
            _record_identity_event(
                db,
                agent_id=payload.agent_id,
                event_type=event_type,
                status=(
                    "oscillation_detected"
                    if event_type == "machine_identity_conflict_oscillation_detected"
                    else "auto_resolved"
                ),
                actor="system",
                platform=payload.platform,
                hostname=payload.hostname,
                hardware_fingerprint=payload.hardware_fingerprint,
                previous_fingerprint=machine.identity_conflict_previous_fingerprint,
                message=summary,
            )

    transition = AgentIdentityHistoryRepository(db).get_requested_transition_by_new_agent_id(
        payload.agent_id
    )
    if transition is not None:
        _record_identity_event(
            db,
            agent_id=transition.agent_id,
            new_agent_id=payload.agent_id,
            command_id=transition.command_id,
            event_type="force_reidentify_inventory_seen",
            status="enrolled",
            actor=payload.agent_id,
            platform=payload.platform,
            hostname=payload.hostname,
            hardware_fingerprint=payload.hardware_fingerprint,
            reason=transition.reason,
            message=f"Inventario recebido da nova identidade {payload.agent_id} ({payload.hostname}).",
        )

    _sync_inventory_patches(db, payload.agent_id, managed_machine_id, pending_inventory_items)

    # Recomputa pending_patches como count de patches nao instalados no PM:
    # "pending" (aguardando decisao) + "approved" (aprovados, aguardando instalacao).
    # Isso alinha com o total de upgradable_packages do OS e com a visao "Todos"
    # na tela de Aprovacoes. "rejected" e excluido (decisao tomada).
    target = f"machine:{managed_machine_id}"
    all_pending_patches = [
        p for p in PatchRepository(db).list_by_target(target)
        if p.approval_status in {"pending", "approved"}
    ]
    pending_pm_count = len(all_pending_patches)
    pending_security_critical_count = sum(
        1 for p in all_pending_patches
        if p.category == "security" or p.severity == "critical"
    )
    machine_refreshed = machine_repository.get_by_id(managed_machine_id)
    if machine_refreshed is not None:
        machine_refreshed.pending_patches = pending_pm_count
        machine_refreshed.pending_security_critical_patches = pending_security_critical_count
        machine_repository.update(machine_refreshed)

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
    # machine_id e derivado deterministicamente do agent_id (mesmo padrao do inventario)
    machine_id = f"agent-{payload.agent_id}"
    job = repository.get_next_pending_for_agent(payload.platform, machine_id)
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

    # Respeitar a política de reboot do agendamento. O schedule armazena o valor
    # como label em português (ex.: "Nao reiniciar"). Se o schedule proíbe reboot,
    # enviamos "manual" ao agente para evitar reinicializações não autorizadas,
    # independentemente da configuração global.
    schedule = ScheduleRepository(db).get_by_id(job.schedule_id)
    schedule_rp = (schedule.reboot_policy or "").lower() if schedule else ""
    schedule_prevents_reboot = "nao" in schedule_rp or "não" in schedule_rp

    is_linux = payload.platform.lower() == "linux"
    effective_reboot_policy = (
        "manual"
        if schedule_prevents_reboot
        else (
            settings_service.get_linux_reboot_policy()
            if is_linux
            else settings_service.get_windows_reboot_policy()
        )
    )

    return AgentJobResponse(
        id=job.id,
        schedule_name=job.schedule_name,
        machine_id=job.machine_id,
        machine_name=job.machine_name,
        patch_id=job.patch_id,
        platform=job.platform,
        severity=job.severity,
        execution_mode=settings_service.resolve_linux_execution_mode(machine.group if machine else None)
        if is_linux
        else "apply",
        real_apply_enabled=settings_service.get_linux_real_apply_enabled(),
        allow_security_only=settings_service.get_linux_allow_security_only(),
        allow_security_and_critical=settings_service.get_linux_allow_security_and_critical(),
        allowed_package_patterns=settings_service.get_linux_allowed_package_patterns(),
        apt_apply_timeout_seconds=settings_service.get_linux_apt_apply_timeout_seconds(),
        windows_scan_apply_enabled=settings_service.get_windows_scan_apply_enabled(),
        windows_download_install_enabled=settings_service.get_windows_download_install_enabled(),
        windows_command_timeout_seconds=settings_service.get_windows_command_timeout_seconds(),
        reboot_policy=effective_reboot_policy,
        reboot_grace_minutes=(
            settings_service.get_linux_reboot_grace_minutes()
            if is_linux
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
    if command.command_type.strip().lower() == "force_reidentify":
        new_agent_id = str(payload_data.get("new_agent_id") or "") or None
        _record_identity_event(
            db,
            agent_id=payload.agent_id,
            new_agent_id=new_agent_id,
            command_id=command.id,
            event_type="force_reidentify_claimed",
            status="running",
            actor=payload.agent_id,
            platform=payload.platform,
            reason=str(payload_data.get("reason") or "") or None,
            message="Comando reivindicado pelo proximo host que consultou a fila compartilhada.",
        )
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
    snapshot_repository = AgentInventorySnapshotRepository(db)
    command = command_repository.get_by_id(command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found")
    if command.agent_id != payload.agent_id:
        raise HTTPException(status_code=403, detail="Invalid agent for command result")

    normalized_result = payload.result.strip().lower()
    expected_terminal_status = "completed" if normalized_result == "applied" else "failed"
    if command.status in {"completed", "failed"}:
        if command.status != expected_terminal_status:
            raise HTTPException(status_code=409, detail="Conflicting command result replay")
        return {"status": "acknowledged", "command_id": command_id}
    if command.status != "running":
        raise HTTPException(status_code=409, detail="Command is not running")

    command_repository.complete(command, normalized_result, payload.message)
    command_kind = command.command_type.strip().lower()

    if command_kind == "force_reidentify":
        command_payload: dict[str, object] = {}
        try:
            parsed_payload = json.loads(command.payload_json or "{}")
            if isinstance(parsed_payload, dict):
                command_payload = parsed_payload
        except json.JSONDecodeError:
            pass
        new_agent_id = str(command_payload.get("new_agent_id") or "") or None
        succeeded = normalized_result == "applied"
        _record_identity_event(
            db,
            agent_id=payload.agent_id,
            new_agent_id=new_agent_id,
            command_id=command.id,
            event_type=(
                "force_reidentify_installer_scheduled"
                if succeeded
                else "force_reidentify_failed"
            ),
            status="completed" if succeeded else "failed",
            actor=payload.agent_id,
            reason=str(command_payload.get("reason") or "") or None,
            message=payload.message,
        )
        settings_service.record_operational_event(
            "agent_force_reidentify_scheduled" if succeeded else "agent_force_reidentify_failed",
            payload.agent_id,
            payload.message
            or (
                f"Instalador de reidentificacao agendado para {payload.agent_id}; "
                f"nova identidade {new_agent_id}."
                if succeeded
                else f"Falha ao agendar reidentificacao de {payload.agent_id}."
            ),
        )
        return {"status": "acknowledged", "command_id": command_id}

    if command_kind == "upgrade_agent":
        settings_service.record_operational_event(
            "agent_upgrade_scheduled" if normalized_result == "applied" else "agent_upgrade_failed",
            payload.agent_id,
            payload.message or f"Resultado do upgrade do agente {payload.agent_id}: {normalized_result}.",
        )
        return {"status": "acknowledged", "command_id": command_id}

    if command_kind not in {"reboot_now", "scheduled_reboot"}:
        settings_service.record_operational_event(
            "unsupported_agent_command_result",
            payload.agent_id,
            payload.message
            or f"Resultado {normalized_result} recebido para comando nao suportado {command_kind}.",
        )
        return {"status": "acknowledged", "command_id": command_id}

    event_prefix = "scheduled_reboot" if command_kind == "scheduled_reboot" else "manual_reboot"
    if normalized_result == "applied":
        snapshot_repository.update_post_patch_state(
            payload.agent_id,
            post_patch_state="reboot-scheduled",
            post_patch_message=payload.message or f"Reboot aceito pelo agente {payload.agent_id}.",
            reboot_scheduled_at=datetime.now(UTC),
        )
        settings_service.record_operational_event(
            f"{event_prefix}_completed",
            payload.agent_id,
            payload.message or f"Reboot aceito pelo agente {payload.agent_id}.",
        )
    else:
        snapshot_repository.update_post_patch_state(
            payload.agent_id,
            post_patch_state="reboot-failed",
            post_patch_message=payload.message or f"Falha ao executar reboot no agente {payload.agent_id}.",
            reboot_scheduled_at=None,
        )
        settings_service.record_operational_event(
            f"{event_prefix}_failed",
            payload.agent_id,
            payload.message or f"Falha ao executar reboot no agente {payload.agent_id}.",
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
    snapshot_repository = AgentInventorySnapshotRepository(db)

    patch = patch_repository.get_by_id(job.patch_id)
    machine = machine_repository.get_by_id(job.machine_id)

    result = payload.result.lower()
    job.status = "completed" if result == "applied" else "failed"
    job.error_message = payload.error_message
    job.finished_at = datetime.now(UTC)
    job_repository.update(job)

    if machine is not None and result == "applied":
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
                duration_seconds=int((datetime.now(UTC) - job.started_at).total_seconds()) if job.started_at else 0,
                executed_at=datetime.now(UTC),
            )
        ]
    )

    if result == "applied" and patch is not None:
        # Patch instalado com sucesso — remove do catalogo de aprovacoes.
        # O historico fica no ExecutionLog e no job concluido.
        # Proximo inventario reinsere se o pacote voltar a precisar de atualizacao.
        patch_repository.delete(patch)
    elif result == "failed" and patch is not None:
        failure_reason = _classify_job_failure(payload.error_message)
        if failure_reason and failure_reason.startswith("guardrail_"):
            # Falha de guardrail e permanente ate que a configuracao mude.
            # Manter o patch "approved" faria o scheduler criar 3 novos jobs por dia
            # para patches que nunca instalaram sob as configuracoes atuais.
            # Revertemos para "pending" para parar o loop e alertar o operador.
            patch.approval_status = "pending"
            patch.reviewed_by = None
            patch.reviewed_at = None
            patch_repository.update(patch)

    execution_mode = (payload.execution_mode or "").strip().lower()
    if job.platform.lower() == "linux" and execution_mode == "apply":
        settings_service = SettingsService(db)
        if result == "applied":
            post_patch_state = "apply-completed"
            post_patch_message = f"Apply Linux concluido em {job.machine_name}."
            reboot_scheduled_at = None
            settings_service.record_operational_event(
                "linux_apply_completed",
                payload.agent_id,
                f"Apply Linux concluido em {job.machine_name} para o patch {job.patch_id}.",
            )
            if payload.reboot_required:
                reboot_policy = settings_service.get_linux_reboot_policy()
                grace_minutes = settings_service.get_linux_reboot_grace_minutes()
                post_patch_state = "reboot-scheduled" if payload.reboot_scheduled else "reboot-required"
                post_patch_message = payload.reboot_message or (
                    f"Host {job.machine_name} requer reboot apos apply com politica {reboot_policy}."
                )
                reboot_scheduled_at = datetime.now(UTC) if payload.reboot_scheduled else None
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
            snapshot_repository.update_post_patch_state(
                payload.agent_id,
                post_patch_state=post_patch_state,
                post_patch_message=post_patch_message,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=reboot_scheduled_at,
            )
            agent_registry_service.update_post_patch_state(
                payload.agent_id,
                post_patch_state=post_patch_state,
                post_patch_message=post_patch_message,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=reboot_scheduled_at,
            )
        else:
            summary = f"Apply Linux falhou em {job.machine_name} para o patch {job.patch_id}."
            if payload.error_message:
                summary = f"{summary} {payload.error_message}"
            snapshot_repository.update_post_patch_state(
                payload.agent_id,
                post_patch_state="apply-failed",
                post_patch_message=payload.error_message or summary,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=None,
            )
            agent_registry_service.update_post_patch_state(
                payload.agent_id,
                post_patch_state="apply-failed",
                post_patch_message=payload.error_message or summary,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=None,
            )
            settings_service.record_operational_event(
                "linux_apply_failed",
                payload.agent_id,
                summary,
            )
    elif job.platform.lower() == "windows" and execution_mode == "apply":
        settings_service = SettingsService(db)
        if result == "applied":
            post_patch_state = "apply-completed"
            post_patch_message = f"Apply Windows concluido em {job.machine_name}."
            reboot_scheduled_at = None
            settings_service.record_operational_event(
                "windows_apply_completed",
                payload.agent_id,
                f"Apply Windows concluido em {job.machine_name} para o patch {job.patch_id}.",
            )
            if payload.reboot_required:
                reboot_policy = settings_service.get_windows_reboot_policy()
                grace_minutes = settings_service.get_windows_reboot_grace_minutes()
                post_patch_state = "reboot-scheduled" if payload.reboot_scheduled else "reboot-required"
                post_patch_message = payload.reboot_message or (
                    f"Host {job.machine_name} requer reboot apos apply com politica {reboot_policy}."
                )
                reboot_scheduled_at = datetime.now(UTC) if payload.reboot_scheduled else None
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
            snapshot_repository.update_post_patch_state(
                payload.agent_id,
                post_patch_state=post_patch_state,
                post_patch_message=post_patch_message,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=reboot_scheduled_at,
            )
            agent_registry_service.update_post_patch_state(
                payload.agent_id,
                post_patch_state=post_patch_state,
                post_patch_message=post_patch_message,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=reboot_scheduled_at,
            )
        else:
            summary = f"Apply Windows falhou em {job.machine_name} para o patch {job.patch_id}."
            if payload.error_message:
                summary = f"{summary} {payload.error_message}"
            snapshot_repository.update_post_patch_state(
                payload.agent_id,
                post_patch_state="apply-failed",
                post_patch_message=payload.error_message or summary,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=None,
            )
            agent_registry_service.update_post_patch_state(
                payload.agent_id,
                post_patch_state="apply-failed",
                post_patch_message=payload.error_message or summary,
                last_apply_result=result,
                last_apply_at=datetime.now(UTC),
                reboot_scheduled_at=None,
            )
            settings_service.record_operational_event(
                "windows_apply_failed",
                payload.agent_id,
                summary,
            )

    agent_registry_service.heartbeat(payload.agent_id, job.platform, payload.agent_id)
    return {"status": "ok"}
