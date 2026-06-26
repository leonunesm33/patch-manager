# Claude Code Handoff - Patch Manager

Este arquivo existe para permitir retomar o projeto pelo Claude Code a partir do GitHub, mesmo sem acesso ao historico completo da conversa original.

## Contexto do produto

Patch Manager/PatchOps e uma POC de plataforma para gerenciar atualizacoes de hosts Windows e Linux:

- inventario de maquinas e updates pendentes
- agentes instalaveis com bootstrap e aprovacao na central
- aprovacao/rejeicao de patches
- agendamento por maquina, grupo ou sistema operacional
- janelas separadas para instalacao e reboot
- fila de jobs, comandos de agentes, execucoes e status
- relatorios e exportacoes operacionais

O foco atual e deixar a solucao confiavel para homologacao real e demonstracao comercial controlada.

## Repositorios e caminhos usados pelo usuario

| Ambiente | Caminho | Papel |
|---|---|---|
| WSL Ubuntu-24.04 | `~/projetos/patch-manager` | **PRIMARIO** — commits, build, Docker |
| GitHub | `https://github.com/leonunesm33/patch-manager.git` | origem remota |
| Windows Disco D | `D:\Patch Manager` | espelho de leitura / build do exe Windows |
| Servidor POC | `/opt/patch-manager` | Ubuntu 24.04 remoto, demo/homologacao |

**Regra de trabalho**: todos os commits e operacoes Docker partem do WSL (`~/projetos/patch-manager`).
O Disco D e um espelho que faz `git pull` apos o push do WSL. A excecao e o build do exe Windows
(`PatchManagerAgentWindows.exe`), que exige Python/pywin32 no Windows e deve ser feito em `D:\Patch Manager`.

Para atualizar o servidor POC apos um commit:

```bash
cd /opt/patch-manager
sudo git pull --ff-only
cd infra/compose
sudo docker compose up -d --build api web
```

Regra: use `--build api web` sempre que houver mudancas em `apps/api` ou `apps/web`.
O container `web` compila o React em tempo de build — sem rebuild, o frontend antigo continua sendo servido.

## Regras de trabalho

- Nao use `git reset --hard`, `git checkout --` ou comandos destrutivos sem pedido explicito.
- Nao acione reboot real sem confirmacao clara. Para testes, prefira `PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=true`.
- Se for testar reboot real na maquina do usuario, finalize processos relevantes e avise com antecedencia.
- Use `apply_patch` para edicoes manuais.
- Preserve alteracoes existentes que nao foram feitas por voce.
- Comunique em portugues, de forma objetiva e colaborativa.

## Como subir a central local

No WSL:

```bash
cd ~/projetos/patch-manager/infra/compose
sudo docker compose up -d
```

Se o Docker instalado no WSL for via snap, o binario pode estar em `/snap/bin/docker`.

Health checks:

```bash
curl -k https://localhost/health
curl http://localhost:8000/health/detailed
```

Portal:

- `https://localhost`

API:

- `http://localhost:8000`

Se faltar arquivo de ambiente:

```bash
cd ~/projetos/patch-manager
mkdir -p infra/env
cp infra/env/api.env.example infra/env/api.env
```

Depois ajuste segredos em `infra/env/api.env`.

## Comandos comuns de validacao

Frontend:

```bash
cd ~/projetos/patch-manager/apps/web
npm run build
```

API:

```bash
cd ~/projetos/patch-manager/apps/api
source .venv/bin/activate
python -m compileall app
alembic upgrade head
```

Compose:

```bash
cd ~/projetos/patch-manager/infra/compose
sudo docker compose ps
sudo docker compose logs --tail=120 api
sudo docker compose logs --tail=120 web
sudo docker compose logs --tail=120 gateway
```

Smoke test:

```bash
cd ~/projetos/patch-manager
export PATCH_MANAGER_PASSWORD='<senha-do-admin>'
deploy/central/smoke-test.sh
```

## Instalacao e upgrade de agentes

Use preferencialmente os comandos gerados no menu `Configuracoes` do painel.

Linux:

```bash
curl -fsSL "https://<central>/api/v1/agents/install/linux.sh?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>" | sudo bash
```

Linux upgrade:

```bash
curl -fsSL "https://<central>/api/v1/agents/install/linux-upgrade.sh?server_url=https%3A%2F%2F<central>" | sudo bash
```

Windows, em PowerShell administrativo:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://<central>/api/v1/agents/install/windows.ps1?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>' | iex"
```

Windows upgrade:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://<central>/api/v1/agents/install/windows-upgrade.ps1?server_url=https%3A%2F%2F<central>' | iex"
```

Windows service (Windows Server 2012+):

