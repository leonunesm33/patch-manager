# Agent Linux

Estrutura inicial para o agente Linux.
## Agente Linux

Base do agente Linux para homologacao controlada.

### Estado atual

- heartbeat, check-in e inventario
- claim de jobs Linux
- execucao em `dry-run` e `apply`
- logs em console e opcionalmente em arquivo
- loop com retry/backoff
- arquivos base para rodar como servico `systemd`

### Execucao manual

```bash
cd apps/agent-linux
cp .env.example .env
PATCH_MANAGER_AGENT_KEY=patch-manager-agent-key python3 agent/main.py
```

### Variaveis principais

- `PATCH_MANAGER_API`: endpoint base da API de agentes
- `PATCH_MANAGER_AGENT_KEY`: credencial secreta do agente
- `PATCH_MANAGER_AGENT_ID`: identificador unico do host
- `PATCH_MANAGER_EXECUTION_MODE`: fallback inicial do agente
- `PATCH_MANAGER_LOG_FILE`: arquivo local de log
- `PATCH_MANAGER_ENV_FILE`: caminho opcional para um arquivo `.env`

O agente tenta carregar automaticamente um `.env` em:

- diretório atual
- `apps/agent-linux/.env`
- caminho informado por `PATCH_MANAGER_ENV_FILE`

### Rodando como servico

Arquivos de apoio:

- `deploy/patch-manager-agent-linux.service`
- `deploy/install-linux-agent.sh`

Fluxo sugerido em homologacao:

```bash
cd apps/agent-linux
chmod +x deploy/install-linux-agent.sh
./deploy/install-linux-agent.sh
sudoedit /etc/patch-manager/agent-linux.env
sudo systemctl enable --now patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -f
```
