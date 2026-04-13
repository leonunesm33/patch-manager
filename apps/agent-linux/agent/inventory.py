import os
import platform
import socket
import subprocess


def _run(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=15,
        )
        return completed.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _count_lines(output: str) -> int:
    return len([line for line in output.splitlines() if line.strip()])


def collect_inventory(agent_version: str, execution_mode: str) -> dict[str, object]:
    hostname = socket.gethostname()
    try:
        primary_ip = socket.gethostbyname(hostname)
    except OSError:
        primary_ip = "127.0.0.1"
    package_manager = "unknown"
    installed_packages = 0
    upgradable_packages = 0

    if os.path.exists("/usr/bin/apt") or os.path.exists("/bin/apt"):
        package_manager = "apt"
        installed_packages = _count_lines(_run(["dpkg-query", "-W", "-f=${Package}\n"]))
        upgradable_output = _run(["apt", "list", "--upgradable"])
        upgradable_packages = max(_count_lines(upgradable_output) - 1, 0)

    reboot_required = os.path.exists("/var/run/reboot-required")

    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "package_manager": package_manager,
        "installed_packages": installed_packages,
        "upgradable_packages": upgradable_packages,
        "reboot_required": reboot_required,
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "agent_version": agent_version,
        "execution_mode": execution_mode,
    }
