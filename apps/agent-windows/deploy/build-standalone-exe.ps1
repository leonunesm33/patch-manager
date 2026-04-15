param(
  [string]$OutputRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) "dist")
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$AgentRoot = Join-Path $ProjectRoot "agent"
$MainScript = Join-Path $AgentRoot "main.py"
$SpecFile = Join-Path $PSScriptRoot "patch-manager-agent-windows.spec"

if (-not (Test-Path $MainScript)) {
  throw "Arquivo principal nao encontrado: $MainScript"
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

$null = New-Item -ItemType Directory -Force -Path $OutputRoot

py -3 -m PyInstaller `
  --noconfirm `
  --distpath $OutputRoot `
  $SpecFile

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller falhou com codigo $LASTEXITCODE"
}

Write-Host "Build concluido em $OutputRoot"
