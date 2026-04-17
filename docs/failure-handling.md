# Failure Handling

## Comportamentos definidos
- agente offline: passa a aparecer como parado e o host pode aparecer offline
- credencial revogada: agente volta para bootstrap ou para, conforme o caso
- enrollment rejeitado: agente encerra o processo
- guardrail bloqueado: job falha com motivo classificado
- timeout operacional: agente respeita timeout configurado por plataforma

## Reexecucao segura
- agentes revogados ou rejeitados podem ser reabertos para aprovacao
- hosts podem ser reintegrados a partir do console
- jobs e execucoes falhas ficam visiveis para nova acao operacional

## Diagnostico
- health simples e detalhado
- logs da stack via Docker Compose
- logs locais dos agentes
- status de agente no console

## Observacao
A estrategia atual privilegia previsibilidade e visibilidade para a POC. Retry automatico profundo por tipo de falha ainda pode ser ampliado em uma fase posterior.
