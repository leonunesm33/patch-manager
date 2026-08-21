# Agent Installation Guide

## Linux
O agente Linux pode ser instalado a partir do comando gerado no painel:

```bash
curl -fsSL "https://<central>/api/v1/agents/install/linux.sh?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>" | sudo bash
```

Fluxo:
- instala arquivos em `/opt/patch-manager/agent-linux`
- cria `/etc/patch-manager/agent-linux.env`
- registra `systemd`
- entra em `Agentes pendentes`
- apos aprovacao, passa para `Agentes conectados`

## Windows
O agente Windows pode ser instalado com o comando gerado no painel:

```powershell
powershell -ExecutionPolicy Bypass -Command "irm 'https://<central>/api/v1/agents/install/windows.ps1?server_url=https%3A%2F%2F<central>&bootstrap_token=<token>' | iex"
```

Fluxo:
- instala em `C:\ProgramData\PatchManager\agent-windows`
- cria `C:\ProgramData\PatchManager\agent-windows.env`
- registra task `PatchManagerAgentWindows`
- entra em `Agentes pendentes`
- apos aprovacao, passa para `Agentes conectados`

## Upgrade
- Linux: usar `linux-upgrade.sh`
- Windows: usar `windows-upgrade.ps1`

## Reintegracao
- agente revogado pode ser reaberto para aprovacao
- agente rejeitado pode ser reaberto na fila
- agente parado aparece separado no painel

## Reboot controlado

Agentes podem receber comandos de reboot agendado quando a politica permitir. Para homologacao, valide as flags antes de testar:

Windows:

```env
PATCH_MANAGER_ENABLE_WINDOWS_HOST_REBOOT=true
PATCH_MANAGER_SIMULATE_WINDOWS_HOST_REBOOT=true
```

Linux:

```env
PATCH_MANAGER_ENABLE_HOST_REBOOT=true
PATCH_MANAGER_SIMULATE_HOST_REBOOT=true
```

Somente desative simulacao em hosts de homologacao preparados e depois de confirmar com o operador.

## Reinstalacao

Reinstalar o agente em um host ja enrollado gera um novo Agent ID (UUID aleatorio, nao mais derivado do hostname), entao o host aparecera no painel como um novo enrollment pendente em vez de reaproveitar o registro existente. O operador deve remover manualmente o registro antigo (orfao) dessa maquina no painel apos aprovar o novo enrollment.

## Templates clonados com o agente instalado

Nao crie uma golden image com o agente ja ativo e com o arquivo de ambiente persistido. Clonar `/etc/patch-manager/agent-linux.env` ou `C:\ProgramData\PatchManager\agent-windows.env` replica `PATCH_MANAGER_AGENT_ID` e `PATCH_MANAGER_AGENT_KEY`; todos os clones passam a disputar a mesma maquina e a mesma fila de comandos.

Processo recomendado:

1. instale o agente somente depois de clonar a VM; ou
2. no primeiro boot de cada clone, remova o arquivo de ambiente antes de iniciar o servico e execute a instalacao normal para gerar uma identidade exclusiva.

### Runbook de remediacao iterativa

Quando o painel sinalizar **possivel identidade duplicada**:

1. abra os detalhes operacionais e confira o historico de identidade (hostname, fingerprint e horario);
2. escolha **Forcar reidentificacao (proximo host a conectar)** e confirme digitando o `agent_id` compartilhado;
3. a acao enfileira `force_reidentify` para o `agent_id` antigo. Nao e possivel escolher o host fisico: o primeiro clone que consultar a fila reivindica o comando;
4. aguarde esse host reaparecer em **Agentes pendentes** com o novo UUID e com hostname/IP proprios;
5. aprove o novo enrollment e confirme que ele passa a reportar inventario;
6. repita os passos 2 a 5 sobre o `agent_id` antigo, sempre um comando por vez, ate nenhum novo host aparecer durante a janela operacional definida pela equipe;
7. somente depois dessa observacao, remova manualmente a linha antiga, que nao representa mais um host real.

O fluxo nao revoga nem remove automaticamente a identidade antiga: os clones restantes ainda precisam dela para receber a proxima iteracao. Um comando pendente ou em execucao bloqueia outro `force_reidentify` para o mesmo `agent_id`; um claim sem confirmacao expira apos 15 minutos para permitir recuperacao operacional. Se o bootstrap token estiver expirado, a API rejeita a acao; rotacione o token antes de tentar novamente. Fora de `localhost`, a URL de instalacao precisa usar HTTPS. Como o protocolo atual inclui o bootstrap token na URL do instalador, restrinja logs de proxy/processo durante a remediacao e rotacione o token ao concluir o runbook.

> O resultado `applied` do comando significa que o instalador foi agendado no host que reivindicou a fila. A conclusao real deve ser confirmada pelo novo enrollment e pelo inventario no historico de identidade.
