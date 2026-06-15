param(
  [string]$OutputRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist")
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AgentRoot = Join-Path $ProjectRoot "agent"
$ServiceScript = Join-Path $AgentRoot "service.py"
$SpecFile = Join-Path $PSScriptRoot "patch-manager-agent-windows.spec"

if (-not (Test-Path $ServiceScript)) {
  throw "Arquivo principal nao encontrado: $ServiceScript"
}

if (-not (Test-Path $SpecFile)) {
  throw "Arquivo spec nao encontrado: $SpecFile"
}

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  throw "Launcher 'py' nao encontrado. Instale Python.org com o launcher habilitado."
}

try {
  & py -3 -m PyInstaller --version | Out-Null
} catch {
  throw "PyInstaller nao encontrado nesse Python. Instale com: py -3 -m pip install pyinstaller"
}

try {
  & py -3 -c "import win32service, win32serviceutil, servicemanager" 2>&1 | Out-Null
} catch {
  throw "pywin32 nao encontrado. Instale com: py -3 -m pip install pywin32"
}

$null = New-Item -ItemType Directory -Force -Path $OutputRoot

py -3 -m PyInstaller `
  --noconfirm `
  --distpath $OutputRoot `
  $SpecFile

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller falhou com codigo $LASTEXITCODE"
}

Write-Host "Build concluido em $OutputRoot"
Write-Host "Nota: o exe registra o servico '$( & py -3 -c 'from agent.service import SERVICE_NAME; print(SERVICE_NAME)' 2>$null || echo 'PatchManagerAgent' )' ao ser executado com: PatchManagerAgentWindows.exe install"
