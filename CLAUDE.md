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
- `Agendamentos` suporta escopo por maquina, grupo ou SO; recorrencia unica/diaria/semanal/mensal **e mensal-por-dia-da-semana** (`monthly_weekday` — ex.: "3a quinta-feira do mes", "ultima sexta-feira do mes"); horarios separados para instalacao e reboot.
- `Maquinas` possui grupos de maquinas em popup para evitar poluicao visual; o campo Grupo no formulario de editar/criar maquina e um `<select>` alimentado pelos grupos cadastrados (nao texto livre).
- `Maquinas` tem coluna `SO` (versao amigavel do SO, ex.: "Ubuntu 24.04", "Server 2022") coletada pelo agente, separada da coluna `Plataforma`.
- Deteccao de conflito de identidade de agente (clones de template com hostname provisorio): fingerprint de hardware compara maquinas com o mesmo `agent_id`. Mudanca de fingerprint agora **auto-resolve** (promove o novo fingerprint a canonico sem intervencao manual, registra evento de auditoria `machine_identity_conflict_auto_resolved`) — cobre o caso comum de reprovisionamento legitimo de uma unica maquina. Se o mesmo `agent_id` alternar entre dois fingerprints dentro de 1h (`IDENTITY_CONFLICT_OSCILLATION_WINDOW` em `apps/api/app/api/v1/agents.py`), para de auto-resolver, sinaliza `identity_conflict_oscillation_detected_at` e volta ao fluxo manual (badge "possivel identidade duplicada", acao "Resolver conflito de identidade", evento `machine_identity_conflict_oscillation_detected`) — cobre o caso de duas VMs fisicas compartilhando o mesmo `agent_id`/credencial (template mal clonado antes da correcao do commit 884c720). Resolver manualmente limpa o estado e libera a auto-resolucao de novo.
- Remediacao definitiva de `agent_id` compartilhado: a acao `force_reidentify` reserva um novo UUID e e reivindicada atomicamente pelo **proximo** clone que consultar a fila; o agente executa o instalador inicial, reinicia e reaparece como enrollment pendente. A identidade antiga nao e revogada, permitindo repetir o fluxo um host por vez. O historico relacional `agent_identity_history` aparece nos detalhes da maquina. Nunca descreva essa acao como direcionada ao hostname atualmente exibido.
- Windows agent coleta nomes reais dos updates quando possivel, nao apenas IDs.
- Guardrails Linux: alem de `Somente seguranca`, existe `Seguranca e criticos` (instala patch se for security-tagged **ou** severidade `critical`). Os dois sao mutuamente exclusivos (ligar um desliga o outro).

## Padrao de implementacao para novos campos/recursos

Ao adicionar um campo persistido (ex.: nova coluna em `machines` ou `schedules`), a ordem que funcionou de forma consistente:

1. **Model** (`apps/api/app/models/*.py`): adicionar coluna `Mapped[...]`, nullable a menos que haja um default seguro.
2. **Migration** (`apps/api/alembic/versions/`): nome `YYYYMMDD_NNNN_descricao.py`, `revision`/`down_revision` apontando pro head atual (`alembic heads` confirma). Rodar `alembic heads`/`alembic history` para validar a cadeia antes de aplicar.
3. **Schema** (`apps/api/app/schemas/*.py`): schema de resposta e de create/update. Validacao cross-field (ex.: "campo X obrigatorio quando campo Y = valor Z") vai num `@model_validator(mode="after")` do Pydantic v2, nao no endpoint.
4. **API** (`apps/api/app/api/v1/*.py`): normalizacao/rotulos (`_normalize_*`, `_*_label`) e persistencia (`_apply_payload` ou equivalente).
5. **Repository/Service**: logica de negocio (ex.: `patch_cycle_service.py` decide quando um agendamento "dispara"; `settings_service.py` guarda config chave-valor generica).
6. **Frontend types** (`apps/web/src/features/<area>/types.ts`): espelhar o schema da API.
7. **Frontend UI** (`apps/web/src/features/<area>/pages/*.tsx`): form, tabela, labels.
8. **Testes**: pelo menos um teste de logica de negocio pura (ex.: `test_patch_cycle_schedule_recurrence.py`) e um teste de API via `TestClient` (ex.: `test_schedules_monthly_weekday.py`), usando os fixtures de `apps/api/app/tests/conftest.py` (`client`, `db_session`, SQLite in-memory).

