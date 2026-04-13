#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${1:-/opt/patch-manager/agent-linux}"
SERVICE_NAME="patch-manager-agent-linux.service"
SERVICE_TARGET="/etc/systemd/system/${SERVICE_NAME}"
ENV_TARGET="/etc/patch-manager/agent-linux.env"

sudo mkdir -p "${INSTALL_ROOT}"
sudo mkdir -p /etc/patch-manager
sudo mkdir -p /var/log/patch-manager

sudo rsync -a --delete ./ "${INSTALL_ROOT}/"

if ! id patchmanager >/dev/null 2>&1; then
  sudo useradd --system --create-home --shell /usr/sbin/nologin patchmanager
fi

if [[ ! -f "${ENV_TARGET}" ]]; then
  sudo install -m 640 "${INSTALL_ROOT}/.env.example" "${ENV_TARGET}"
fi

sudo install -m 644 "${INSTALL_ROOT}/deploy/${SERVICE_NAME}" "${SERVICE_TARGET}"
sudo chown -R patchmanager:patchmanager "${INSTALL_ROOT}" /var/log/patch-manager
sudo systemctl daemon-reload

echo "Instalacao concluida."
echo "Revise ${ENV_TARGET} antes de iniciar o servico."
echo "Comandos sugeridos:"
echo "  sudo systemctl enable --now ${SERVICE_NAME}"
echo "  sudo journalctl -u ${SERVICE_NAME} -f"
