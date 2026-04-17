# Patch Manager POC Homologation Criteria

## A central e considerada pronta para entrega quando:

### Instalacao
- a stack sobe via `install-central.sh`
- gateway, web, api, db e redis ficam saudaveis
- o painel responde em HTTPS

### Autenticacao e seguranca minima
- o admin inicial precisa trocar a senha
- perfis `admin`, `operator` e `viewer` funcionam
- segredos nao ficam fixos em codigo para a instalacao da POC

### Fluxo funcional
- host Linux instala, entra em pendentes, e pode ser aprovado
- host Windows instala, entra em pendentes, e pode ser aprovado
- inventario chega na central
- patch pode ser aprovado
- schedule pode ser criado
- job pode ser acompanhado em relatorios
- status pos-patch fica visivel

### Persistencia
- a central volta apos reboot do host
- banco preserva dados apos restart
- agentes persistem credencial e retornam sem reenrollment indevido

### Operacao
- logs sao acessiveis
- healthcheck simples e detalhado respondem
- backup e restore funcionam
- smoke test automatizado passa

### Auditoria e rastreabilidade
- aprovacao de patch identifica o usuario
- eventos operacionais ficam registrados
- jobs, execucoes e comandos do agente ficam visiveis por host
