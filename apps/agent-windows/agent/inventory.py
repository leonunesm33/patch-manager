import functools
import json
import logging
import os
import platform
import socket
import subprocess

_logger = logging.getLogger("patch_manager_agent_windows")


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
    except (OSError, subprocess.SubprocessError) as exc:
        _logger.warning("powershell_exec_error: %s", exc)
        return None

    if completed.returncode != 0:
        stderr_snippet = (completed.stderr or "").strip()[:200]
        _logger.warning(
            "powershell_nonzero_exit: rc=%d stderr=%r", completed.returncode, stderr_snippet
        )
        return None

    raw_output = (completed.stdout or "").strip()
    if not raw_output:
        _logger.warning("powershell_empty_output for script: %s", script[:120])
        return None
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError as exc:
        _logger.warning("powershell_json_decode_error: %s | output: %r", exc, raw_output[:200])
        return None
    return parsed if isinstance(parsed, dict) else None


@functools.lru_cache(maxsize=1)
def _collect_hardware_fingerprint() -> str | None:
    override = os.getenv("PATCH_MANAGER_FINGERPRINT_OVERRIDE", "").strip()
    if override:
        return override
    data = _run_powershell_json(
        "Get-CimInstance Win32_ComputerSystemProduct | "
        "Select-Object @{Name='uuid';Expression={$_.UUID}} | ConvertTo-Json -Compress"
    )
    if data is None:
        return None
    value = data.get("uuid")
    return str(value).strip() or None if value else None


_WINDOWS_EDITION_SUFFIXES = (
    "Datacenter",
    "Standard",
    "Enterprise",
    "Essentials",
    "Education",
    "Foundation",
    "Home",
    "Pro",
)


def _parse_windows_os_release(caption: str) -> str | None:
    value = caption.strip()
    if value.startswith("Microsoft "):
        value = value[len("Microsoft ") :]
    if value.startswith("Windows "):
        value = value[len("Windows ") :]
    for suffix in _WINDOWS_EDITION_SUFFIXES:
        if value.endswith(f" {suffix}"):
            value = value[: -(len(suffix) + 1)]
            break
    value = value.strip()
    return value or None


# Cache manual: armazena apenas quando a coleta é bem-sucedida.
# lru_cache cachearia None permanentemente se o PowerShell falhar na
# inicialização do serviço (ex.: WMI ainda carregando), impedindo
# retentativas nos ciclos seguintes.
_os_release_cache: str | None = None
_os_release_collected: bool = False


def _collect_os_release() -> str | None:
    global _os_release_cache, _os_release_collected
    if _os_release_collected:
        return _os_release_cache

    data = _run_powershell_json(
        "Get-CimInstance Win32_OperatingSystem | "
        "Select-Object @{Name='caption';Expression={$_.Caption}} | ConvertTo-Json -Compress"
    )
    if data is None:
        _logger.warning(
            "os_release_collection_failed: Win32_OperatingSystem query returned no data; "
            "os_release will be null this cycle and retried on next inventory. "
            "Ensure the agent exe was built after 2026-08-20 (commit 91feb3e)."
        )
        return None
    value = data.get("caption")
    if not value:
        _logger.warning("os_release_empty_caption: caption field missing or empty in CIM response")
        return None
    result = _parse_windows_os_release(str(value))
    _logger.debug("os_release_collected: raw=%r parsed=%r", value, result)
    # Só marca como coletado se o resultado for válido
    if result is not None:
        _os_release_cache = result
        _os_release_collected = True
    return result


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
  $result = $searcher.Search("IsInstalled=0 and IsHidden=0")
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
      source = if ($update.Type -eq 2) { 'windows-update-driver' } else { $source }
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
        "hardware_fingerprint": _collect_hardware_fingerprint(),
        "os_release": _collect_os_release(),
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
