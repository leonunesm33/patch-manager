# Patch Manager POC Troubleshooting

## Painel nao abre
- valide `https://<host>/health`
- confira `docker compose logs -f gateway`
- confirme existencia de `infra/certs/tls.crt` e `infra/certs/tls.key`

## API indisponivel
- valide `docker compose ps`
- valide `docker compose logs -f api`
- teste `docker compose exec api curl -fsS http://localhost:8000/health/detailed`

## Erro de banco
- valide `docker compose logs -f db`
- valide a `DATABASE_URL` em `infra/env/api.env`
- reaplique migrations:

```bash
docker compose exec api alembic upgrade head
```

## Agente nao aparece
- confirme conectividade ate `https://<host>`
- valide bootstrap token
- veja `Agentes pendentes`, `Agentes rejeitados`, `Agentes revogados` e `Agentes parados`

## Agente aparece como parado
- o backend considera heartbeat vencido apos a janela de conectividade
- valide logs locais do agente e o relogio do host

## Task do agente Windows falha
- valide `C:\ProgramData\PatchManager\agent-windows.env`
- valide a task `PatchManagerAgentWindows`
- use o launcher `agent\run-agent.ps1`

## Service do agente Linux falha
- valide:

```bash
sudo systemctl status patch-manager-agent-linux.service
sudo journalctl -u patch-manager-agent-linux.service -f
```

## Login falha
- confirme troca da senha padrao
- se o usuario exigir troca de senha, ele sera redirecionado automaticamente
- valide papel/perfil do usuario para a acao tentada
