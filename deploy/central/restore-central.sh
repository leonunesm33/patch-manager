#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Uso: $0 /caminho/do/backup.sql"
  exit 1
fi

BACKUP_FILE="$1"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/patch-manager}"

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Arquivo de backup nao encontrado: ${BACKUP_FILE}"
  exit 1
fi

cd "${INSTALL_ROOT}/infra/compose"
source .env

docker compose exec -T db psql -U "${POSTGRES_USER:-patchmanager}" -d "${POSTGRES_DB:-patchmanager}" < "${BACKUP_FILE}"

echo "Restore concluido a partir de ${BACKUP_FILE}"
