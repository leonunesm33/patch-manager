# Patch Manager POC Operations Guide

## Subir e parar a central

```bash
sudo systemctl start patch-manager-central.service
sudo systemctl stop patch-manager-central.service
sudo systemctl status patch-manager-central.service
```

Ou diretamente:

```bash
cd /opt/patch-manager/infra/compose
docker compose up -d
docker compose down
```

## Healthcheck
- gateway: `https://<host>/health`
- API detalhada: `https://<host>/api/v1/health/detailed`

## Logs

```bash
cd /opt/patch-manager/infra/compose
docker compose logs -f gateway
docker compose logs -f api
docker compose logs -f web
docker compose logs -f db
```

## Backup

```bash
chmod +x /opt/patch-manager/deploy/central/backup-central.sh
/opt/patch-manager/deploy/central/backup-central.sh
```

## Restore

```bash
chmod +x /opt/patch-manager/deploy/central/restore-central.sh
/opt/patch-manager/deploy/central/restore-central.sh /opt/patch-manager/backups/patch-manager-YYYYMMDD-HHMMSS.sql
```

## Smoke test

```bash
export PATCH_MANAGER_PASSWORD='<senha-do-admin>'
chmod +x /opt/patch-manager/deploy/central/smoke-test.sh
/opt/patch-manager/deploy/central/smoke-test.sh
```

## Operacao dos agentes
- agentes novos entram em `Agentes pendentes`
- agentes rejeitados param o processo
- agentes revogados podem ser reintegrados ou reabertos para aprovacao
- agentes parados aparecem separados em `Configuracoes`

## Reboot e apply
- Linux e Windows possuem politica de reboot separada
- `apply` real continua protegido por guardrails
- hosts com reboot pendente ou agendado aparecem no dashboard e em operacoes

## Perfis de acesso
- `admin`: configuracoes globais, bootstrap token, mudancas sensiveis
- `operator`: operacao diaria, aprovacoes, agendamentos, execucoes e acoes nos hosts
- `viewer`: leitura de dashboard, relatorios, maquinas e status
