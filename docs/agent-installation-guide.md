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
