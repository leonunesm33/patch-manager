#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/patch-manager}"
BACKUP_DIR="${BACKUP_DIR:-${INSTALL_ROOT}/backups}"
TIMESTAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${BACKUP_DIR}"
cd "${INSTALL_ROOT}/infra/compose"

source .env

docker compose exec -T db pg_dump -U "${POSTGRES_USER:-patchmanager}" -d "${POSTGRES_DB:-patchmanager}" > "${BACKUP_DIR}/patch-manager-${TIMESTAMP}.sql"

echo "Backup gerado em ${BACKUP_DIR}/patch-manager-${TIMESTAMP}.sql"
