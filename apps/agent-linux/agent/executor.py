import os
import fnmatch
import re
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


def _derive_package_name(patch_id: str) -> str:
    for separator in ("=", "_", ":"):
        if separator in patch_id:
            return patch_id.split(separator, 1)[0]
    parts = patch_id.split("-")
    return parts[0] if parts else patch_id


def _is_safe_package_name(package_name: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9][a-z0-9+._-]*", package_name))


def _is_package_allowed(config: AgentConfig, package_name: str) -> bool:
    if not config.allowed_package_patterns:
        return True
    return any(fnmatch.fnmatch(package_name, pattern) for pattern in config.allowed_package_patterns)


def _resolve_runtime_flag(job: dict[str, object], key: str, fallback: bool) -> bool:
    value = job.get(key)
    if value is None:
        return fallback
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _resolve_runtime_patterns(job: dict[str, object], fallback: list[str]) -> list[str]:
    value = job.get("allowed_package_patterns")
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return fallback


def _resolve_runtime_timeout(job: dict[str, object], fallback: int) -> int:
    value = job.get("apt_apply_timeout_seconds")
    try:
        return max(int(value), 30) if value is not None else fallback
    except (TypeError, ValueError):
        return fallback


def _list_upgradable_packages() -> set[str]:
    code, output = _run(["apt", "list", "--upgradable"], timeout=30)
    if code != 0:
        return set()
    packages: set[str] = set()
    for line in output.splitlines():
        entry = line.strip()
        if not entry or entry.lower().startswith("listing..."):
            continue
        package_name = entry.split("/", 1)[0].strip()
        if package_name:
            packages.add(package_name)
    return packages


def _has_security_candidate(package_name: str) -> bool:
    code, output = _run(["apt-cache", "policy", package_name], timeout=30)
    if code != 0:
        return False
    lowered = output.lower()
    return "security" in lowered


def _is_reboot_required() -> bool:
    return os.path.exists("/var/run/reboot-required")


def handle_post_apply_reboot(
    job: dict[str, object],
    reboot_required: bool,
    config: AgentConfig | None,
) -> tuple[bool, str | None]:
    if not reboot_required:
        return False, None

    reboot_policy = str(job.get("reboot_policy", "manual")).strip().lower()
    reboot_grace_minutes = _resolve_runtime_timeout(
        {"apt_apply_timeout_seconds": job.get("reboot_grace_minutes")},
        60,
    )

    if reboot_policy == "manual":
        return False, "Reboot pendente mantido para acao manual."
    if reboot_policy == "notify":
        return False, "Reboot pendente sinalizado para o operador."
    if reboot_policy != "maintenance-window":
        return False, f"Politica de reboot desconhecida: {reboot_policy}."
    if config is None or not config.enable_host_reboot:
        return False, "Host reboot esta desabilitado neste agente."

    code, output = _run(
        ["shutdown", "-r", f"+{reboot_grace_minutes}"],
        timeout=config.reboot_command_timeout_seconds,
    )
    if code == 0:
        return True, f"Reboot agendado para daqui {reboot_grace_minutes} minutos."
    return False, output or "Falha ao agendar reboot no host."


def execute_manual_reboot_command(
    command: dict[str, object],
    config: AgentConfig | None,
) -> tuple[str, str | None]:
    if str(command.get("command_type", "")).strip().lower() != "reboot_now":
        return "failed", f"Unsupported command type: {command.get('command_type')}"
    if config is None or not config.enable_host_reboot:
        return "failed", "Host reboot esta desabilitado neste agente."

    code, output = _run(
        ["shutdown", "-r", "+1"],
        timeout=config.reboot_command_timeout_seconds,
    )
    if code == 0:
        return "applied", "Reboot manual agendado para 1 minuto a partir de agora."
    return "failed", output or "Falha ao agendar reboot manual no host."


def execute_patch_job(job: dict[str, object]) -> tuple[str, str | None]:
    result, error_message, _ = execute_patch_job_with_mode(job, "dry-run", None)
    return result, error_message


def execute_patch_job_with_mode(
    job: dict[str, object],
    execution_mode: str,
    config: AgentConfig | None,
) -> tuple[str, str | None, bool]:
    patch_id = str(job.get("patch_id", ""))
    package_name = _derive_package_name(patch_id)
    normalized_mode = execution_mode.strip().lower()

    if normalized_mode == "apply":
        real_apply_enabled = config.enable_real_apply if config else False
        allow_security_only = config.allow_security_only if config else False
        allowed_package_patterns = config.allowed_package_patterns if config else []
        apt_apply_timeout_seconds = config.apt_apply_timeout_seconds if config else 900

        real_apply_enabled = _resolve_runtime_flag(job, "real_apply_enabled", real_apply_enabled)
        allow_security_only = _resolve_runtime_flag(job, "allow_security_only", allow_security_only)
        allowed_package_patterns = _resolve_runtime_patterns(job, allowed_package_patterns)
        apt_apply_timeout_seconds = _resolve_runtime_timeout(job, apt_apply_timeout_seconds)

        if not real_apply_enabled:
            code, output = _run(["apt-get", "-s", "install", "-y", package_name], timeout=60)
            if code == 0:
                return (
                    "failed",
                    "Real apply is disabled on this host. Simulation succeeded but no package was installed.",
                    False,
                )
            return "failed", output or f"Unable to simulate install for package {package_name}", False

        if not _is_safe_package_name(package_name):
            return "failed", f"Package name {package_name!r} did not pass safety validation.", False

        effective_config = config
        if effective_config is not None:
            effective_config.allowed_package_patterns = allowed_package_patterns

        if effective_config is not None and not _is_package_allowed(effective_config, package_name):
            return "failed", f"Package {package_name} is not allowed by local guardrails.", False

        upgradable_packages = _list_upgradable_packages()
        if package_name not in upgradable_packages:
            return "failed", f"Package {package_name} is not currently upgradable on this host.", False

        if allow_security_only and not _has_security_candidate(package_name):
            return "failed", f"Package {package_name} does not have a security-tagged upgrade candidate.", False

        code, output = _run(
            [
                "apt-get",
                "-o",
                "Dpkg::Options::=--force-confold",
                "--only-upgrade",
                "install",
                "-y",
                package_name,
            ],
            timeout=apt_apply_timeout_seconds,
        )
        if code == 0:
            return "applied", None, _is_reboot_required()
        return "failed", output or f"Unable to apply upgrade for package {package_name}", False

    code, output = _run(["apt-cache", "policy", package_name])
    if code == 0 and output:
        return "applied", None, False
    return "failed", output or f"Unable to inspect package {package_name}", False
