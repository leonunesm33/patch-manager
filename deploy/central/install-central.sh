#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
INSTALL_ROOT="${INSTALL_ROOT:-/opt/patch-manager}"
DOMAIN="${PATCH_MANAGER_DOMAIN:-localhost}"
HTTP_PORT="${PATCH_MANAGER_HTTP_PORT:-80}"
HTTPS_PORT="${PATCH_MANAGER_HTTPS_PORT:-443}"

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Erro: comando '$1' nao encontrado."
    exit 1
  fi
}

require_command docker
require_command openssl

if ! docker compose version >/dev/null 2>&1; then
  echo "Erro: docker compose nao esta disponivel."
  exit 1
fi

read -r -p "Senha inicial do admin [gerar automaticamente]: " ADMIN_PASSWORD
read -r -p "Senha do PostgreSQL [gerar automaticamente]: " POSTGRES_PASSWORD
read -r -p "Bootstrap token dos agentes [gerar automaticamente]: " BOOTSTRAP_TOKEN
read -r -p "Agent key seed [gerar automaticamente]: " AGENT_KEY

ADMIN_PASSWORD="${ADMIN_PASSWORD:-$(openssl rand -base64 24 | tr -d '\n')}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -hex 24)}"
BOOTSTRAP_TOKEN="${BOOTSTRAP_TOKEN:-$(openssl rand -hex 24)}"
AGENT_KEY="${AGENT_KEY:-$(openssl rand -hex 24)}"
JWT_SECRET="$(openssl rand -hex 32)"

sudo mkdir -p "${INSTALL_ROOT}"
sudo rsync -a --delete \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.venv' \
  "${PROJECT_ROOT}/" "${INSTALL_ROOT}/"

sudo mkdir -p "${INSTALL_ROOT}/infra/env" "${INSTALL_ROOT}/infra/certs"

sudo cp "${INSTALL_ROOT}/infra/compose/.env.example" "${INSTALL_ROOT}/infra/compose/.env"
sudo cp "${INSTALL_ROOT}/infra/env/api.env.example" "${INSTALL_ROOT}/infra/env/api.env"

sudo sed -i "s|^PATCH_MANAGER_HTTP_PORT=.*|PATCH_MANAGER_HTTP_PORT=${HTTP_PORT}|" "${INSTALL_ROOT}/infra/compose/.env"
sudo sed -i "s|^PATCH_MANAGER_HTTPS_PORT=.*|PATCH_MANAGER_HTTPS_PORT=${HTTPS_PORT}|" "${INSTALL_ROOT}/infra/compose/.env"
sudo sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=${POSTGRES_PASSWORD}|" "${INSTALL_ROOT}/infra/compose/.env"

sudo sed -i "s|change-me-postgres|${POSTGRES_PASSWORD}|g" "${INSTALL_ROOT}/infra/env/api.env"
sudo sed -i "s|JWT_SECRET=.*|JWT_SECRET=${JWT_SECRET}|" "${INSTALL_ROOT}/infra/env/api.env"
sudo sed -i "s|SEED_ADMIN_PASSWORD=.*|SEED_ADMIN_PASSWORD=${ADMIN_PASSWORD}|" "${INSTALL_ROOT}/infra/env/api.env"
sudo sed -i "s|AGENT_BOOTSTRAP_TOKEN=.*|AGENT_BOOTSTRAP_TOKEN=${BOOTSTRAP_TOKEN}|" "${INSTALL_ROOT}/infra/env/api.env"
sudo sed -i "s|SEED_LINUX_AGENT_KEY=.*|SEED_LINUX_AGENT_KEY=${AGENT_KEY}|" "${INSTALL_ROOT}/infra/env/api.env"
sudo sed -i "s|CORS_ALLOW_ORIGINS=.*|CORS_ALLOW_ORIGINS=https://${DOMAIN},https://127.0.0.1|" "${INSTALL_ROOT}/infra/env/api.env"

if [[ ! -f "${INSTALL_ROOT}/infra/certs/tls.crt" || ! -f "${INSTALL_ROOT}/infra/certs/tls.key" ]]; then
  sudo openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "${INSTALL_ROOT}/infra/certs/tls.key" \
    -out "${INSTALL_ROOT}/infra/certs/tls.crt" \
    -days 365 \
    -subj "/CN=${DOMAIN}"
fi

sudo install -m 644 "${INSTALL_ROOT}/deploy/central/patch-manager-central.service" /etc/systemd/system/patch-manager-central.service
sudo systemctl daemon-reload

cd "${INSTALL_ROOT}/infra/compose"
sudo docker compose up -d --build
sudo systemctl enable patch-manager-central.service >/dev/null 2>&1 || true

cat <<EOF

Instalacao concluida.

URL da central:
  https://${DOMAIN}:${HTTPS_PORT}

Credenciais iniciais:
  usuario: admin
  senha: ${ADMIN_PASSWORD}

Bootstrap token:
  ${BOOTSTRAP_TOKEN}

Seed Linux agent key:
  ${AGENT_KEY}

Proximos passos:
  1. Acessar a central e trocar a senha inicial do admin.
  2. Confiar no certificado TLS self-signed para a POC, se necessario.
  3. Usar os comandos de instalacao dos agentes pelo painel.
EOF
