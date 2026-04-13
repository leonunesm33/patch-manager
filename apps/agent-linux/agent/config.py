import os
from dataclasses import dataclass
from pathlib import Path


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
    agent_id: str
    platform: str
    agent_version: str
    api_base: str
    agent_key: str
    default_execution_mode: str
    heartbeat_interval_seconds: int
    idle_sleep_seconds: int
    inventory_interval_seconds: int
    failure_backoff_seconds: int
    request_timeout_seconds: int
    log_level: str
    log_file: str | None
    log_to_stdout: bool


def load_config() -> AgentConfig:
    log_file = os.getenv("PATCH_MANAGER_LOG_FILE")
    if log_file:
        Path(log_file).expanduser().parent.mkdir(parents=True, exist_ok=True)

    return AgentConfig(
        agent_id=os.getenv("PATCH_MANAGER_AGENT_ID", "linux-agent-01"),
        platform="linux",
        agent_version=os.getenv("PATCH_MANAGER_AGENT_VERSION", "0.2.0"),
        api_base=os.getenv("PATCH_MANAGER_API", "http://localhost:8000/api/v1/agents"),
        agent_key=os.getenv("PATCH_MANAGER_AGENT_KEY", "patch-manager-agent-key"),
        default_execution_mode=os.getenv("PATCH_MANAGER_EXECUTION_MODE", "dry-run").strip().lower(),
        heartbeat_interval_seconds=max(_read_int("PATCH_MANAGER_HEARTBEAT_INTERVAL", 10), 3),
        idle_sleep_seconds=max(_read_int("PATCH_MANAGER_IDLE_SLEEP", 5), 1),
        inventory_interval_seconds=max(_read_int("PATCH_MANAGER_INVENTORY_INTERVAL", 60), 15),
        failure_backoff_seconds=max(_read_int("PATCH_MANAGER_FAILURE_BACKOFF", 10), 3),
        request_timeout_seconds=max(_read_int("PATCH_MANAGER_REQUEST_TIMEOUT", 10), 3),
        log_level=os.getenv("PATCH_MANAGER_LOG_LEVEL", "INFO").strip().upper(),
        log_file=log_file,
        log_to_stdout=_read_bool("PATCH_MANAGER_LOG_TO_STDOUT", True),
    )
