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

    seconds = max(reboot_grace_minutes * 60, 60)
    code, output = _run(
        ["shutdown.exe", "/r", "/t", str(seconds), "/c", "Patch Manager scheduled reboot"],
        timeout=config.reboot_command_timeout_seconds,
    )
    if code == 0:
        return True, f"Reboot Windows agendado para daqui {reboot_grace_minutes} minutos."
    return False, output or "Falha ao agendar reboot no host Windows."


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
            return "applied", None, False
        return "failed", output or "Falha ao validar ambiente PowerShell do agente Windows.", False

    if not _resolve_bool(job, "windows_scan_apply_enabled", config.enable_windows_scan_apply):
        return "failed", "Windows apply path is disabled on this host.", False

    timeout = _resolve_timeout(job, "windows_command_timeout_seconds", config.windows_command_timeout_seconds)
    code, output = _run_powershell_step(
        "Start-Process UsoClient.exe -ArgumentList 'StartScan' -Wait; 'StartScan completed'",
        timeout=timeout,
    )
    if code != 0:
        return "failed", output or "Falha ao executar StartScan no host Windows.", False

    download_install_enabled = _resolve_bool(
        job,
        "windows_download_install_enabled",
        config.enable_windows_download_install,
    )
    if not download_install_enabled:
        return "applied", None, _is_reboot_required()

    code, output = _run_powershell_step(
        "Start-Process UsoClient.exe -ArgumentList 'StartDownload' -Wait; 'StartDownload completed'",
        timeout=timeout,
    )
    if code != 0:
        return "failed", output or "Falha ao executar StartDownload no host Windows.", False

    code, output = _run_powershell_step(
        "Start-Process UsoClient.exe -ArgumentList 'StartInstall' -Wait; 'StartInstall completed'",
        timeout=timeout,
    )
    if code == 0:
        return "applied", None, _is_reboot_required()
    return "failed", output or "Falha ao executar StartInstall no host Windows.", False
