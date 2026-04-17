import glob
import gzip
import os
import platform
import re
import socket
import subprocess
from datetime import datetime


UPGRADABLE_PATTERN = re.compile(
    r"^(?P<identifier>[^/\s]+)/(?P<source>\S+)\s+(?P<target_version>\S+).*\[upgradable from:\s*(?P<current_version>[^\]]+)\]$"
)
DPKG_LOG_PATTERN = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<action>upgrade|install)\s+(?P<package>\S+)\s+(?P<old_version>\S+)\s+(?P<new_version>\S+)$"
)


def _run(command: list[str], timeout: int = 15) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _count_lines(output: str) -> int:
    return len([line for line in output.splitlines() if line.strip()])


def _collect_apt_upgradable_details(limit: int = 50) -> list[dict[str, object]]:
    upgradable_output = _run(["apt", "list", "--upgradable"], timeout=30)
    details: list[dict[str, object]] = []
    for raw_line in upgradable_output.splitlines()[1:]:
        line = raw_line.strip()
        if not line:
            continue
        match = UPGRADABLE_PATTERN.match(line)
        if match:
            identifier = match.group("identifier")
            source = match.group("source")
            current_version = match.group("current_version")
            target_version = match.group("target_version")
        else:
            parts = line.split()
            package_token = parts[0] if parts else "unknown"
            identifier = package_token.split("/", 1)[0]
            source = package_token.split("/", 1)[1] if "/" in package_token else "unknown"
            target_version = parts[1] if len(parts) > 1 else None
            current_match = re.search(r"\[upgradable from:\s*([^\]]+)\]", line)
            current_version = current_match.group(1) if current_match else None

        details.append(
            {
                "identifier": identifier,
                "title": identifier,
                "current_version": current_version,
                "target_version": target_version,
                "source": source,
                "summary": line,
                "kb_id": None,
                "security_only": "security" in line.lower() or "security" in str(source).lower(),
                "installed_at": None,
            }
        )
        if len(details) >= limit:
            break
    return details


def _read_log_lines(path: str) -> list[str]:
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8", errors="ignore") as handle:
                return handle.readlines()
        with open(path, encoding="utf-8", errors="ignore") as handle:
            return handle.readlines()
    except OSError:
        return []


def _collect_recent_dpkg_updates(limit: int = 20) -> list[dict[str, object]]:
    log_paths = sorted(
        glob.glob("/var/log/dpkg.log*"),
        key=lambda path: os.path.getmtime(path) if os.path.exists(path) else 0,
        reverse=True,
    )
    seen: set[tuple[str, str, str]] = set()
    details: list[dict[str, object]] = []

    for log_path in log_paths:
        for raw_line in reversed(_read_log_lines(log_path)):
            line = raw_line.strip()
            if not line:
                continue
            match = DPKG_LOG_PATTERN.match(line)
            if match is None:
                continue

            package_name = match.group("package").split(":", 1)[0]
            old_version = match.group("old_version")
            new_version = match.group("new_version")
            dedupe_key = (package_name, old_version, new_version)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            try:
                installed_at = datetime.strptime(
                    f"{match.group('date')} {match.group('time')}",
                    "%Y-%m-%d %H:%M:%S",
                ).isoformat()
            except ValueError:
                installed_at = None

            details.append(
                {
                    "identifier": package_name,
                    "title": package_name,
                    "current_version": old_version if old_version != "<none>" else None,
                    "target_version": new_version,
                    "source": match.group("action"),
                    "summary": (
                        f"{match.group('action')} de {old_version} para {new_version}"
                        if old_version != "<none>"
                        else f"{match.group('action')} em {new_version}"
                    ),
                    "kb_id": None,
                    "security_only": False,
                    "installed_at": installed_at,
                }
            )
            if len(details) >= limit:
                return details

    return details


def collect_inventory(agent_version: str, execution_mode: str) -> dict[str, object]:
    hostname = socket.gethostname()
    try:
        primary_ip = socket.gethostbyname(hostname)
    except OSError:
        primary_ip = "127.0.0.1"
    package_manager = "unknown"
    installed_packages = 0
    upgradable_packages = 0
    pending_updates: list[dict[str, object]] = []
    installed_updates: list[dict[str, object]] = []

    if os.path.exists("/usr/bin/apt") or os.path.exists("/bin/apt"):
        package_manager = "apt"
        installed_packages = _count_lines(_run(["dpkg-query", "-W", "-f=${Package}\n"]))
        pending_updates = _collect_apt_upgradable_details()
        upgradable_packages = len(pending_updates)
        installed_updates = _collect_recent_dpkg_updates()

    reboot_required = os.path.exists("/var/run/reboot-required")

    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "package_manager": package_manager,
        "installed_packages": installed_packages,
        "upgradable_packages": upgradable_packages,
        "reboot_required": reboot_required,
        "installed_update_count": len(installed_updates),
        "pending_update_summary": "; ".join(item["title"] for item in pending_updates[:3]),
        "pending_updates": pending_updates,
        "installed_updates": installed_updates,
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "agent_version": agent_version,
        "execution_mode": execution_mode,
    }
