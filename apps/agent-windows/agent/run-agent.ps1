$ErrorActionPreference = 'Stop'

function Resolve-RealPython {
  $candidates = @()

  $pyCommand = Get-Command py -ErrorAction SilentlyContinue
  if ($pyCommand) {
    try {
      $pythonFromLauncher = & $pyCommand.Source -3 -c "import sys; print(sys.executable)" 2>$null
      if ($pythonFromLauncher) {
        $candidates += $pythonFromLauncher.Trim()
      }
    } catch {}
  }

  $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
  if ($pythonCommand -and $pythonCommand.Source -and $pythonCommand.Source -notlike "*WindowsApps\python.exe") {
    $candidates += $pythonCommand.Source
  }

  $python3Command = Get-Command python3 -ErrorAction SilentlyContinue
  if ($python3Command -and $python3Command.Source) {
    $candidates += $python3Command.Source
  }

  foreach ($candidate in $candidates | Select-Object -Unique) {
    if ($candidate -and (Test-Path $candidate)) {
      return $candidate
    }
  }

  return $null
}

$ScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$InstallRoot = Split-Path -Parent $ScriptRoot
$ExePath = Join-Path $InstallRoot "dist\PatchManagerAgentWindows.exe"
$EmbeddedPython = Join-Path $InstallRoot "runtime\python.exe"
$MainScript = Join-Path $ScriptRoot "main.py"
$DefaultEnvFile = "C:\ProgramData\PatchManager\agent-windows.env"

if (-not $env:PATCH_MANAGER_ENV_FILE -and (Test-Path $DefaultEnvFile)) {
  $env:PATCH_MANAGER_ENV_FILE = $DefaultEnvFile
}

if (Test-Path $ExePath) {
  & $ExePath
  exit $LASTEXITCODE
}

if (Test-Path $EmbeddedPython) {
  & $EmbeddedPython $MainScript
  exit $LASTEXITCODE
}

$PythonExecutable = Resolve-RealPython
if ($PythonExecutable) {
  & $PythonExecutable $MainScript
  exit $LASTEXITCODE
}

Write-Error "Nenhum runtime do agente Windows foi encontrado. Esperado: dist\\PatchManagerAgentWindows.exe, runtime\\python.exe ou um Python real no host."
exit 1
