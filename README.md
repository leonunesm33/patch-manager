# Patch Manager

Patch Manager, apresentado no frontend como **PatchOps**, e uma plataforma POC para inventario, aprovacao, agendamento e execucao controlada de atualizacoes em hosts Linux e Windows.

O objetivo atual e demonstrar um fluxo fim a fim funcional para homologacao: central web, API, banco, agentes instalaveis, aprovacao de patches, agendamentos, fila operacional, retorno de status, auditoria basica e relatorios.

## Estado atual

Ja implementado:

- frontend React/Vite com dashboards, maquinas, aprovacoes, agendamentos, operacoes, relatorios, configuracoes e usuarios
- backend FastAPI com PostgreSQL, Redis, migrations, autenticacao JWT e seed controlado
- Docker Compose para central local/POC com API, web, gateway TLS, banco e Redis
- agentes Linux e Windows com bootstrap, aprovacao/rejeicao, heartbeat, inventario, comandos e upgrade remoto
- inventario de updates Linux e Windows com persistencia de snapshots
- fluxo de aprovacoes com patches pendentes e gerenciados
- agendamentos por maquina, grupo ou sistema operacional, com janela de instalacao e janela de reboot separadas
- fila operacional para jobs, execucoes e comandos de agente
- relatorios com exportacao em CSV, JSON, HTML, PDF via impressao do browser e XLS compativel com Excel
- documentacao de POC, operacao, troubleshooting, agentes, criterios de homologacao e limites do servico

Ainda em amadurecimento:

- execucao real de patches em larga escala deve continuar protegida por guardrails e homologacao por ambiente
- exportacao XLSX nativa ainda nao foi implementada; o formato atual e uma tabela HTML entregue com MIME de Excel
- PDF usa fluxo de impressao/salvar como PDF do navegador
- RBAC ainda e simples, com perfis `admin` e `user`
- TLS atual da POC pode usar certificado self-signed; producao deve usar certificado corporativo/CA confiavel
- empacotamento Windows ainda nao possui assinatura digital de release

## Estrutura

- `apps/web`: frontend React + Vite + TypeScript
- `apps/api`: backend FastAPI, SQLAlchemy, Alembic, scheduler e worker
- `apps/agent-linux`: agente Linux, instaladores e upgrade remoto
- `apps/agent-windows`: agente Windows, instaladores, launcher e build standalone
- `infra/compose`: Docker Compose da central
- `infra/env`: exemplos de variaveis de ambiente
- `infra/gateway`: Nginx gateway/TLS
- `deploy/central`: instalador, service, backup, restore e smoke test da central
- `docs`: documentacao de implantacao, operacao, homologacao, troubleshooting, auditoria e limites
- `tools`: utilitarios de teste/local smoke

## Execucao local recomendada

O ambiente local usado na homologacao roda melhor pelo WSL, mantendo o repositorio tambem sincronizado em `D:\Patch Manager`.

No WSL:

```bash
cd ~/patch-manager/infra/compose
sudo docker compose up -d
```

Health checks:

```bash
curl -k https://localhost/health
curl http://localhost:8000/health/detailed
```

URLs principais:

- painel local: `https://localhost`
- API local: `http://localhost:8000`
- health detalhado: `http://localhost:8000/health/detailed`

Se o compose reclamar de variaveis ausentes, copie e ajuste:

```bash
mkdir -p infra/env
cp infra/env/api.env.example infra/env/api.env
```

## Desenvolvimento

Frontend:

```bash
cd apps/web
npm install
npm run build
```

API:

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Smoke test da central instalada:

```bash
export PATCH_MANAGER_PASSWORD='<senha-do-admin>'
chmod +x deploy/central/smoke-test.sh
deploy/central/smoke-test.sh
```

## Agentes

Os comandos oficiais de instalacao e atualizacao sao gerados no menu `Configuracoes` do painel.

Linux:

```bash
curl -fsSL "https://<central>/api/v1/agents/install/linux.sh?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>" | sudo bash
```

Windows, em PowerShell administrativo:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://<central>/api/v1/agents/install/windows.ps1?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>' | iex"
```

Depois da instalacao, o host entra em `Agentes pendentes` e precisa ser aprovado no painel.

Guias detalhados:

- `docs/agent-installation-guide.md`
- `docs/linux-agent-homologation.md`
- `docs/windows-agent-homologation.md`
- `docs/linux-agent-test-checklist.md`
- `docs/windows-agent-test-checklist.md`

## Documentacao principal

- `CLAUDE.md`: handoff operacional para continuar o projeto pelo Claude Code
- `docs/poc-deployment-guide.md`: implantacao da central POC
- `docs/poc-operations-guide.md`: operacao diaria
- `docs/poc-troubleshooting.md`: diagnostico de falhas comuns
- `docs/project-handoff-review.md`: revisao consolidada para continuidade por outro agente de codigo
- `docs/poc-demo-script.md`: roteiro de demonstracao
- `docs/poc-homologation-criteria.md`: criterios para considerar a POC pronta
- `docs/service-scope-and-limits.md`: limites e escopo comercial atual
- `docs/support-and-upgrade.md`: suporte, atualizacao e rollback
- `docs/roadmap.md`: backlog e proximas evolucoes

## Regras importantes para continuidade

- Evite `git reset --hard` e qualquer comando destrutivo sem aprovacao explicita.
- Antes de testar reboot real, confirme o ambiente e prefira simulacao.
- Para Windows, valide `C:\ProgramData\PatchManager\agent-windows.env` antes de testar comandos destrutivos.
- Mantenha GitHub, `D:\Patch Manager` e `~/patch-manager` sincronizados quando alternar entre Cursor, WSL e outros agentes de codigo.
- Use o WSL como ambiente principal de build/teste quando as dependencias Windows nao estiverem instaladas.
