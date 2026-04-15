# Agent Windows

Base do agente Windows para homologacao controlada.

## Estado atual

- heartbeat, check-in e inventario
- bootstrap enrollment com aprovacao no console
- claim de jobs Windows
- `dry-run`, `StartScan` controlado e opcionalmente `StartDownload` + `StartInstall`
- logs em console e opcionalmente em arquivo
- loop com retry/backoff
- instalacao remota e upgrade por script PowerShell
- launcher preparado para usar `dist/PatchManagerAgentWindows.exe` ou `runtime/python.exe`

## Execucao manual

```powershell
cd apps/agent-windows
copy .env.example .env
python agent/main.py
```

## Variaveis principais

- `PATCH_MANAGER_API`: endpoint base da API de agentes
- `PATCH_MANAGER_AGENT_KEY`: credencial secreta do agente
- `PATCH_MANAGER_AGENT_ID`: identificador unico do host
- `PATCH_MANAGER_BOOTSTRAP_TOKEN`: token de cadastro inicial
- `PATCH_MANAGER_ENABLE_WINDOWS_SCAN_APPLY`: libera `UsoClient StartScan`
- `PATCH_MANAGER_ENABLE_WINDOWS_DOWNLOAD_INSTALL`: libera `StartDownload` e `StartInstall`
- `PATCH_MANAGER_WINDOWS_COMMAND_TIMEOUT`: timeout dos comandos PowerShell
- `PATCH_MANAGER_LOG_FILE`: arquivo local de log

## Instalacao remota

No painel, em `Configuracoes`, o sistema gera dois comandos:

- instalacao Windows
- atualizacao Windows

O instalador remoto:

- grava os arquivos em `C:\ProgramData\PatchManager\agent-windows`
- grava o ambiente em `C:\ProgramData\PatchManager\agent-windows.env`
- registra a task `PatchManagerAgentWindows`
- usa o launcher `agent\run-agent.ps1`
- inicia o agente automaticamente

## Empacotamento para producao

O projeto agora suporta tres estrategias de runtime para o agente Windows, nesta ordem:

1. `dist\PatchManagerAgentWindows.exe`
2. `runtime\python.exe`
3. Python real do host

Pastas relevantes:

- `dist/`
- `runtime/`
- `deploy/build-standalone-exe.ps1`
- `deploy/build-runtime-layout.ps1`
- `deploy/patch-manager-agent-windows.spec`

Fluxo sugerido para homologacao real:

1. gerar um `.exe` standalone com `build-standalone-exe.ps1`
2. ou copiar um runtime Python dedicado para `runtime/`
3. publicar esses artefatos junto do agente no repositório/servidor
4. rodar a instalacao remota no host Windows
5. validar que a task usa `agent\run-agent.ps1`

Exemplo de build standalone:

```powershell
cd apps/agent-windows
pip install pyinstaller
.\deploy\build-standalone-exe.ps1
```

Resultado esperado:

- `dist\PatchManagerAgentWindows.exe`

Assim que esse arquivo existir, a instalacao remota e o upgrade remoto vao copiá-lo automaticamente
para o host Windows e o launcher vai passar a usa-lo com prioridade maxima.

## Fluxo sugerido de homologacao

1. gerar o comando de instalacao Windows no painel
2. rodar em PowerShell administrativo
3. aprovar o host em `Agentes pendentes`
4. validar o inventario na UI
5. testar `dry-run`
6. liberar `StartScan`
7. liberar `StartDownload` e `StartInstall` apenas em ambiente controlado
