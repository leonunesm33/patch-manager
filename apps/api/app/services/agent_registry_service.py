from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from threading import Lock

from app.schemas.agent import AgentCommandResponse, ConnectedAgentResponse


class AgentRegistryService:
    DEFAULT_MAX_AGE_SECONDS = 120

    def __init__(self) -> None:
        self._agents: dict[str, dict[str, str | datetime]] = {}
        self._commands: dict[str, list[dict[str, object]]] = {}
        self._lock = Lock()

    def _threshold(self, max_age_seconds: int | None = None) -> datetime:
        effective_max_age = max_age_seconds if max_age_seconds is not None else self.DEFAULT_MAX_AGE_SECONDS
        return datetime.utcnow() - timedelta(seconds=effective_max_age)

    def heartbeat(self, agent_id: str, platform: str, hostname: str) -> None:
        with self._lock:
            current = self._agents.get(agent_id, {})
            self._agents[agent_id] = {
                "agent_id": agent_id,
                "platform": platform,
                "hostname": hostname,
                "os_name": str(current.get("os_name", platform)),
                "os_version": str(current.get("os_version", "unknown")),
                "kernel_version": str(current.get("kernel_version", "unknown")),
                "agent_version": str(current.get("agent_version", "unknown")),
                "execution_mode": str(current.get("execution_mode", "unknown")),
                "primary_ip": str(current.get("primary_ip", "")),
                "package_manager": str(current.get("package_manager", "")),
                "installed_packages": current.get("installed_packages"),
                "upgradable_packages": current.get("upgradable_packages"),
                "reboot_required": current.get("reboot_required"),
                "installed_update_count": current.get("installed_update_count"),
                "pending_update_summary": str(current.get("pending_update_summary", "")),
                "windows_update_source": str(current.get("windows_update_source", "")),
                "last_seen_at": datetime.utcnow(),
            }

    def check_in(
        self,
        agent_id: str,
        platform: str,
        hostname: str,
        os_name: str,
        os_version: str,
        kernel_version: str,
        agent_version: str,
        execution_mode: str,
    ) -> None:
        with self._lock:
            self._agents[agent_id] = {
                "agent_id": agent_id,
                "platform": platform,
                "hostname": hostname,
                "os_name": os_name,
                "os_version": os_version,
                "kernel_version": kernel_version,
                "agent_version": agent_version,
                "execution_mode": execution_mode,
                "primary_ip": str(self._agents.get(agent_id, {}).get("primary_ip", "")),
                "package_manager": str(self._agents.get(agent_id, {}).get("package_manager", "")),
                "installed_packages": self._agents.get(agent_id, {}).get("installed_packages"),
                "upgradable_packages": self._agents.get(agent_id, {}).get("upgradable_packages"),
                "reboot_required": self._agents.get(agent_id, {}).get("reboot_required"),
                "installed_update_count": self._agents.get(agent_id, {}).get("installed_update_count"),
                "pending_update_summary": str(self._agents.get(agent_id, {}).get("pending_update_summary", "")),
                "windows_update_source": str(self._agents.get(agent_id, {}).get("windows_update_source", "")),
                "last_seen_at": datetime.utcnow(),
            }

    def update_inventory(
        self,
        agent_id: str,
        platform: str,
        hostname: str,
        primary_ip: str,
        package_manager: str,
        installed_packages: int,
        upgradable_packages: int,
        reboot_required: bool,
        installed_update_count: int | None,
        pending_update_summary: str | None,
        windows_update_source: str | None,
        os_name: str,
        os_version: str,
        kernel_version: str,
        agent_version: str,
        execution_mode: str,
    ) -> None:
        with self._lock:
            self._agents[agent_id] = {
                "agent_id": agent_id,
                "platform": platform,
                "hostname": hostname,
                "os_name": os_name,
                "os_version": os_version,
                "kernel_version": kernel_version,
                "agent_version": agent_version,
                "execution_mode": execution_mode,
                "primary_ip": primary_ip,
                "package_manager": package_manager,
                "installed_packages": installed_packages,
                "upgradable_packages": upgradable_packages,
                "reboot_required": reboot_required,
                "installed_update_count": installed_update_count,
                "pending_update_summary": pending_update_summary or "",
                "windows_update_source": windows_update_source or "",
                "last_seen_at": datetime.utcnow(),
            }

    def count_connected(self, max_age_seconds: int = 120) -> int:
        threshold = self._threshold(max_age_seconds)
        with self._lock:
            return len(
                [
                    agent
                    for agent in self._agents.values()
                    if isinstance(agent.get("last_seen_at"), datetime)
                    and agent["last_seen_at"] >= threshold
                ]
            )

    def has_platform(self, platform: str, max_age_seconds: int = 120) -> bool:
        threshold = self._threshold(max_age_seconds)
        platform_normalized = platform.lower()
        with self._lock:
            return any(
                isinstance(agent.get("last_seen_at"), datetime)
                and agent["last_seen_at"] >= threshold
                and str(agent.get("platform", "")).lower() == platform_normalized
                for agent in self._agents.values()
            )

    def list_connected(self, max_age_seconds: int = 120) -> list[ConnectedAgentResponse]:
        threshold = self._threshold(max_age_seconds)
        with self._lock:
            agents = [
                ConnectedAgentResponse(
                    agent_id=str(agent["agent_id"]),
                    platform=str(agent["platform"]),
                    hostname=str(agent["hostname"]),
                    os_name=str(agent["os_name"]),
                    os_version=str(agent["os_version"]),
                    kernel_version=str(agent["kernel_version"]),
                    agent_version=str(agent["agent_version"]),
                    execution_mode=str(agent.get("execution_mode", "")) or None,
                    primary_ip=str(agent.get("primary_ip", "")) or None,
                    package_manager=str(agent.get("package_manager", "")) or None,
                    installed_packages=(
                        int(agent["installed_packages"])
                        if agent.get("installed_packages") is not None
                        else None
                    ),
                    upgradable_packages=(
                        int(agent["upgradable_packages"])
                        if agent.get("upgradable_packages") is not None
                        else None
                    ),
                    reboot_required=(
                        bool(agent["reboot_required"])
                        if agent.get("reboot_required") is not None
                        else None
                    ),
                    installed_update_count=(
                        int(agent["installed_update_count"])
                        if agent.get("installed_update_count") is not None
                        else None
                    ),
                    pending_update_summary=str(agent.get("pending_update_summary", "")) or None,
                    windows_update_source=str(agent.get("windows_update_source", "")) or None,
                    last_seen_at=agent["last_seen_at"],
                )
                for agent in self._agents.values()
                if isinstance(agent.get("last_seen_at"), datetime)
                and agent["last_seen_at"] >= threshold
            ]
        return sorted(agents, key=lambda item: item.last_seen_at, reverse=True)

    def get_connected(self, agent_id: str, max_age_seconds: int = 120) -> ConnectedAgentResponse | None:
        threshold = self._threshold(max_age_seconds)
        with self._lock:
            agent = self._agents.get(agent_id)
            if agent is None:
                return None
            if not isinstance(agent.get("last_seen_at"), datetime) or agent["last_seen_at"] < threshold:
                return None
            return ConnectedAgentResponse(
                agent_id=str(agent["agent_id"]),
                platform=str(agent["platform"]),
                hostname=str(agent["hostname"]),
                os_name=str(agent["os_name"]),
                os_version=str(agent["os_version"]),
                kernel_version=str(agent["kernel_version"]),
                agent_version=str(agent["agent_version"]),
                execution_mode=str(agent.get("execution_mode", "")) or None,
                primary_ip=str(agent.get("primary_ip", "")) or None,
                package_manager=str(agent.get("package_manager", "")) or None,
                installed_packages=(
                    int(agent["installed_packages"])
                    if agent.get("installed_packages") is not None
                    else None
                ),
                upgradable_packages=(
                    int(agent["upgradable_packages"])
                    if agent.get("upgradable_packages") is not None
                    else None
                ),
                reboot_required=(
                    bool(agent["reboot_required"])
                    if agent.get("reboot_required") is not None
                    else None
                ),
                installed_update_count=(
                    int(agent["installed_update_count"])
                    if agent.get("installed_update_count") is not None
                    else None
                ),
                pending_update_summary=str(agent.get("pending_update_summary", "")) or None,
                windows_update_source=str(agent.get("windows_update_source", "")) or None,
                last_seen_at=agent["last_seen_at"],
            )

    def is_connected(self, agent_id: str, max_age_seconds: int = 120) -> bool:
        return self.get_connected(agent_id, max_age_seconds=max_age_seconds) is not None

    def disconnect(self, agent_id: str) -> None:
        with self._lock:
            self._agents.pop(agent_id, None)
            self._commands.pop(agent_id, None)

    def enqueue_command(
        self,
        agent_id: str,
        command_type: str,
        payload: dict[str, str | int | bool | None] | None = None,
    ) -> AgentCommandResponse:
        command = {
            "id": str(uuid4()),
            "command_type": command_type,
            "target_agent_id": agent_id,
            "payload": payload or {},
            "created_at": datetime.utcnow(),
        }
        with self._lock:
            self._commands.setdefault(agent_id, []).append(command)
        return AgentCommandResponse.model_validate(command)

    def pop_next_command(self, agent_id: str) -> AgentCommandResponse | None:
        with self._lock:
            queue = self._commands.get(agent_id, [])
            if not queue:
                return None
            command = queue.pop(0)
            if not queue:
                self._commands.pop(agent_id, None)
        return AgentCommandResponse.model_validate(command)


agent_registry_service = AgentRegistryService()
