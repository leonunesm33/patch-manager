Coloque aqui um runtime embutido do Python para o agente Windows.

Estrutura esperada:

- `runtime/python.exe`
- bibliotecas e DLLs associadas ao runtime embarcado

Quando esses arquivos existirem, o instalador remoto do agente Windows vai copiá-los
automaticamente para o host e o launcher `agent/run-agent.ps1` vai priorizar
`runtime/python.exe` antes de procurar Python no sistema.
