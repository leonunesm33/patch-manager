from datetime import UTC, datetime
import json
from urllib.parse import quote, unquote

from sqlalchemy.orm import Session

from app.repositories.system_setting_repository import SystemSettingRepository


class SettingsService:
    LINUX_AGENT_MODE_KEY = "linux_agent_mode"
    LINUX_GROUP_MODE_PREFIX = "linux_group_mode::"
    LINUX_REAL_APPLY_ENABLED_KEY = "linux_real_apply_enabled"
    LINUX_SECURITY_ONLY_KEY = "linux_allow_security_only"
    LINUX_ALLOWED_PACKAGE_PATTERNS_KEY = "linux_allowed_package_patterns"
    LINUX_APT_APPLY_TIMEOUT_KEY = "linux_apt_apply_timeout"
    LINUX_REBOOT_POLICY_KEY = "linux_reboot_policy"
    LINUX_REBOOT_GRACE_MINUTES_KEY = "linux_reboot_grace_minutes"
    LINUX_REAL_APPLY_ENABLED_BY_KEY = "linux_real_apply_enabled_by"
    LINUX_REAL_APPLY_ENABLED_AT_KEY = "linux_real_apply_enabled_at"
    WINDOWS_SCAN_APPLY_ENABLED_KEY = "windows_scan_apply_enabled"
    WINDOWS_DOWNLOAD_INSTALL_ENABLED_KEY = "windows_download_install_enabled"
    WINDOWS_COMMAND_TIMEOUT_KEY = "windows_command_timeout"
    WINDOWS_REBOOT_POLICY_KEY = "windows_reboot_policy"
    WINDOWS_REBOOT_GRACE_MINUTES_KEY = "windows_reboot_grace_minutes"
    AGENT_BOOTSTRAP_TOKEN_KEY = "agent_bootstrap_token"
    AGENT_INSTALL_SERVER_URL_KEY = "agent_install_server_url"
    OPERATIONAL_EVENTS_KEY = "operational_events"

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
            "real_apply_enabled": self.get_linux_real_apply_enabled(),
            "allow_security_only": self.get_linux_allow_security_only(),
            "allowed_package_patterns": self.get_linux_allowed_package_patterns(),
            "apt_apply_timeout_seconds": self.get_linux_apt_apply_timeout_seconds(),
            "reboot_policy": self.get_linux_reboot_policy(),
            "reboot_grace_minutes": self.get_linux_reboot_grace_minutes(),
            "real_apply_last_enabled_by": self.get_linux_real_apply_last_enabled_by(),
            "real_apply_last_enabled_at": self.get_linux_real_apply_last_enabled_at(),
            "windows_scan_apply_enabled": self.get_windows_scan_apply_enabled(),
            "windows_download_install_enabled": self.get_windows_download_install_enabled(),
            "windows_command_timeout_seconds": self.get_windows_command_timeout_seconds(),
            "windows_reboot_policy": self.get_windows_reboot_policy(),
            "windows_reboot_grace_minutes": self.get_windows_reboot_grace_minutes(),
        }

    def get_linux_real_apply_enabled(self) -> bool:
        setting = self.repository.get(self.LINUX_REAL_APPLY_ENABLED_KEY)
        if setting is None:
            self.repository.upsert(self.LINUX_REAL_APPLY_ENABLED_KEY, "false")
            return False
        return setting.value.strip().lower() in {"1", "true", "yes", "on"}

    def set_linux_real_apply_enabled(self, enabled: bool) -> bool:
        normalized = "true" if enabled else "false"
        self.repository.upsert(self.LINUX_REAL_APPLY_ENABLED_KEY, normalized)
        return enabled

    def get_linux_real_apply_last_enabled_by(self) -> str | None:
        setting = self.repository.get(self.LINUX_REAL_APPLY_ENABLED_BY_KEY)
        if setting is None or not setting.value.strip():
            return None
        return setting.value.strip()

    def get_linux_real_apply_last_enabled_at(self) -> str | None:
        setting = self.repository.get(self.LINUX_REAL_APPLY_ENABLED_AT_KEY)
        if setting is None or not setting.value.strip():
            return None
        return setting.value.strip()

    def record_linux_real_apply_enabled_by(self, username: str) -> None:
        normalized_username = username.strip() or "unknown"
        self.repository.upsert(self.LINUX_REAL_APPLY_ENABLED_BY_KEY, normalized_username)
        self.repository.upsert(
            self.LINUX_REAL_APPLY_ENABLED_AT_KEY,
            datetime.now(UTC).isoformat(),
        )

    def get_linux_allow_security_only(self) -> bool:
        setting = self.repository.get(self.LINUX_SECURITY_ONLY_KEY)
        if setting is None:
            self.repository.upsert(self.LINUX_SECURITY_ONLY_KEY, "false")
            return False
        return setting.value.strip().lower() in {"1", "true", "yes", "on"}

    def set_linux_allow_security_only(self, enabled: bool) -> bool:
        normalized = "true" if enabled else "false"
        self.repository.upsert(self.LINUX_SECURITY_ONLY_KEY, normalized)
        return enabled

    def get_linux_allowed_package_patterns(self) -> list[str]:
        setting = self.repository.get(self.LINUX_ALLOWED_PACKAGE_PATTERNS_KEY)
        if setting is None:
            self.repository.upsert(self.LINUX_ALLOWED_PACKAGE_PATTERNS_KEY, "")
            return []
        return [item.strip() for item in setting.value.split(",") if item.strip()]

    def set_linux_allowed_package_patterns(self, patterns: list[str]) -> list[str]:
        normalized = [item.strip() for item in patterns if item.strip()]
        self.repository.upsert(self.LINUX_ALLOWED_PACKAGE_PATTERNS_KEY, ",".join(normalized))
        return normalized

    def get_linux_apt_apply_timeout_seconds(self) -> int:
        setting = self.repository.get(self.LINUX_APT_APPLY_TIMEOUT_KEY)
        if setting is None:
            self.repository.upsert(self.LINUX_APT_APPLY_TIMEOUT_KEY, "900")
            return 900
        try:
            return max(int(setting.value), 30)
        except ValueError:
            return 900

    def set_linux_apt_apply_timeout_seconds(self, timeout_seconds: int) -> int:
        normalized = max(timeout_seconds, 30)
        self.repository.upsert(self.LINUX_APT_APPLY_TIMEOUT_KEY, str(normalized))
        return normalized

    def get_linux_reboot_policy(self) -> str:
        setting = self.repository.get(self.LINUX_REBOOT_POLICY_KEY)
        if setting is None:
            self.repository.upsert(self.LINUX_REBOOT_POLICY_KEY, "manual")
            return "manual"
        return self._normalize_reboot_policy(setting.value)

    def set_linux_reboot_policy(self, policy: str) -> str:
        normalized = self._normalize_reboot_policy(policy)
        self.repository.upsert(self.LINUX_REBOOT_POLICY_KEY, normalized)
        return normalized

    def get_linux_reboot_grace_minutes(self) -> int:
        setting = self.repository.get(self.LINUX_REBOOT_GRACE_MINUTES_KEY)
        if setting is None:
            self.repository.upsert(self.LINUX_REBOOT_GRACE_MINUTES_KEY, "60")
            return 60
        try:
            return max(int(setting.value), 5)
        except ValueError:
            return 60

    def set_linux_reboot_grace_minutes(self, grace_minutes: int) -> int:
        normalized = max(grace_minutes, 5)
        self.repository.upsert(self.LINUX_REBOOT_GRACE_MINUTES_KEY, str(normalized))
        return normalized

    def get_windows_scan_apply_enabled(self) -> bool:
        setting = self.repository.get(self.WINDOWS_SCAN_APPLY_ENABLED_KEY)
        if setting is None:
            self.repository.upsert(self.WINDOWS_SCAN_APPLY_ENABLED_KEY, "false")
            return False
        return setting.value.strip().lower() in {"1", "true", "yes", "on"}

    def set_windows_scan_apply_enabled(self, enabled: bool) -> bool:
        normalized = "true" if enabled else "false"
        self.repository.upsert(self.WINDOWS_SCAN_APPLY_ENABLED_KEY, normalized)
        return enabled

    def get_windows_download_install_enabled(self) -> bool:
        setting = self.repository.get(self.WINDOWS_DOWNLOAD_INSTALL_ENABLED_KEY)
        if setting is None:
            self.repository.upsert(self.WINDOWS_DOWNLOAD_INSTALL_ENABLED_KEY, "false")
            return False
        return setting.value.strip().lower() in {"1", "true", "yes", "on"}

    def set_windows_download_install_enabled(self, enabled: bool) -> bool:
        normalized = "true" if enabled else "false"
        self.repository.upsert(self.WINDOWS_DOWNLOAD_INSTALL_ENABLED_KEY, normalized)
        return enabled

    def get_windows_command_timeout_seconds(self) -> int:
        setting = self.repository.get(self.WINDOWS_COMMAND_TIMEOUT_KEY)
        if setting is None:
            self.repository.upsert(self.WINDOWS_COMMAND_TIMEOUT_KEY, "60")
            return 60
        try:
            return max(int(setting.value), 15)
        except ValueError:
            return 60

    def set_windows_command_timeout_seconds(self, timeout_seconds: int) -> int:
        normalized = max(timeout_seconds, 15)
        self.repository.upsert(self.WINDOWS_COMMAND_TIMEOUT_KEY, str(normalized))
        return normalized

    def get_windows_reboot_policy(self) -> str:
        setting = self.repository.get(self.WINDOWS_REBOOT_POLICY_KEY)
        if setting is None:
            self.repository.upsert(self.WINDOWS_REBOOT_POLICY_KEY, "manual")
            return "manual"
        return self._normalize_reboot_policy(setting.value)

    def set_windows_reboot_policy(self, policy: str) -> str:
        normalized = self._normalize_reboot_policy(policy)
        self.repository.upsert(self.WINDOWS_REBOOT_POLICY_KEY, normalized)
        return normalized

    def get_windows_reboot_grace_minutes(self) -> int:
        setting = self.repository.get(self.WINDOWS_REBOOT_GRACE_MINUTES_KEY)
        if setting is None:
            self.repository.upsert(self.WINDOWS_REBOOT_GRACE_MINUTES_KEY, "60")
            return 60
        try:
            return max(int(setting.value), 5)
        except ValueError:
            return 60

    def set_windows_reboot_grace_minutes(self, grace_minutes: int) -> int:
        normalized = max(grace_minutes, 5)
        self.repository.upsert(self.WINDOWS_REBOOT_GRACE_MINUTES_KEY, str(normalized))
        return normalized

    def get_agent_bootstrap_token(self) -> str:
        setting = self.repository.get(self.AGENT_BOOTSTRAP_TOKEN_KEY)
        if setting is None or not setting.value.strip():
            self.repository.upsert(self.AGENT_BOOTSTRAP_TOKEN_KEY, "patch-manager-bootstrap-token")
            return "patch-manager-bootstrap-token"
        return setting.value

    def set_agent_bootstrap_token(self, token: str) -> str:
        normalized = token.strip() or "patch-manager-bootstrap-token"
        self.repository.upsert(self.AGENT_BOOTSTRAP_TOKEN_KEY, normalized)
        return normalized

    def get_agent_install_server_url(self) -> str:
        setting = self.repository.get(self.AGENT_INSTALL_SERVER_URL_KEY)
        if setting is None or not setting.value.strip():
            self.repository.upsert(self.AGENT_INSTALL_SERVER_URL_KEY, "http://localhost:8000")
            return "http://localhost:8000"
        return setting.value.rstrip("/")

    def set_agent_install_server_url(self, server_url: str) -> str:
        normalized = server_url.strip().rstrip("/") or "http://localhost:8000"
        self.repository.upsert(self.AGENT_INSTALL_SERVER_URL_KEY, normalized)
        return normalized

    def list_operational_events(self, limit: int = 20) -> list[dict[str, str]]:
        setting = self.repository.get(self.OPERATIONAL_EVENTS_KEY)
        if setting is None or not setting.value.strip():
            return []
        try:
            data = json.loads(setting.value)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        normalized = [
            {
                "event_type": str(item.get("event_type", "")),
                "severity": str(item.get("severity", self._infer_event_severity(str(item.get("event_type", ""))))),
                "actor": str(item.get("actor", "system")),
                "summary": str(item.get("summary", "")),
                "occurred_at": str(item.get("occurred_at", "")),
            }
            for item in data
            if isinstance(item, dict)
        ]
        return normalized[:limit]

    def record_operational_event(self, event_type: str, actor: str, summary: str) -> None:
        current = self.list_operational_events(limit=100)
        current.insert(
            0,
            {
                "event_type": event_type.strip() or "info",
                "severity": self._infer_event_severity(event_type),
                "actor": actor.strip() or "system",
                "summary": summary.strip(),
                "occurred_at": datetime.now(UTC).isoformat(),
            },
        )
        self.repository.upsert(self.OPERATIONAL_EVENTS_KEY, json.dumps(current[:50]))

    def _infer_event_severity(self, event_type: str) -> str:
        normalized = event_type.strip().lower()
        if normalized in {
            "agent_enrollment_rejected",
            "agent_revoked_by_machine_delete",
            "agent_revoked_manual",
            "agent_reintegrated_manual",
            "agent_requeue_from_revoked",
            "linux_real_apply_enabled",
            "linux_reboot_required",
            "linux_manual_reboot_requested",
            "windows_scan_apply_updated",
            "windows_download_install_updated",
            "windows_command_timeout_updated",
            "windows_reboot_required",
            "windows_reboot_scheduled",
            "windows_reboot_policy_updated",
        }:
            return "warn"
        if normalized in {
            "linux_apply_failed",
            "linux_manual_reboot_failed",
            "windows_apply_failed",
        }:
            return "error"
        return "info"

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

    def _normalize_reboot_policy(self, policy: str) -> str:
        normalized = policy.strip().lower()
        if normalized not in {"manual", "notify", "maintenance-window"}:
            return "manual"
        return normalized
