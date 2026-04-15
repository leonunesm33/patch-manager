import os
from dataclasses import dataclass
from pathlib import Path


def _load_env_file() -> str | None:
    env_candidates = [
        os.getenv("PATCH_MANAGER_ENV_FILE"),
        str(Path.cwd() / ".env"),
        str(Path(__file__).resolve().parent.parent / ".env"),
    ]
    for candidate in env_candidates:
        if not candidate:
            continue
        env_path = Path(candidate).expanduser()
        if not env_path.exists() or not env_path.is_file():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))
        return str(env_path)
    return None


def save_env_values(env_file_path: str | None, values: dict[str, str]) -> None:
    if env_file_path is None:
        return
    env_path = Path(env_file_path).expanduser()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    existing_lines = env_path.read_text(encoding="utf-8").splitlines() if env_path.exists() else []
    updated_keys: set[str] = set()
    rewritten: list[str] = []

    for raw_line in existing_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            rewritten.append(raw_line)
            continue

        key, _ = raw_line.split("=", 1)
        normalized_key = key.strip()
        if normalized_key in values:
            rewritten.append(f"{normalized_key}={values[normalized_key]}")
            updated_keys.add(normalized_key)
        else:
            rewritten.append(raw_line)

    for key, value in values.items():
        if key not in updated_keys:
            rewritten.append(f"{key}={value}")

    env_path.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
    for key, value in values.items():
        os.environ[key] = value


def _read_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _read_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(slots=True)
class AgentConfig:
    env_file_path: str | None
    agent_id: str
    platform: str
    agent_version: str
    api_base: str
    agent_key: str
    bootstrap_token: str
    default_execution_mode: str
    enable_real_apply: bool
    allow_security_only: bool
    allowed_package_patterns: list[str]
    apt_apply_timeout_seconds: int
    enable_host_reboot: bool
    reboot_command_timeout_seconds: int
    heartbeat_interval_seconds: int
    idle_sleep_seconds: int
    inventory_interval_seconds: int
    failure_backoff_seconds: int
    request_timeout_seconds: int
    log_level: str
    log_file: str | None
    log_to_stdout: bool


def load_config() -> AgentConfig:
    env_file_path = _load_env_file()
    if env_file_path is None:
        env_file_path = str(Path.cwd() / ".env")
    log_file = os.getenv("PATCH_MANAGER_LOG_FILE")
    if log_file:
        Path(log_file).expanduser().parent.mkdir(parents=True, exist_ok=True)

    return AgentConfig(
        env_file_path=env_file_path,
        agent_id=os.getenv("PATCH_MANAGER_AGENT_ID", "linux-agent-01"),
        platform="linux",
        agent_version=os.getenv("PATCH_MANAGER_AGENT_VERSION", "0.2.0"),
        api_base=os.getenv("PATCH_MANAGER_API", "http://localhost:8000/api/v1/agents"),
        agent_key=os.getenv("PATCH_MANAGER_AGENT_KEY", "").strip(),
        bootstrap_token=os.getenv("PATCH_MANAGER_BOOTSTRAP_TOKEN", "").strip(),
        default_execution_mode=os.getenv("PATCH_MANAGER_EXECUTION_MODE", "dry-run").strip().lower(),
        enable_real_apply=_read_bool("PATCH_MANAGER_ENABLE_REAL_APPLY", False),
        allow_security_only=_read_bool("PATCH_MANAGER_ALLOW_SECURITY_ONLY", False),
        allowed_package_patterns=[
            item.strip()
            for item in os.getenv("PATCH_MANAGER_ALLOWED_PACKAGE_PATTERNS", "").split(",")
            if item.strip()
        ],
        apt_apply_timeout_seconds=max(_read_int("PATCH_MANAGER_APT_APPLY_TIMEOUT", 900), 30),
        enable_host_reboot=_read_bool("PATCH_MANAGER_ENABLE_HOST_REBOOT", False),
        reboot_command_timeout_seconds=max(_read_int("PATCH_MANAGER_REBOOT_COMMAND_TIMEOUT", 30), 5),
        heartbeat_interval_seconds=max(_read_int("PATCH_MANAGER_HEARTBEAT_INTERVAL", 10), 3),
        idle_sleep_seconds=max(_read_int("PATCH_MANAGER_IDLE_SLEEP", 5), 1),
        inventory_interval_seconds=max(_read_int("PATCH_MANAGER_INVENTORY_INTERVAL", 60), 15),
        failure_backoff_seconds=max(_read_int("PATCH_MANAGER_FAILURE_BACKOFF", 10), 3),
        request_timeout_seconds=max(_read_int("PATCH_MANAGER_REQUEST_TIMEOUT", 10), 3),
        log_level=os.getenv("PATCH_MANAGER_LOG_LEVEL", "INFO").strip().upper(),
        log_file=log_file,
        log_to_stdout=_read_bool("PATCH_MANAGER_LOG_TO_STDOUT", True),
    )
