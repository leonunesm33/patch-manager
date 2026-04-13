from __future__ import annotations

from datetime import datetime, timedelta
from threading import Lock

from app.schemas.agent import ConnectedAgentResponse


class AgentRegistryService:
    def __init__(self) -> None:
        self._agents: dict[str, dict[str, str | datetime]] = {}
        self._lock = Lock()

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
                "last_seen_at": datetime.utcnow(),
            }

    def count_connected(self, max_age_seconds: int = 120) -> int:
        threshold = datetime.utcnow() - timedelta(seconds=max_age_seconds)
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
        threshold = datetime.utcnow() - timedelta(seconds=max_age_seconds)
        platform_normalized = platform.lower()
        with self._lock:
            return any(
                isinstance(agent.get("last_seen_at"), datetime)
                and agent["last_seen_at"] >= threshold
                and str(agent.get("platform", "")).lower() == platform_normalized
                for agent in self._agents.values()
            )

    def list_connected(self, max_age_seconds: int = 120) -> list[ConnectedAgentResponse]:
        threshold = datetime.utcnow() - timedelta(seconds=max_age_seconds)
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
                    last_seen_at=agent["last_seen_at"],
                )
                for agent in self._agents.values()
                if isinstance(agent.get("last_seen_at"), datetime)
                and agent["last_seen_at"] >= threshold
            ]
        return sorted(agents, key=lambda item: item.last_seen_at, reverse=True)


agent_registry_service = AgentRegistryService()
