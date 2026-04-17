# Patch Manager Scope and Limits

## Coberto na POC atual
- central unica com frontend, API, banco, redis e gateway TLS
- agentes Linux e Windows com bootstrap e aprovacao
- inventario e status por host
- aprovacao de patches
- agendamentos
- fila de jobs e retorno de status
- guardrails de execucao
- reboot manual e politica basica pos-patch
- trilha operacional e filtros de maquina

## Fora de escopo nesta fase
- alta disponibilidade
- multi-tenant completo com isolamento forte por cliente
- SSO corporativo
- PKI e certificados emitidos por CA corporativa
- RBAC granular por recurso
- integracao nativa com ITSM/CMDB
- rollback automatico de patches do sistema operacional
- relatorios executivos completos por SLA

## Multiambiente minimo
- grupos de maquinas
- campo de ambiente nas maquinas
- separacao operacional entre homologacao e producao no inventario e filtros

## Observacao comercial
Esta POC demonstra operacao real e fluxo funcional, mas ainda nao deve ser vendida como substituto completo de uma plataforma enterprise de patch management sem backlog adicional de produto.
