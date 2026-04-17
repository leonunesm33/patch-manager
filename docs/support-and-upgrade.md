# Support, Upgrade and Rollback

## Atualizacao da central
1. backup do banco
2. `git pull`
3. `docker compose up -d --build`
4. validar `/health` e `/health/detailed`
5. rodar smoke test

## Rollback da central
1. voltar o codigo para o commit anterior
2. `docker compose up -d --build`
3. se necessario, restaurar dump do banco

## Atualizacao dos agentes
- Linux: `linux-upgrade.sh`
- Windows: `windows-upgrade.ps1`

## Atendimento a incidente
- confirmar indisponibilidade real da central
- confirmar se o problema e gateway, API, banco ou agente
- coletar:
  - logs do gateway
  - logs da API
  - logs do agente
  - status do agente no console

## Evidencias minimas
- horario do incidente
- host afetado
- agente afetado
- patch/job/comando associado
- erro visivel no painel ou nos logs