Guardrails/flags mutuamente exclusivos (ex.: `allow_security_only` x `allow_security_and_critical`): a exclusao mutua **tem que ser garantida no service/backend** (cada setter zera o outro), nunca apenas na UI — um script ou outro cliente da API tambem precisa respeitar a regra.

Campos que o operador pode editar manualmente mas que tambem sao atualizados por um processo automatico (ex.: `machine.group`, preenchido tanto pelo agente a cada inventario quanto pelo formulario de edicao): o processo automatico so deve aplicar um **default quando o campo ainda esta vazio** (`campo = campo or default`), nunca sobrescrever incondicionalmente — senao a edicao manual e revertida no proximo ciclo do agente (foi um bug real, ver historico de commits de `apps/api/app/api/v1/agents.py`).

## Armadilhas tecnicas conhecidas

- **Bit de execucao (chmod) cai ao editar via caminho UNC** (`\\wsl.localhost\...`): qualquer edicao feita a partir do Windows num arquivo que era `100755` (scripts `.sh`, alguns `.py`) some para `100644`. Sempre conferir `git diff --summary | grep -i mode` antes de commitar e rodar `chmod 755 <arquivo>` nos que precisam.
- **`ORDER BY` sem desempate determinístico gera "flicker" na paginacao do front**: se duas linhas empatam na coluna de ordenacao (ex.: dois hosts com o mesmo `name`, comum em maquinas clonadas de template antes do rename), o Postgres nao garante a mesma ordem entre consultas. Como a paginacao das listas e so no front (indice de pagina fixo sobre lista ja ordenada), isso faz um item "sumir e reaparecer" mesmo com o total inalterado. Sempre desempatar por uma coluna unica e estavel (ex.: `id`) — ver `MachineRepository.list_all()`.
- **`docker compose` (plugin v2) pode nao estar instalado no WSL**, so o binario `docker` puro. Sem sudo: baixar o binario oficial e colocar em `~/.docker/cli-plugins/docker-compose` (plugin por usuario, nao precisa de root):
  ```bash
  mkdir -p ~/.docker/cli-plugins
  curl -fsSL -o ~/.docker/cli-plugins/docker-compose \
    https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64
  chmod +x ~/.docker/cli-plugins/docker-compose
  ```
- **Gateway nginx forca redirect para HTTPS com certificado self-signed** (`infra/gateway/nginx.conf`), o que bloqueia navegadores headless (Playwright) com `ERR_CERT_AUTHORITY_INVALID` mesmo em `http://localhost/`. Para testar a UI via browser automatizado sem mexer no gateway real: subir um override temporario do `docker-compose.yml` (fora do repo, ex. em `~/tmp/`) expondo o container `web` numa porta alternativa com um `nginx.conf` custom que proxeia `/api/` para `http://api:8000` (rede interna do compose), sem TLS. Reverter com `docker compose up -d --force-recreate web` (usando so o `docker-compose.yml` do repo) ao terminar, e apagar os arquivos temporarios.
- **"Funciona aqui mas nao no ambiente do usuario" ao investigar bug relatado apos deploy**: antes de assumir bug de codigo, confirmar que o ambiente relatante rodou o rebuild da imagem apos o `git pull` — `git pull` sozinho NAO reconstroi a imagem Docker. Se um campo novo simplesmente "nao aplica" ou "some depois de salvar", suspeitar de schema Pydantic antigo (versao anterior ao commit) ignorando silenciosamente o campo desconhecido no payload.
- **`_schedule_period_key`/dedup de jobs**: recorrencias que devem disparar uma vez por mes (ex. `monthly`, `monthly_weekday`) usam a chave `YYYY-MM`; reagendar para o mesmo horario ja processado no periodo atual pode nao gerar novo job por deduplicacao (ja documentado abaixo em "Pontos de atencao atuais").
- **Ordem de leitura do Vite (`.env`)**: o `Dockerfile` de `apps/web` so faz `COPY` de arquivos explicitamente listados (`package*.json`, `index.html`, `tsconfig*.json`, `vite.config.ts`, `.env.example`, `src`) — um `.env` criado ad-hoc no host **nao entra na imagem** a menos que o Dockerfile seja alterado para copia-lo. `VITE_API_BASE_URL` so tem efeito se o arquivo certo (`.env`/`.env.production`) estiver no build context E for copiado.

