# Project Handoff Review

Este documento consolida o estado revisado do Patch Manager para continuidade por outro agente de codigo, incluindo Claude Code, a partir do GitHub.

## Resumo executivo

O projeto esta em estagio de POC funcional. A central, os agentes, o fluxo de aprovacao, agendamento, fila operacional, retorno de status e relatorios ja existem e podem ser demonstrados em ambiente local/homologacao.

A solucao ainda nao deve ser tratada como produto enterprise completo sem reforcos de seguranca, empacotamento, observabilidade, RBAC granular e homologacoes adicionais de execucao real.

## Modulos revisados

### Frontend

Local: `apps/web`

Estado:

- React + Vite + TypeScript
- layout PatchOps com menu lateral
- telas de Dashboard, Maquinas, Aprovacoes, Agendamentos, Operacoes, Relatorios, Configuracoes e Usuarios
- filtros ocultos por botao onde aplicavel
- acoes contextuais por menu de tres pontos
- modais centrais para edicao/detalhes em fluxos principais
- relatorios com exportacao em CSV, JSON, HTML, PDF e Excel-compativel

Validacao sugerida:

```bash
cd apps/web
npm run build
```

### API

Local: `apps/api`

Estado:

- FastAPI
- SQLAlchemy + Alembic
- autenticacao JWT
- usuarios e perfis simples
- maquinas, patches, aprovacoes, grupos, agendamentos, jobs, comandos e agentes
- scheduler e worker com autostart configuravel
- health checks

Validacao sugerida:

```bash
cd apps/api
source .venv/bin/activate
python -m compileall app
alembic upgrade head
```

### Central Docker/POC

Locais:

- `infra/compose`
- `infra/env`
- `infra/gateway`
- `deploy/central`

Estado:

- PostgreSQL 16
- Redis 7
- API containerizada
- frontend containerizado
- gateway Nginx com TLS local
- instalador de central
- backup, restore, start/stop e smoke test

Validacao sugerida:

```bash
cd infra/compose
docker compose up -d
docker compose ps
curl -k https://localhost/health
curl http://localhost:8000/health/detailed
```

### Agente Linux

Local: `apps/agent-linux`

Estado:

- bootstrap enrollment
- aprovacao/rejeicao/reintegracao
- heartbeat e inventario
- coleta de updates via apt
- jobs Linux
- reboot agendado com guardrails
- instalador e upgrade remoto
- service systemd

Documentos:

- `docs/linux-agent-homologation.md`
- `docs/linux-agent-test-checklist.md`

### Agente Windows

Local: `apps/agent-windows`

Estado:

- bootstrap enrollment
- aprovacao/rejeicao/reintegracao
- heartbeat e inventario
- coleta de updates Windows com nome do update quando disponivel
- jobs Windows
- reboot agendado com simulacao e execucao real protegida
- instalador e upgrade remoto
- scheduled task
- launcher com prioridade para executavel standalone

Documentos:

- `docs/windows-agent-homologation.md`
- `docs/windows-agent-test-checklist.md`

## Funcionalidades principais

- Maquinas: inventario, status, patches pendentes, grupos e detalhes por host.
- Aprovacoes: patches pendentes e patches ja gerenciados, com filtros.
- Agendamentos: escopo por maquina, grupo ou SO; frequencia unica, diaria, semanal ou mensal; horario de instalacao e horario de reboot separados.
- Operacoes: fila de patches, comandos de agentes, pendencias, reintegracao e acoes operacionais.
- Relatorios: historico operacional, jobs, execucoes, falhas, guardrails e exportacoes.
- Configuracoes: politicas globais, Linux, Windows, scheduler, bootstrap e comandos de instalacao/upgrade.
- Usuarios: ajuste de perfil, senha e administracao simples de usuarios/perfis.

## Lacunas conhecidas

- Exportacao XLSX e atualmente Excel-compativel, nao `.xlsx` nativo.
- Exportacao PDF usa impressao do navegador.
- RBAC ainda e simples.
- TLS local pode usar certificado self-signed.
- Windows agent precisa de pipeline de release assinado para producao.
- Apply real deve continuar restrito a homologacao controlada.
- Testes automatizados de scheduler/reboot ainda devem ser ampliados.
- Observabilidade ainda depende principalmente de logs e telas operacionais.

## Pontos criticos para o proximo agente

- Antes de mexer em reboot, confirme se o teste e simulado ou real.
- Antes de concluir que um agendamento falhou, verifique scheduler, deduplicacao, horario local e logs do agente.
- Em ambiente local, WSL e Windows podem reportar o mesmo hostname fisico como agentes diferentes.
- Se o portal nao abre em `https://localhost`, verifique gateway, certificados e containers antes de alterar frontend.
- Se `windows-upgrade.ps1` falhar, valide se o executavel do agente esta em uso e pare a task antes de atualizar.
- Se um patch aparece como contador em `Maquinas` mas nao em `Aprovacoes`, conferir status/filtro e snapshots de inventario.

## Comando de continuidade recomendado

Ao abrir pelo Claude Code, comece por:

```bash
git status --short
cat CLAUDE.md
cat README.md
cat docs/project-handoff-review.md
```

Depois escolha a validacao adequada:

```bash
cd apps/web && npm run build
```

ou:

```bash
cd infra/compose && docker compose ps
```
