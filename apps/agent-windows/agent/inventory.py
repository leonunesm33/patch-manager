import json
import platform
import socket
import subprocess


def _as_list(value: object) -> list[dict[str, object]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        return [value]
    return []


def _run_powershell_json(script: str) -> dict[str, object] | None:
    try:
        completed = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", script],
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
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
    script = r"""
$hotfixCount = (Get-HotFix | Measure-Object).Count
$pendingCount = 0
$updateSummary = ''
$rebootRequired = $false
$source = 'windows-update'
$pendingUpdates = @()
$installedUpdates = @()

try {
  $session = New-Object -ComObject Microsoft.Update.Session
  $searcher = $session.CreateUpdateSearcher()
  $result = $searcher.Search("IsInstalled=0 and Type='Software'")
  $pendingCount = $result.Updates.Count
  $titles = @()
  for ($i = 0; $i -lt [Math]::Min($result.Updates.Count, 25); $i++) {
    $update = $result.Updates.Item($i)
    $titles += $update.Title
    $kbId = $null
    try {
      if ($update.KBArticleIDs.Count -gt 0) {
        $kbId = "KB$($update.KBArticleIDs[0])"
      }
    } catch {}
    $categories = @()
    try {
      foreach ($category in $update.Categories) {
        $categories += $category.Name
      }
    } catch {}
    $identifier = $update.Title
    try {
      $identifier = $update.Identity.UpdateID
    } catch {}
    $pendingUpdates += [PSCustomObject]@{
      identifier = $identifier
      title = $update.Title
      current_version = $null
      target_version = $null
      source = $source
      summary = ($categories -join '; ')
      kb_id = $kbId
      security_only = (($categories -match 'security').Count -gt 0) -or ($update.Title -match 'Security')
      installed_at = $null
    }
  }
  $updateSummary = ($titles | Select-Object -First 3) -join '; '
} catch {
  $source = 'windows-update-unavailable'
}

$rebootPath = 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired'
if (Test-Path $rebootPath) { $rebootRequired = $true }

$installedUpdates = Get-HotFix |
  Sort-Object InstalledOn -Descending |
  Select-Object -First 20 |
  ForEach-Object {
    [PSCustomObject]@{
      identifier = $_.HotFixID
      title = if ($_.Description) { $_.Description } else { $_.HotFixID }
      current_version = $null
      target_version = $null
      source = if ($_.InstalledBy) { $_.InstalledBy } else { 'windows-update' }
      summary = if ($_.Caption) { $_.Caption } else { $_.Description }
      kb_id = $_.HotFixID
      security_only = ($_.Description -match 'Security')
      installed_at = if ($_.InstalledOn) { ([datetime]$_.InstalledOn).ToString('o') } else { $null }
    }
  }

[PSCustomObject]@{
  installed_update_count = $hotfixCount
  upgradable_packages = $pendingCount
  pending_update_summary = $updateSummary
  reboot_required = $rebootRequired
  windows_update_source = $source
  pending_updates = $pendingUpdates
  installed_updates = $installedUpdates
} | ConvertTo-Json -Depth 5 -Compress
"""
    data = _run_powershell_json(script) or {}
    return {
        "installed_update_count": int(data.get("installed_update_count", 0) or 0),
        "upgradable_packages": int(data.get("upgradable_packages", 0) or 0),
        "pending_update_summary": str(data.get("pending_update_summary", "") or ""),
        "reboot_required": bool(data.get("reboot_required", False)),
        "windows_update_source": str(
            data.get("windows_update_source", "windows-update") or "windows-update"
        ),
        "pending_updates": _as_list(data.get("pending_updates")),
        "installed_updates": _as_list(data.get("installed_updates")),
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
        "pending_updates": windows_metrics["pending_updates"],
        "installed_updates": windows_metrics["installed_updates"],
        "os_name": platform.system(),
        "os_version": platform.version(),
        "kernel_version": platform.release(),
        "agent_version": agent_version,
        "execution_mode": execution_mode,
    }