## Testes automatizados

```bash
# API (pytest, SQLite in-memory via fixtures de conftest.py)
cd ~/projetos/patch-manager/apps/api
source .venv/bin/activate
python -m pytest app/tests/ -v

# Agente Linux (usa o mesmo venv da API, so tem stdlib)
cd ~/projetos/patch-manager/apps/agent-linux
source ~/projetos/patch-manager/apps/api/.venv/bin/activate
python -m pytest agent/tests/ -v

# Agente Windows (idem)
cd ~/projetos/patch-manager/apps/agent-windows
source ~/projetos/patch-manager/apps/api/.venv/bin/activate
python -m pytest agent/tests/ -v

# Frontend (typecheck)
cd ~/projetos/patch-manager/apps/web
npx tsc -b
```

Auth em teste de API: `apps/api/app/tests/conftest.py` ja tem overrides para `get_db`/`get_agent_identity`. Endpoints com `require_operator`/`require_admin` precisam de override pontual no proprio teste (ver `test_machines_identity_conflict.py` ou `test_schedules_monthly_weekday.py` como referencia — classe `_FakeOperator` + `app.dependency_overrides[require_operator] = lambda: _FakeOperator()`, sempre limpando no `finally`).

## Variaveis de ambiente e segredos (nomes apenas — nunca commitar valores reais)

| Variavel | Onde e usada | Arquivo de origem (valor real) |
|---|---|---|
| `POSTGRES_PASSWORD`, `POSTGRES_USER`, `POSTGRES_DB` | container `db` | `infra/compose/.env` |
| `PATCH_MANAGER_HTTP_PORT`, `PATCH_MANAGER_HTTPS_PORT` | gateway nginx | `infra/compose/.env` |
| `JWT_SECRET`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES` | autenticacao da API | `infra/env/api.env` |
| `DATABASE_URL` | conexao da API ao Postgres | `infra/env/api.env` |
| `SEED_ADMIN_USERNAME`, `SEED_ADMIN_PASSWORD` | usuario admin criado no seed (`python -m app.seed`) | `infra/env/api.env` |
| `AGENT_BOOTSTRAP_TOKEN` | token usado por agentes novos para se cadastrar | `infra/env/api.env` (tambem editavel via UI em Configuracoes) |
| `SEED_LINUX_AGENT_ID`, `SEED_LINUX_AGENT_KEY` | credencial do agente Linux de demo/seed | `infra/env/api.env` |
| `PATCH_MANAGER_AGENT_KEY`, `PATCH_MANAGER_AGENT_ID` | credencial de um agente instalado (Linux/Windows) | `.env` local do agente (`/etc/patch-manager/...` ou `C:\ProgramData\PatchManager\agent-windows.env`) |
| `PATCH_MANAGER_ALLOW_SECURITY_ONLY`, `PATCH_MANAGER_ALLOW_SECURITY_AND_CRITICAL` | fallback local do guardrail quando o agente esta offline da central | `.env` do agente Linux |

Os arquivos `*.env.example` no repo (`infra/compose/.env.example`, `infra/env/api.env.example`) documentam todas as chaves esperadas com valores placeholder — sempre usa-los como referencia de "quais variaveis existem", nunca os valores reais que ja estejam em `infra/compose/.env`/`infra/env/api.env` (esses dois arquivos sao gitignored).

Login do seed admin (painel web): usuario/senha vem de `SEED_ADMIN_USERNAME`/`SEED_ADMIN_PASSWORD` em `infra/env/api.env` — confirmar o valor la, nao assumir o default do `.env.example`.

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
