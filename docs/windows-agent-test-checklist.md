# Windows Agent Homologation Checklist

Use this checklist during Windows homologation and capture evidence for each item.

## Environment Readiness

- Backend API responds at `/health`
- PostgreSQL is up and migrations are applied
- Seed data is loaded
- Windows host can reach `http://BACKEND_HOST:8000`
- PowerShell can execute the install and upgrade commands

Evidence:

- output of `irm http://BACKEND_HOST:8000/health`
- output of `Test-NetConnection -ComputerName BACKEND_HOST -Port 8000`
- screenshot or output showing administrative PowerShell when needed

## Remote Installation

- remote Windows install command finishes successfully
- `C:\ProgramData\PatchManager\agent-windows` is created
- `C:\ProgramData\PatchManager\agent-windows.env` is created
- `dist\PatchManagerAgentWindows.exe` exists on the host
- scheduled task `PatchManagerAgentWindows` is created

Evidence:

- output of the install command
- output of `dir C:\ProgramData\PatchManager\agent-windows`
- output of `dir C:\ProgramData\PatchManager\agent-windows\dist`

## Launcher Validation

- `agent\run-agent.ps1` starts without error
- launcher reads `C:\ProgramData\PatchManager\agent-windows.env`
- agent shows the expected API base and agent ID
- agent does not depend on host Python when `dist\PatchManagerAgentWindows.exe` is present

Evidence:

- terminal log with `Windows agent online`
- terminal log showing bootstrap or successful check-in

## Enrollment Flow

- host appears in `Agentes pendentes`
- approval moves the host to `Agentes conectados`
- rejection stops the process
- revocation removes the host from `Agentes conectados`
- after revocation, the host returns to `Agentes pendentes`

Evidence:

- screenshot of `Configuracoes > Agentes pendentes`
- screenshot of `Configuracoes > Agentes conectados`
- terminal log after rejection or revocation

## Scheduled Task Validation

- task exists with the expected PowerShell launcher
- task starts successfully
- task can restart the agent after upgrade
- task survives logoff/logon or reboot as expected for the chosen registration mode

Evidence:

- output of `Get-ScheduledTask -TaskName PatchManagerAgentWindows | Format-List`
- output of `Get-ScheduledTaskInfo -TaskName PatchManagerAgentWindows`

## Inventory Validation

- hostname is correct in the UI
- IP is correct in the UI
- pending Windows update information is visible
- connected Windows host is visible in `Configuracoes`
- dashboard reflects Windows-side operational signals when applicable

Evidence:

- screenshot of `Configuracoes`
- screenshot of `Dashboard`

## Upgrade Flow

- remote upgrade command finishes successfully
- upgrade replaces the existing `.exe`
- scheduled task is restarted after the upgrade
- the host remains enrolled and connected after the upgrade

Evidence:

- output of the remote upgrade command
- output of `dir C:\ProgramData\PatchManager\agent-windows\dist`
- screenshot of the host still present in `Agentes conectados`

## Job Processing

- at least one Windows patch is approved
- jobs are enqueued
- the Windows agent claims the job
- the job transitions to `running`
- the result is returned to the backend
- reports show the execution outcome

Evidence:

- screenshot of `Patches`
- screenshot of `Relatorios` queue with claimed Windows agent
- screenshot of execution history

## Known Current Limits

- reboot execution is not finalized yet
- detailed Windows update catalog by KB is not exposed in the UI yet
- the packaging flow is homologation-ready, but not yet a signed release pipeline
