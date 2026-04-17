#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${INSTALL_ROOT:-/opt/patch-manager}"
cd "${INSTALL_ROOT}/infra/compose"
docker compose down
