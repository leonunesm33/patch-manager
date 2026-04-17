# Patch Manager POC Demo Script

## Historia da demo
Mostrar uma central unica que descobre hosts, recebe inventario, controla aprovacao de updates, agenda execucao, acompanha status em tempo real e mantem trilha operacional.

## Ambiente recomendado
- 1 central Ubuntu com a stack Docker
- 1 host Linux homologado com agente ativo
- 1 host Windows homologado com agente ativo
- ao menos um host com updates pendentes, ou inventario de laboratorio preparado

## Roteiro
1. Abrir o dashboard e mostrar:
   - conformidade
   - reboot pendente
   - comandos operacionais
2. Ir em `Configuracoes`:
   - mostrar agentes conectados, pendentes, parados e revogados
   - mostrar bootstrap e guardrails
3. Ir em `Maquinas`:
   - filtrar por ambiente e origem
   - abrir o detalhe operacional de um host
4. Ir em `Patches`:
   - aprovar um patch
5. Ir em `Agendamentos`:
   - mostrar a janela de manutencao
6. Ir em `Relatorios`:
   - enfileirar/processar ou aguardar o fluxo automatico
   - mostrar jobs, status e falhas visiveis
7. Voltar ao dashboard:
   - mostrar atualizacao do estado pos-patch
8. Mostrar `Operacoes`:
   - aprovar agente pendente ou solicitar reboot manual

## Mensagem de valor
- menos operacao manual distribuida
- visibilidade unica de Linux e Windows
- controle de aprovacao e guardrails antes do apply
- onboarding de agentes com bootstrap simples