- nome do servico: `PatchManagerAgent`
- display: `Patch Manager Agent`
- pasta: `C:\ProgramData\PatchManager\agent-windows`
- exe: `C:\ProgramData\PatchManager\agent-windows\dist\PatchManagerAgentWindows.exe`
- env: `C:\ProgramData\PatchManager\agent-windows.env`
- gerenciar: `Start-Service PatchManagerAgent` / `Stop-Service PatchManagerAgent`
- registrar manualmente: `PatchManagerAgentWindows.exe install`
- remover manualmente: `PatchManagerAgentWindows.exe remove`
- diagnostico manual (fora do servico): `PatchManagerAgentWindows.exe run`

Flags importantes do agente Windows:

- `PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=true`
- `PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=true` para teste seguro
- `PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=false` somente para reboot real autorizado

Build do exe (requer pywin32 instalado — rodar no Windows, nao no WSL):

```powershell
py -3 -m pip install pywin32 pyinstaller
cd "D:\Patch Manager\apps\agent-windows"
py -3 -m PyInstaller --noconfirm --distpath dist deploy\patch-manager-agent-windows.spec
```

Apos o build, commitar o exe pelo Windows (ou copiar para o WSL e commitar de la):

```powershell
cd "D:\Patch Manager"
git add apps/agent-windows/dist/PatchManagerAgentWindows.exe
git commit -m "Build: rebuild exe do agente Windows"
git push origin main
```

O exe e rastreado no git (`!apps/agent-windows/dist/PatchManagerAgentWindows.exe` no .gitignore)
para que o servidor POC possa servi-lo via `/api/v1/agents/install/windows-agent.exe`.

## Fluxos implementados recentemente

- `Aprovacoes` foi dividido em patches pendentes e patches ja gerenciados.
- Filtros de `Aprovacoes` ficam ocultos atras de botao `Filtros`.
- `Relatorios` agora concentra dados e exportacoes.
- Acoes de fila `Gerar jobs agora` e `Executar proximo ciclo` foram movidas para `Operacoes`.
- `Agendamentos` suporta escopo por maquina, grupo ou SO, recorrencia unica/diaria/semanal/mensal e horarios separados para instalacao e reboot.
- `Maquinas` possui grupos de maquinas em popup para evitar poluicao visual.
- Windows agent coleta nomes reais dos updates quando possivel, nao apenas IDs.

## Pontos de atencao atuais

- Exportacao XLSX ainda e compatibilidade Excel via HTML `.xls`; implementar `.xlsx` real se isso virar requisito.
- Exportacao PDF usa janela de impressao do navegador; para PDF servidor, criar endpoint backend dedicado.
- Reboot agendado depende do scheduler gerar comando e do agente consumir. Verifique logs da API e do agente antes de concluir falha.
- O scheduler roda por intervalo, geralmente 30s, conforme `SCHEDULER_INTERVAL_SECONDS`.
- Reagendar para o mesmo horario ja processado pode nao gerar novo comando por deduplicacao; use um horario futuro novo durante testes.
- Ambiente local pode ter nomes duplicados de host quando ha agente Windows e Linux/WSL na mesma maquina fisica.
- Producao precisa reforcar TLS, segredos, assinatura do agente Windows, backup/restore testado e RBAC granular.

## Onde olhar primeiro

- `README.md`: visao geral e comandos principais
- `docs/poc-deployment-guide.md`: instalacao central
- `docs/poc-homologation-step-by-step.md`: roteiro completo de homologacao da central e agentes
- `docs/poc-operations-guide.md`: operacao da central
- `docs/poc-troubleshooting.md`: diagnostico
- `docs/agent-installation-guide.md`: agentes
- `docs/windows-agent-homologation.md`: homologacao Windows
- `docs/linux-agent-homologation.md`: homologacao Linux
- `docs/service-scope-and-limits.md`: escopo e limites
- `docs/roadmap.md`: proximas evolucoes

## Sincronizacao esperada

O fluxo padrao parte do WSL:

```bash
# No WSL (repositorio primario)
cd ~/projetos/patch-manager
git status --short
git add .
git commit -m "<mensagem objetiva>"
git push origin main
```

Depois alinhar o espelho Windows (Disco D):

```powershell
# No Windows / PowerShell
cd "D:\Patch Manager"
git fetch origin
git pull --ff-only
```

E o servidor POC:

```bash
cd /opt/patch-manager
sudo git pull --ff-only
cd infra/compose
sudo docker compose up -d --build api web  # somente se houver mudancas em apps/api ou apps/web
```

**Excecao — build do exe Windows**: commitar pelo Windows diretamente (Python/pywin32 nao estao no WSL).
Apos o push do Windows, o WSL sincroniza com `git pull --ff-only`.
