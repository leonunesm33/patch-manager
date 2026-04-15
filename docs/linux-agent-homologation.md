# Linux Agent Homologation Guide

This guide describes how to install and validate the current Linux agent on a separate host for a real homologation run.

## Current Scope

What already works:

- agent registration with the backend
- heartbeat and connected-agent visibility
- host inventory with installed package count
- host inventory with upgradable package count
- reboot-required signal
- Linux job claim and result submission
- controlled execution modes `dry-run` and `apply`

What is still simulated:

- `apply` uses `apt-get -s` and does not install packages for real yet
- the frontend does not show a full installed-package catalog by package name/version

## Prerequisites

On the target Linux host:

- Ubuntu or Debian
- `python3`
- `apt`
- `rsync`
- network access to the Patch Manager API
- privilege to install a systemd service

Validation commands:

```bash
python3 --version
apt --version
rsync --version
hostname
ip a
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

```bash
curl http://BACKEND_IP:8000/health
```

Bootstrap flow:

- define the bootstrap token in `Configuracoes`
- copy the generated install command
- run it on the target Linux host
- approve or reject the host in `Agentes pendentes`

## Manual Validation First

On the target Linux host:

```bash
cd /tmp/agent-linux
cp .env.example .env
```

Edit `.env` with:

```env
PATCH_MANAGER_API=http://BACKEND_IP:8000/api/v1/agents
PATCH_MANAGER_AGENT_ID=linux-agent-01
PATCH_MANAGER_AGENT_KEY=
PATCH_MANAGER_BOOTSTRAP_TOKEN=patch-manager-bootstrap-token
PATCH_MANAGER_EXECUTION_MODE=dry-run
PATCH_MANAGER_LOG_FILE=/var/log/patch-manager/agent-linux.log
```

Run the agent manually:

```bash
cd /tmp/agent-linux
python3 agent/main.py
```

Expected behavior:

- the process starts without import errors
- the backend accepts `check-in`
- the backend accepts `inventory`
- the agent appears in the `Configuracoes` page

## Install as a Service

Preferred bootstrap flow from the console:

```bash
curl -fsSL "http://BACKEND_IP:8000/api/v1/agents/install/linux.sh?server_url=http%3A%2F%2FBACKEND_IP%3A8000&bootstrap_token=patch-manager-bootstrap-token" | sudo bash
```

Fallback local flow from a copied repository:

```bash
cd /tmp/agent-linux
chmod +x deploy/install-linux-agent-guided.sh
./deploy/install-linux-agent-guided.sh \
  --server http://BACKEND_IP:8000 \
  --bootstrap-token patch-manager-bootstrap-token \
  --mode dry-run
```

Start and inspect the service:

```bash
sudo systemctl enable --now patch-manager-agent-linux.service
sudo systemctl status patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -f
```

Generated environment file:

```bash
sudo cat /etc/patch-manager/agent-linux.env
```

## Upgrade an Installed Agent

For a host that already has the agent installed:

```bash
curl -fsSL "http://BACKEND_IP:8000/api/v1/agents/install/linux-upgrade.sh?server_url=http%3A%2F%2FBACKEND_IP%3A8000" | sudo bash
```

Expected result:

- files under `/opt/patch-manager/agent-linux` are refreshed
- `/etc/patch-manager/agent-linux.env` is preserved
- `patch-manager-agent-linux.service` is restarted

Validation commands:

```bash
sudo systemctl status patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -n 50
```

## Validate Pending Updates

On the Linux host:

```bash
apt list --upgradable
apt list --upgradable 2>/dev/null | tail -n +2 | wc -l
```

In Patch Manager:

- `Configuracoes` should show the connected agent
- `Configuracoes` should show package manager `apt`
- `Configuracoes` should show installed package count
- `Configuracoes` should show upgradable package count
- `Maquinas` should reflect pending patch count for the host

## Validate Jobs

In Patch Manager:

1. Approve a Linux patch in `Patches`.
2. Enqueue jobs in `Relatorios`.
3. Let the Linux agent claim the job.
4. Check the result in `Relatorios`.

Expected result:

- the job moves from `pending` to `running`
- the agent field is populated
- the result returns as `applied` or `failed`
- dashboard and reports update after execution logs are created

## Current Homologation Interpretation

This homologation already validates:

- backend to agent trust
- agent to backend communication
- real host inventory collection
- pending update count collection
- end-to-end job orchestration
- safe command execution path for Linux
- bootstrap enrollment and approval flow
- upgrade of an already-installed agent

This homologation does not yet validate:

- real package installation
- reboot execution
- package-by-package historical inventory in the UI
