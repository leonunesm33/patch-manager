# Audit and Traceability

## O que a plataforma registra hoje
- usuario que aprovou ou rejeitou patch
- usuario que revogou, reintegrou ou solicitou reboot de agente
- eventos operacionais de bootstrap token, apply real, reboot e acoes administrativas
- jobs por host com status, erro e agente que fez claim
- execucoes por host e patch
- comandos operacionais por agente e solicitante

## Onde consultar
- `Relatorios`
- `Operacoes`
- detalhe do host em `Maquinas`
- `Configuracoes` para eventos operacionais

## Granularidade atual
- por maquina
- por patch
- por agente
- por usuario solicitante nas acoes operacionais

## Gap conhecido
- ainda nao existe uma trilha unica consolidada em um unico modelo de auditoria enterprise
- para a POC, a rastreabilidade esta distribuida entre eventos operacionais, jobs, execucoes e comandos
