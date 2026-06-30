import subprocess

from config import AgentConfig


def _run(command: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = "\n".join(
            part.strip()
            for part in [completed.stdout or "", completed.stderr or ""]
            if part.strip()
        ).strip()
        return completed.returncode, output
    except (OSError, subprocess.SubprocessError) as exc:
        return 1, str(exc)


def _resolve_bool(job: dict[str, object], key: str, fallback: bool) -> bool:
    value = job.get(key)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return fallback


def _resolve_timeout(job: dict[str, object], key: str, fallback: int) -> int:
    value = job.get(key)
    try:
        if value is None:
            return fallback
        return max(int(value), 15)
    except (TypeError, ValueError):
        return fallback


def _resolve_grace_minutes(job: dict[str, object], key: str, fallback: int) -> int:
    value = job.get(key)
    try:
        if value is None:
            return fallback
        return max(int(value), 5)
    except (TypeError, ValueError):
        return fallback


def _run_powershell_step(command: str, timeout: int) -> tuple[int, str]:
    return _run(["powershell.exe", "-NoProfile", "-Command", command], timeout=timeout)


def _is_reboot_required() -> bool:
    code, _ = _run_powershell_step(
        "$rebootPath = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired'; if (Test-Path $rebootPath) { exit 0 } else { exit 1 }",
        timeout=20,
    )
    return code == 0


def handle_post_apply_reboot(
    job: dict[str, object],
    reboot_required: bool,
    config: AgentConfig,
) -> tuple[bool, str | None]:
    if not reboot_required:
        return False, None

    reboot_policy = str(job.get("reboot_policy", "manual")).strip().lower()
    reboot_grace_minutes = _resolve_grace_minutes(job, "reboot_grace_minutes", 60)

    if reboot_policy == "manual":
        return False, "Reboot pendente mantido para acao manual no Windows."
    if reboot_policy == "notify":
        return False, "Reboot pendente sinalizado para o operador no Windows."
    if reboot_policy != "maintenance-window":
        return False, f"Politica de reboot Windows desconhecida: {reboot_policy}."
    if not config.enable_host_reboot:
        return False, "Host reboot esta desabilitado neste agente Windows."
    if config.simulate_host_reboot:
        return True, f"Simulacao de reboot Windows para daqui {reboot_grace_minutes} minutos. Nenhum shutdown foi executado."

    seconds = max(reboot_grace_minutes * 60, 60)
    code, output = _run(
        ["shutdown.exe", "/r", "/t", str(seconds), "/c", "Patch Manager scheduled reboot"],
        timeout=config.reboot_command_timeout_seconds,
    )
    if code == 0:
        return True, f"Reboot Windows agendado para daqui {reboot_grace_minutes} minutos."
    return False, output or "Falha ao agendar reboot no host Windows."


def execute_reboot_command(
    command: dict[str, object],
    config: AgentConfig,
) -> tuple[str, str | None]:
    command_type = str(command.get("command_type", "")).strip().lower()
    if command_type not in {"reboot_now", "scheduled_reboot"}:
        return "failed", f"Unsupported command type: {command.get('command_type')}"
    if not config.enable_host_reboot:
        return "failed", "Host reboot esta desabilitado neste agente Windows."
    if config.simulate_host_reboot:
        if command_type == "scheduled_reboot":
            return "applied", "Simulacao de reboot Windows agendado pela janela de manutencao. Nenhum shutdown foi executado."
        return "applied", "Simulacao de reboot Windows manual. Nenhum shutdown foi executado."

    code, output = _run(
        ["shutdown.exe", "/r", "/t", "60", "/c", "Patch Manager scheduled reboot"],
        timeout=config.reboot_command_timeout_seconds,
    )
    if code == 0:
        if command_type == "scheduled_reboot":
            return "applied", "Reboot Windows agendado pela janela de manutencao para 1 minuto a partir de agora."
        return "applied", "Reboot Windows manual agendado para 1 minuto a partir de agora."
    return "failed", output or "Falha ao agendar reboot no host Windows."


# WUA COM API result codes: 2=Succeeded, 3=SucceededWithErrors, 4=Failed, 5=Aborted
_WUA_INSTALL_SCRIPT = """\
$ErrorActionPreference = 'Stop'
try {
    $session = New-Object -ComObject Microsoft.Update.Session
    $searcher = $session.CreateUpdateSearcher()
    # ServerSelection=2 (ssWindowsUpdate) usa Windows Update/Microsoft Update diretamente,
    # ignorando qualquer servidor WSUS/SCCM configurado via GPO. Necessario para o PM
    # operar de forma independente do WSUS.
    $searcher.ServerSelection = 2
    $searchResult = $searcher.Search("IsInstalled=0 and IsHidden=0")
    $count = $searchResult.Updates.Count
    Write-Output "WUA_FOUND:$count"
    if ($count -eq 0) { exit 0 }
    for ($i = 0; $i -lt $count; $i++) {
        Write-Output "WUA_UPDATE:$($searchResult.Updates.Item($i).Title)"
    }
    $downloader = $session.CreateUpdateDownloader()
    $downloader.Updates = $searchResult.Updates
    $dlResult = $downloader.Download()
    Write-Output "WUA_DOWNLOAD:$($dlResult.ResultCode)"
    if ($dlResult.ResultCode -ne 2 -and $dlResult.ResultCode -ne 3) {
        Write-Output "WUA_ERROR:Download falhou (code=$($dlResult.ResultCode))"
        exit 1
    }
    $installer = $session.CreateUpdateInstaller()
    $installer.Updates = $searchResult.Updates
    $installResult = $installer.Install()
    Write-Output "WUA_INSTALL:$($installResult.ResultCode)"
    Write-Output "WUA_REBOOT:$($installResult.RebootRequired)"
    if ($installResult.ResultCode -eq 2 -or $installResult.ResultCode -eq 3) { exit 0 }
    Write-Output "WUA_ERROR:Instalacao falhou (code=$($installResult.ResultCode))"
    exit 1
} catch {
    Write-Output "WUA_ERROR:$_"
    exit 1
}
"""


def _parse_wua_reboot(output: str) -> bool:
    for line in output.splitlines():
        if line.startswith("WUA_REBOOT:"):
            return line[11:].strip().lower() in {"true", "1", "yes"}
    return False


def execute_windows_job(
    job: dict[str, object],
    execution_mode: str,
    config: AgentConfig,
) -> tuple[str, str | None, bool]:
    normalized_mode = execution_mode.strip().lower()

    if normalized_mode != "apply":
        code, output = _run(
            ["powershell.exe", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
            timeout=_resolve_timeout(job, "windows_command_timeout_seconds", config.windows_command_timeout_seconds),
        )
        if code == 0:
            return (
                "applied",
                "[dry-run] Ambiente PowerShell validado. Nenhum patch instalado. "
                "Para executar instalacoes reais, defina PATCH_MANAGER_EXECUTION_MODE=apply "
                "e habilite PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY=true e "
                "PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=true no arquivo .env do agente.",
                False,
            )
        return "failed", output or "Falha ao validar ambiente PowerShell do agente Windows.", False

    if not _resolve_bool(job, "windows_scan_apply_enabled", config.enable_windows_scan_apply):
        return "failed", "Windows apply path is disabled on this host.", False

    download_install_enabled = _resolve_bool(
        job,
        "windows_download_install_enabled",
        config.enable_windows_download_install,
    )
    timeout = _resolve_timeout(job, "windows_command_timeout_seconds", config.windows_command_timeout_seconds)

    if not download_install_enabled:
        code, output = _run_powershell_step(
            "Start-Process UsoClient.exe -ArgumentList 'StartScan' -Wait; 'StartScan completed'",
            timeout=timeout,
        )
        if code != 0:
            return "failed", output or "Falha ao executar StartScan no host Windows.", False
        return (
            "applied",
            "[scan-only] Varredura de atualizacoes concluida via UsoClient. "
            "Nenhum patch foi baixado ou instalado. "
            "Para instalar, defina PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL=true no arquivo .env do agente.",
            _is_reboot_required(),
        )

    # Instalacao sincrona via WUA COM API — retorna resultado real (nao fire-and-forget como UsoClient)
    code, output = _run_powershell_step(_WUA_INSTALL_SCRIPT, timeout=timeout)
    reboot_required = _parse_wua_reboot(output or "")
    if code == 0:
        # Quando WUA_FOUND:0 (patches ja instalados previamente), o script
        # nao emite WUA_REBOOT. Verifica o registry para detectar reboot pendente.
        if not reboot_required:
            reboot_required = _is_reboot_required()
        return "applied", output or "Atualizacoes Windows instaladas via WUA COM API.", reboot_required
    return "failed", output or "Falha ao instalar atualizacoes Windows via WUA COM API.", reboot_required
