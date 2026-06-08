# Roadmap

## Entregue na POC atual

- monorepo com frontend, API, agentes, infraestrutura e documentacao
- frontend navegavel com dashboard, maquinas, aprovacoes, agendamentos, operacoes, relatorios, configuracoes e usuarios
- backend FastAPI com PostgreSQL, Redis, JWT, migrations, scheduler e worker
- Docker Compose para central local/POC com gateway TLS
- agentes Linux e Windows com bootstrap, aprovacao, inventario, check-in, comandos e upgrade remoto
- inventario de updates pendentes Linux e Windows
- aprovacoes com patches pendentes e gerenciados
- agendamentos por maquina, grupo ou sistema operacional
- horarios separados para instalacao e reboot
- grupos de maquinas gerenciados no menu `Maquinas`
- operacoes para fila, comandos, agentes e pendencias
- relatorios com exportacoes CSV, JSON, HTML, PDF e Excel-compativel
- documentacao de POC, operacao, troubleshooting, homologacao e limites

## Proximas evolucoes recomendadas

- implementar exportacao `.xlsx` real e PDF server-side
- adicionar testes automatizados para scheduler, reboot e aprovacoes
- melhorar rastreabilidade visual de comandos agendados por politica
- reforcar RBAC granular por recurso e segregacao por ambiente/cliente
- criar pipeline de release assinado para o agente Windows
- homologar apply real Linux em ambiente dedicado
- homologar instalacao Windows real com politicas corporativas
- adicionar dashboard executivo de SLA e compliance
- integrar logs estruturados com stack externa de observabilidade
