# Windows Agent Homologation Guide

This guide describes how to install and validate the current Windows agent on a real host for homologation.

## Current Scope

What already works:

- remote Windows installation from the backend
- remote upgrade of an already-installed Windows agent
- bootstrap enrollment with approval in the console
- heartbeat, check-in and inventory submission
- connected-agent visibility in the frontend
- Windows job claim and result submission
- controlled Windows execution flow with `dry-run`, `StartScan`, and optional `StartDownload` plus `StartInstall`
- launcher-based runtime resolution through:
  - `dist\PatchManagerAgentWindows.exe`
  - `runtime\python.exe`
  - Python installed on the host as a fallback

What still needs more maturity:

- full Windows Update catalog by KB/package in the UI
- post-install reboot policy and reboot execution
- detailed installed-update history by host

## Prerequisites

On the target Windows host:

- PowerShell 5.1 or newer
- network access to the Patch Manager API
- permission to register a scheduled task
- for production-like homologation, prefer an administrative PowerShell

Validation commands:

```powershell
$PSVersionTable.PSVersion
Test-NetConnection -ComputerName BACKEND_HOST -Port 8000
hostname
ipconfig
```

## Backend Preparation

On the Patch Manager server:

```bash
cd ~/patch-manager/apps/api
source .venv/bin/activate
alembic upgrade head
python -m app.seed
uvicorn app.main:app --reload --port 8000
```

Health check:

```powershell
irm http://BACKEND_HOST:8000/health
```

Bootstrap flow:

- define the bootstrap token in `Configuracoes`
- if using packaged Windows agent delivery, make sure `dist\PatchManagerAgentWindows.exe` is already present in the project served by the API
- copy the generated Windows install command from the console
- run it on the target Windows host
- approve or reject the host in `Agentes pendentes`

## Remote Installation

Preferred installation flow from the console:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'http://BACKEND_HOST:8000/api/v1/agents/install/windows.ps1?server_url=http%3A%2F%2FBACKEND_HOST%3A8000&bootstrap_token=patch-manager-bootstrap-token' | iex"
```

Expected result:

- files are written under `C:\ProgramData\PatchManager\agent-windows`
- environment is written to `C:\ProgramData\PatchManager\agent-windows.env`
- scheduled task `PatchManagerAgentWindows` is created
- the launcher `agent\run-agent.ps1` is used by the task
- the agent starts automatically and appears in `Agentes pendentes`

Inspect the installed layout:

```powershell
dir C:\ProgramData\PatchManager\agent-windows
dir C:\ProgramData\PatchManager\agent-windows\dist
Get-Content C:\ProgramData\PatchManager\agent-windows.env
```

## Manual Start Validation

To validate the launcher manually on the Windows host:

```powershell
cd C:\ProgramData\PatchManager\agent-windows
powershell -ExecutionPolicy Bypass -File .\agent\run-agent.ps1
```

Expected behavior:

- the process starts without traceback
- the log shows `Windows agent online`
- the log shows the API base
- if the agent is not yet approved, it should enter the bootstrap flow
- after approval, the agent should complete check-in and inventory

## Scheduled Task Validation

Inspect the scheduled task:

```powershell
Get-ScheduledTask -TaskName PatchManagerAgentWindows | Format-List
```

Expected action:

- `Execute`: `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`
- `Arguments`: `-ExecutionPolicy Bypass -File agent\run-agent.ps1`
- `WorkingDirectory`: `C:\ProgramData\PatchManager\agent-windows`

Run it manually if needed:

```powershell
Start-ScheduledTask -TaskName PatchManagerAgentWindows
```

## Enrollment Flow

The expected enrollment lifecycle is:

1. the host appears in `Agentes pendentes`
2. approval moves the host to `Agentes conectados`
3. rejection stops the local process
4. revocation removes the host from `Agentes conectados`
5. the agent returns to bootstrap and appears again in `Agentes pendentes`

This is especially important for validating real recovery behavior after credential invalidation.

## Upgrade an Installed Agent

For a host that already has the Windows agent installed:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'http://BACKEND_HOST:8000/api/v1/agents/install/windows-upgrade.ps1?server_url=http%3A%2F%2FBACKEND_HOST%3A8000' | iex"
```

Expected result:

- the task is stopped
- the current agent process is terminated if needed
- files under `C:\ProgramData\PatchManager\agent-windows` are refreshed
- `C:\ProgramData\PatchManager\agent-windows.env` is preserved
- the task is started again

Validation commands:

```powershell
dir C:\ProgramData\PatchManager\agent-windows\dist
Get-ScheduledTaskInfo -TaskName PatchManagerAgentWindows
```

## Inventory Validation

In Patch Manager:

- `Configuracoes` should show the connected Windows agent
- hostname should match the Windows host
- IP should match the host network address
- pending update information should be visible
- the agent version should be visible

If the host reports inventory correctly, the backend snapshot layer is working as expected.

## Job Validation

In Patch Manager:

1. approve a Windows patch in `Patches`
2. enqueue jobs in `Relatorios`
3. let the Windows agent claim the job
4. confirm the result in `Relatorios`

Expected result:

- the job moves from `pending` to `running`
- the agent column is populated
- the result returns as `applied` or `failed`
- dashboard and reports reflect the execution

## Current Homologation Interpretation

This homologation already validates:

- backend to Windows agent trust
- bootstrap enrollment on Windows
- delivery of packaged agent executable
- scheduled-task based execution
- inventory submission and snapshot persistence
- end-to-end Windows job orchestration
- upgrade of an already-installed Windows agent
- recovery after credential revocation

This homologation does not yet validate:

- automatic reboot execution
- detailed Windows update history by KB in the UI
- a full production-grade packaging pipeline with signed releases
