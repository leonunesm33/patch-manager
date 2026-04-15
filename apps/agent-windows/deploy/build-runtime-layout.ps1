param(
  [string]$PythonRoot = "",
  [string]$OutputRoot = (Join-Path (Split-Path -Parent $PSScriptRoot) "runtime")
)

$ErrorActionPreference = 'Stop'

if (-not $PythonRoot) {
  throw "Informe -PythonRoot apontando para uma instalacao real do Python no Windows."
}

if (-not (Test-Path $PythonRoot)) {
  throw "PythonRoot nao encontrado: $PythonRoot"
}

$null = New-Item -ItemType Directory -Force -Path $OutputRoot
Copy-Item -Path (Join-Path $PythonRoot "*") -Destination $OutputRoot -Recurse -Force

Write-Host "Runtime copiado para $OutputRoot"
Write-Host "Revise o conteudo e remova arquivos desnecessarios antes de publicar."
