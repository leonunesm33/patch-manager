from urllib.parse import quote, unquote

from sqlalchemy.orm import Session

from app.repositories.system_setting_repository import SystemSettingRepository


class SettingsService:
    LINUX_AGENT_MODE_KEY = "linux_agent_mode"
    LINUX_GROUP_MODE_PREFIX = "linux_group_mode::"

    def __init__(self, session: Session) -> None:
        self.repository = SystemSettingRepository(session)

    def get_linux_execution_mode(self) -> str:
        setting = self.repository.get(self.LINUX_AGENT_MODE_KEY)
        if setting is None:
            return "dry-run"
        return self._normalize_mode(setting.value)

    def set_linux_execution_mode(self, mode: str) -> str:
        normalized = self._normalize_mode(mode)
        self.repository.upsert(self.LINUX_AGENT_MODE_KEY, normalized)
        return normalized

    def get_linux_group_execution_modes(self, machine_groups: list[str]) -> list[dict[str, str | bool]]:
        normalized_groups = sorted({group.strip() for group in machine_groups if group and group.strip()})
        stored_settings = {
            self._decode_group_key(setting.key): self._normalize_mode(setting.value)
            for setting in self.repository.list_by_prefix(self.LINUX_GROUP_MODE_PREFIX)
        }
        default_mode = self.get_linux_execution_mode()
        return [
            {
                "group_name": group_name,
                "linux_agent_mode": stored_settings.get(group_name, default_mode),
                "uses_default": group_name not in stored_settings,
            }
            for group_name in normalized_groups
        ]

    def set_linux_group_execution_mode(self, machine_group: str, mode: str) -> str:
        normalized_group = machine_group.strip()
        normalized_mode = self._normalize_mode(mode)
        if not normalized_group:
            return normalized_mode
        self.repository.upsert(self._group_key(normalized_group), normalized_mode)
        return normalized_mode

    def resolve_linux_execution_mode(self, machine_group: str | None) -> str:
        default_mode = self.get_linux_execution_mode()
        if machine_group is None or not machine_group.strip():
            return default_mode

        setting = self.repository.get(self._group_key(machine_group.strip()))
        if setting is None:
            return default_mode
        return self._normalize_mode(setting.value)

    def build_execution_settings(self, machine_groups: list[str]) -> dict[str, object]:
        return {
            "linux_agent_mode": self.get_linux_execution_mode(),
            "linux_group_modes": self.get_linux_group_execution_modes(machine_groups),
        }

    def _group_key(self, machine_group: str) -> str:
        return f"{self.LINUX_GROUP_MODE_PREFIX}{quote(machine_group, safe='')}"

    def _decode_group_key(self, key: str) -> str:
        encoded_group = key.removeprefix(self.LINUX_GROUP_MODE_PREFIX)
        return unquote(encoded_group)

    def _normalize_mode(self, mode: str) -> str:
        normalized = mode.strip().lower()
        if normalized not in {"dry-run", "apply"}:
            return "dry-run"
        return normalized
