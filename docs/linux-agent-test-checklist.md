# Linux Agent Homologation Checklist

Use this checklist during homologation and capture evidence for each item.

## Environment Readiness

- Backend API responds at `/health`
- PostgreSQL is up and migrations are applied
- Seed data is loaded
- Linux host can reach `http://BACKEND_IP:8000`
- `python3`, `apt`, and `rsync` are installed on the Linux host

Evidence:

- output of `curl http://BACKEND_IP:8000/health`
- output of `python3 --version`
- output of `apt --version`

## Manual Agent Start

- `.env` created from `.env.example`
- `PATCH_MANAGER_API` points to the correct backend
- `PATCH_MANAGER_AGENT_ID` is defined
- `PATCH_MANAGER_BOOTSTRAP_TOKEN` matches the backend token
- `python3 agent/main.py` starts without traceback

Evidence:

- terminal log with `Linux agent online`
- terminal log with first successful inventory push

## Backend Registration

- agent appears in `Configuracoes`
- platform shows `linux`
- hostname is correct
- IP is correct
- package manager shows `apt`

Evidence:

- screenshot of `Configuracoes > Agentes conectados`

## Inventory Validation

- installed package count is shown
- upgradable package count is shown
- reboot-required state is shown correctly
- `Maquinas` reflects the managed host

Evidence:

- screenshot of `Configuracoes`
- screenshot of `Maquinas`
- output of `apt list --upgradable 2>/dev/null | tail -n +2 | wc -l`

## Service Installation

- remote install command or `install-linux-agent-guided.sh` finishes successfully
- `/etc/patch-manager/agent-linux.env` is created
- `patch-manager-agent-linux.service` is enabled
- service starts successfully after reboot or restart

Evidence:

- output of `sudo systemctl status patch-manager-agent-linux.service`
- output of `sudo journalctl -u patch-manager-agent-linux.service -n 50`

## Enrollment Flow

- host appears in `Agentes pendentes`
- approval moves the host to `Agentes conectados`
- rejection stops the agent process
- deleting the machine revokes the credential
- the agent reappears in `Agentes pendentes`

Evidence:

- screenshot of `Configuracoes > Agentes pendentes`
- screenshot of `Configuracoes > Agentes conectados`
- journal output after rejection

## Upgrade Flow

- remote upgrade command runs successfully
- the service restarts without losing the existing identity
- the host remains connected after the upgrade

Evidence:

- output of the remote upgrade command
- output of `sudo systemctl status patch-manager-agent-linux.service`
- screenshot of the host still present in `Agentes conectados`

## Job Processing

- at least one Linux patch is approved
- jobs are enqueued
- the Linux agent claims the job
- the job transitions to `running`
- the result is returned to the backend
- reports show the execution outcome

Evidence:

- screenshot of `Patches`
- screenshot of `Relatorios` queue with claimed agent
- screenshot of execution history

## Known Current Limits

- `apply` is still a safe simulation using `apt-get -s`
- no real package installation should be expected
- no automatic reboot is implemented
- no package catalog by name/version is shown in the UI yet
