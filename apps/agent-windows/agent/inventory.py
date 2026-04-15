import platform
import socket
import json
import subprocess


def _run_powershell_json(script: str) -> dict[str, object] | None:
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=45,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    if completed.returncode != 0:
        return None

    raw_output = (completed.stdout or "").strip()
    if not raw_output:
        return None
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _collect_windows_update_metrics() -> dict[str, object]:
    script = """
$hotfixCount = (Get-HotFix | Measure-Object).Count
$updateSummary = ''
$pendingCount = 0
$rebootRequired = $false
$source = 'windows-update'
try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Software'")
  $pendingCount = $result.Updates.Count
  $titles = @()
  for ($i = 0; $i -lt [Math]::Min($result.Updates.Count, 3); $i++) {
    $titles += $result.Updates.Item($i).Title
  }
  $updateSummary = ($titles -join '; ')
} catch {
  $source = 'windows-update-unavailable'
}
$rebootPath = 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update\\RebootRequired'
if (Test-Path $rebootPath) { $rebootRequired = $true }
[PSCustomObject]@{
  installed_update_count = $hotfixCount
  upgradable_packages = $pendingCount
  pending_update_summary = $updateSummary
  reboot_required = $rebootRequired
  windows_update_source = $source
} | ConvertTo-Json -Compress
"""
    data = _run_powershell_json(script) or {}
    return {
        "installed_update_count": int(data.get("installed_update_count", 0) or 0),
        "upgradable_packages": int(data.get("upgradable_packages", 0) or 0),
        "pending_update_summary": str(data.get("pending_update_summary", "") or ""),
        "reboot_required": bool(data.get("reboot_required", False)),
        "windows_update_source": str(data.get("windows_update_source", "windows-update") or "windows-update"),
    }


def collect_inventory(agent_version: str, execution_mode: str) -> dict[str, object]:
    hostname = socket.gethostname()
    try:
        primary_ip = socket.gethostbyname(hostname)
    except OSError:
        primary_ip = "127.0.0.1"

    windows_metrics = _collect_windows_update_metrics()

    return {
        "hostname": hostname,
        "primary_ip": primary_ip,
        "package_manager": "windows-update",
        "installed_packages": windows_metrics["installed_update_count"],
        "upgradable_packages": windows_metrics["upgradable_packages"],
        "reboot_required": windows_metrics["reboot_required"],
        "installed_update_count": windows_metrics["installed_update_count"],
        "pending_update_summary": windows_metrics["pending_update_summary"],
        "windows_update_source": windows_metrics["windows_update_source"],
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "agent_version": agent_version,
        "execution_mode": execution_mode,
    }
