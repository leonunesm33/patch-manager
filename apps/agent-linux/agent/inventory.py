import functools
import glob
import gzip
import json
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


@functools.lru_cache(maxsize=1)
def _collect_hardware_fingerprint() -> str | None:
    override = os.getenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "").strip()
    if override:
        return override
    output = _run(["sudo", "cat", "/sys/class/dmi/id/product_uuid"])
    return output.strip() or None


# PackageKit/Cockpit priority → severity mapping
_APT_PRIORITY_TO_SEVERITY: dict[str, str] = {
    "required": "critical",
    "important": "important",
    "standard": "moderate",
    "optional": "low",
    "extra": "low",
}


def _get_package_info_via_python_apt() -> dict[str, dict[str, str]] | None:
    """Use apt_pkg (same C library as PackageKit/Cockpit) to get category and severity.

    Returns {pkg_name: {category, severity, current_version, target_version, is_new_install}}
    for ALL packages involved in a dist-upgrade — matches Cockpit's total package count.

    Security classification uses apt_pkg's file_list for each candidate version, which
    enumerates ALL repository origins exactly as PackageKit does. A package is "security"
    if its candidate version's file_list contains a security-tagged archive.

    Returns None if python3-apt is unavailable.
    """
    script = (
        "import apt_pkg, json\n"
        "apt_pkg.init_config()\n"
        "apt_pkg.init_system()\n"
        "cache = apt_pkg.Cache()\n"
        "dep_cache = apt_pkg.DepCache(cache)\n"
        "dep_cache.upgrade(True)\n"
        "SEV = {'required':'critical','important':'important','standard':'moderate',\n"
        "       'optional':'low','extra':'low'}\n"
        "r = {}\n"
        "for pkg in cache.packages:\n"
        "    if not (dep_cache.marked_upgrade(pkg) or dep_cache.marked_install(pkg)): continue\n"
        "    cand = dep_cache.get_candidate_ver(pkg)\n"
        "    if not cand: continue\n"
        "    is_sec = is_upd = is_bp = False\n"
        "    for f, idx in cand.file_list:\n"
        "        a = (f.archive or '').lower()\n"
        "        if 'security' in a: is_sec = True\n"
        "        elif 'updates' in a: is_upd = True\n"
        "        elif 'backports' in a or 'proposed' in a: is_bp = True\n"
        "    cat = 'security' if is_sec else ('bugfix' if is_upd else ('enhancement' if is_bp else 'normal'))\n"
        "    cur = pkg.current_ver.ver_str if pkg.current_ver else None\n"
        "    r[pkg.name] = {'category':cat, 'severity':SEV.get((cand.priority_str or '').lower(),'unknown'),\n"
        "                   'current_version':cur, 'target_version':cand.ver_str, 'is_new_install':cur is None}\n"
        "print(json.dumps(r))\n"
    )
    output = _run(["python3", "-c", script], timeout=90)
    if not output:
        return None
    try:
        # apt_pkg writes progress messages to stdout before the JSON; use the last line
        last_line = output.strip().split("\n")[-1]
        return json.loads(last_line)
    except (json.JSONDecodeError, ValueError):
        return None


def _infer_category_from_source(source: str) -> str:
    """Infer PackageKit category from apt source/archive name (fallback when python3-apt unavailable).

    Mirrors Cockpit's security rule: a package is 'security' only when the source field
    contains 'security' AND does NOT also contain 'updates' (packages promoted to the
    updates pocket are categorized as 'bugfix', not 'security').
    Third-party PPA packages (archive 'jammy' without a pocket qualifier) are 'normal',
    matching the PackageKit/Cockpit label for such packages.
    """
    s = source.lower()
    has_security = "security" in s
    has_updates = "updates" in s
    if has_security and not has_updates:
        return "security"
    if has_updates:
        return "bugfix"
    if "backports" in s or "proposed" in s:
        return "enhancement"
    return "normal"


def _collect_apt_upgradable_details(limit: int = 500) -> list[dict[str, object]]:
    # Prefer python3-apt (dist-upgrade aware, correct security detection)
    pkg_info = _get_package_info_via_python_apt()

    if pkg_info is not None:
        details: list[dict[str, object]] = []
        for name, info in pkg_info.items():
            category = info.get("category", "unknown")
            severity = info.get("severity", "unknown")
            current_version = info.get("current_version")
            target_version = info.get("target_version")
            is_new = info.get("is_new_install", False)
            source = "new-install" if is_new else "upgrade"
            summary = (
                f"{name} {current_version} -> {target_version}"
                if current_version
                else f"{name} {target_version} (new)"
            )
            details.append(
                {
                    "identifier": name,
                    "title": name,
                    "current_version": current_version,
                    "target_version": target_version,
                    "source": source,
                    "summary": summary,
                    "kb_id": None,
                    "security_only": category == "security",
                    "category": category,
                    "severity": severity,
                    "installed_at": None,
                }
            )
            if len(details) >= limit:
                break
        return details

    # Fallback: apt list --upgradable (no dist-upgrade new packages, basic security detection)
    upgradable_output = _run(["apt", "list", "--upgradable"], timeout=30)
    details = []
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

        category = _infer_category_from_source(source)
        is_security = category == "security"
        details.append(
            {
                "identifier": identifier,
                "title": identifier,
                "current_version": current_version,
                "target_version": target_version,
                "source": source,
                "summary": line,
                "kb_id": None,
                "security_only": is_security,
                "category": category,
                "severity": "important" if is_security else "low",
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
        "hardware_fingerprint": _collect_hardware_fingerprint(),
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
