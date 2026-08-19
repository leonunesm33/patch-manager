# Sincronização de hostname e detecção de conflito de identidade de agentes

## Contexto / Problema

Servidores no ambiente do usuário nascem a partir de templates com um hostname
provisório e são renomeados ao longo do processo de criação. O agente do
Patch Manager (Linux e Windows) pode ser instalado dentro da imagem base
**antes** desse hostname final ser aplicado — não há confirmação de que o
enroll (geração do `.env` com `agent_id`/`agent_key`) já roda embutido na
imagem ou se ocorre apenas no primeiro boot de cada clone.

Investigação do código atual (`apps/api`, `apps/agent-linux`,
`apps/agent-windows`) revelou dois problemas distintos:

1. **Bug confirmado — hostname congela após o primeiro inventário.**
   Em `submit_agent_inventory` (`apps/api/app/api/v1/agents.py:1295-1461`), o
   campo `Machine.name` só é gravado na criação do registro (linhas
   1419-1433). Em toda sincronização seguinte (linhas 1434-1443), os campos
   `ip`, `platform`, `environment`, `group`, `status`, `pending_patches`,
   `last_check_in` e `risk` são atualizados, mas `name` nunca é
   reatribuído. Se o hostname do SO mudar depois que o registro já existe, o
   painel mostra o nome antigo para sempre — mesmo a tabela separada
   `AgentInventorySnapshotModel` (que alimenta a lista de "agentes
   conectados") sendo atualizada normalmente a cada ciclo, gerando dados
   inconsistentes entre telas.

2. **Risco não confirmado — colisão de identidade em clones de template.**
   O `agent_id` é derivado do hostname **no momento em que o script de
   instalação roda**, não pela API:
   - Linux (guiado): `apps/agent-linux/deploy/install-linux-agent-guided.sh:112-115`
   - Linux (gerado pela API): `apps/api/app/api/v1/agents.py:283-285`
   - Windows (gerado pela API): `apps/api/app/api/v1/agents.py:481`

   Se o enroll (que grava `agent_id`/`agent_key` no `.env`) rodar **antes**
   da imagem virar template, todo clone nasce com a mesma identidade
   completa (mesmo `agent_id` e `agent_key`), fazendo múltiplos servidores
   reais escreverem no mesmo registro `Machine` (`agent-{agent_id}`,
   `apps/api/app/api/v1/agents.py:1413`) sem qualquer restrição de unicidade
   que impeça isso (`ix_machines_name` é `unique=False`,
   `apps/api/alembic/versions/20260409_0001_initial_schema.py:34`).

## Objetivos

- O hostname exibido no Patch Manager deve sempre refletir o hostname atual
  reportado pelo agente, tanto para Linux quanto para Windows.
- Novas instalações de agente não devem correr risco de colisão de
  identidade quando originadas de um template/imagem clonada.
- Se uma colisão de identidade ocorrer mesmo assim (por exemplo, por causa
  de imagens já existentes com enroll pré-feito), isso deve ser detectado e
  sinalizado ao operador, nunca corrigido silenciosamente por trás dos
  panos.

## Não-objetivos

- Não vamos alterar o processo de provisionamento/template do usuário (isso
  é operacional, fora do Patch Manager).
- Não vamos forçar re-enroll de agentes já instalados e funcionando hoje —
  a mudança na geração de `agent_id` vale só para instalações novas.
- Não vamos implementar fusão/split automático de máquinas em conflito —
  a resolução é sempre uma ação manual do operador.

## Visão geral da arquitetura

Três componentes mudam, em camadas independentes que podem ser
implementadas e testadas separadamente:

1. **API / modelo de dados** — `Machine` passa a manter `name` sempre
   sincronizado, mais dois campos novos para o fingerprint de hardware e o
   estado de conflito.
2. **Agentes (Linux e Windows)** — coletam um identificador de hardware
   estável por VM e o enviam junto com o inventário já existente; os
   scripts de instalação passam a gerar `agent_id` como UUID aleatório em
   vez de derivar do hostname.
3. **Painel (apps/web)** — exibe um aviso quando há conflito de identidade
   e oferece uma ação de resolução.

## Mudanças de modelo de dados

Em `apps/api/app/models/machine.py`, adicionar à `Machine`:

- `hardware_fingerprint: str | None` — identificador de hardware visto no
  primeiro inventário recebido para este `agent_id` (ou no primeiro
  inventário após a atualização do agente, para máquinas já existentes).
- `identity_conflict_fingerprint: str | None` — o fingerprint conflitante
  mais recente visto, quando diferente do armazenado.
- `identity_conflict_detected_at: datetime | None` — quando o conflito mais
  recente foi observado.

Nova migration Alembic adicionando essas três colunas, todas nullable, sem
necessidade de backfill (os valores se populam naturalmente conforme os
agentes fazem check-in).

## Mudanças nos agentes

**Coleta de fingerprint** (lido uma vez na inicialização do processo,
mantido em memória — não muda em runtime, evita custo de coleta a cada
heartbeat):

- Linux: leitura de `/sys/class/dmi/id/product_uuid` (acesso direto via
  sysfs, sem dependência de `dmidecode` instalado).
- Windows: `Get-CimInstance Win32_ComputerSystemProduct` (propriedade
  `UUID`), reaproveitando o padrão já usado no agente Windows para outras
  coletas via `subprocess`/PowerShell
  (`apps/agent-windows/agent/inventory.py`).

O fingerprint é incluído apenas no payload de **inventário** (que já grava
em `Machine` hoje), não no heartbeat leve (que só atualiza o estado em
memória de "agente conectado").

Para viabilizar teste local sem hardware real distinto, é adicionada uma
variável de ambiente opcional `PATCH_MANAGER_FINGERPRINT_OVERRIDE`, que,
quando definida, substitui a leitura real — mesmo padrão de variáveis de
simulação já existente no agente Windows (`PATCH_MANAGER_SIMULATE_*`).

**Geração de `agent_id`** — os scripts de instalação passam a gerar um UUID
aleatório em vez de derivar do hostname:

- `apps/agent-linux/deploy/install-linux-agent-guided.sh:112-115`
- `apps/api/app/api/v1/agents.py:283-285` (texto do instalador Linux gerado
  pela API)
- `apps/api/app/api/v1/agents.py:481` (texto do instalador Windows gerado
  pela API)

Formato mantido legível: `linux-<uuid>` / `windows-<uuid>`. Agentes já
instalados continuam usando o `agent_id` atual (derivado do hostname na
instalação) — nenhuma migração de identidade é feita para eles.

## Mudanças na API

Em `submit_agent_inventory` (`apps/api/app/api/v1/agents.py`):

- O schema de payload de inventário ganha um campo opcional
  `hardware_fingerprint: str | None`, compatível com agentes antigos que
  ainda não o enviam.
- **Criação de máquina nova**: grava `name = payload.hostname` e
  `hardware_fingerprint = payload.hardware_fingerprint` (pode ser `None`
  para agentes antigos).
- **Atualização de máquina existente**:
  - `name` é **sempre** reatribuído a `payload.hostname` (corrige o bug
    do hostname congelado).
  - Se `payload.hardware_fingerprint` for `None` → nenhuma lógica de
    fingerprint é executada.
  - Senão, se `machine.hardware_fingerprint` for `None` (máquina criada
    antes deste recurso, ou agente recém-atualizado) → grava como
    baseline, sem conflito.
  - Senão, se os dois valores forem iguais → nenhuma ação.
  - Senão (valores diferentes) → grava
    `identity_conflict_fingerprint = payload.hardware_fingerprint` e
    `identity_conflict_detected_at = now()`, **sem sobrescrever**
    `hardware_fingerprint` original, e registra um warning no log do
    servidor. O conflito é persistente: não se autolimpa se um fingerprint
    que bate com o original voltar a aparecer depois (isso não prova que o
    problema acabou — pode ser a máquina legítima ainda ativa enquanto uma
    clonada intrusa também está reportando).

Novo endpoint `POST /api/v1/machines/{id}/resolve-identity-conflict`
(exige permissão de admin): aceita o `identity_conflict_fingerprint` mais
recente como novo baseline (sobrescreve `hardware_fingerprint`) e limpa os
dois campos de conflito. Essa é a única ação de resolução — nenhuma segunda
opção de "reconhecer sem aceitar" foi incluída, para não complicar o fluxo
sem necessidade real.

O schema de leitura de `Machine` (list/detail) passa a expor os três campos
novos para o frontend.

## Mudanças no painel (apps/web)

- Indicador visual (badge/aviso) na listagem de máquinas quando
  `identity_conflict_detected_at` não é nulo.
- Detalhe da máquina mostra `hardware_fingerprint` (esperado) vs.
  `identity_conflict_fingerprint` (visto por último) e o timestamp.
- Botão de ação que chama o endpoint de resolução.

## Tratamento de erros

- Falha na coleta do fingerprint no agente (permissão negada, PowerShell
  falhou) → o agente envia o campo como ausente/nulo naquele ciclo (mesmo
  valor tratado como "agente antigo, sem fingerprint" na lógica da API) em
  vez de falhar o heartbeat/inventário inteiro — mesmo padrão defensivo já
  usado hoje no agente Windows (`_run_powershell_json` retornando `None`
  em caso de falha).
- Nenhuma trava de concorrência nova é introduzida além do que já existe
  hoje na gravação de `Machine` neste mesmo endpoint.
- Os textos dos instaladores gerados dinamicamente pela API
  (`agents.py`) precisam continuar sendo scripts bash/PowerShell válidos
  após a troca da linha de geração do `agent_id` — validação manual
  executando o script gerado, já que esses textos não têm cobertura de
  teste automatizada hoje.

## Compatibilidade retroativa

- Colunas novas são nullable, sem exigência de backfill.
- Agentes antigos (sem o campo de fingerprint) continuam funcionando sem
  gerar conflito nem erro — o campo simplesmente não é considerado.
- Máquinas já cadastradas antes deste recurso recebem o fingerprint como
  baseline na primeira vez que reportarem com um agente atualizado, sem
  disparar conflito nesse primeiro contato.
- `agent_id` de instalações existentes não é alterado.

## Plano de testes

**Unitários (backend)**, cobrindo os cenários de `submit_agent_inventory`:

1. Máquina nova → grava hostname e fingerprint.
2. Segunda chamada, mesmo hostname e fingerprint → sem conflito, sem
   mudança.
3. Segunda chamada, hostname diferente, fingerprint igual → `name`
   atualizado, sem conflito (caso principal do pedido original: "servidor
   renomeado legitimamente").
4. Segunda chamada, hostname igual, fingerprint diferente → conflito
   registrado, `name` ainda assim atualizado.
5. Máquina existente sem fingerprint registrado → primeiro fingerprint
   vira baseline, sem conflito.
6. Payload sem campo de fingerprint (agente antigo) → nenhuma lógica de
   conflito é executada, sem erro.

**Manual/integração no ambiente Docker Compose do WSL**:

- Usar `PATCH_MANAGER_FINGERPRINT_OVERRIDE` para simular dois "hardwares"
  diferentes reportando o mesmo `agent_id`/`agent_key` e confirmar que o
  aviso aparece no painel.
- Confirmar que o endpoint de resolução limpa o aviso.
- Rodar os scripts de instalação (Linux e Windows) modificados uma vez de
  ponta a ponta para confirmar que o novo esquema de `agent_id` não quebra
  o fluxo de enroll/aprovação.

## Fora de escopo / trabalho futuro

- Ajuste do processo de provisionamento/template do usuário para evitar
  gerar imagens com enroll pré-feito (recomendação operacional, não faz
  parte deste código).
- Fusão automática de histórico entre duas máquinas em conflito.
- Filtro dedicado de "máquinas em conflito" na listagem do painel (o badge
  cobre a necessidade inicial).
