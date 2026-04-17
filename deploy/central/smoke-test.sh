#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://localhost}"
USERNAME="${PATCH_MANAGER_USERNAME:-admin}"
PASSWORD="${PATCH_MANAGER_PASSWORD:-}"

if [[ -z "${PASSWORD}" ]]; then
  echo "Defina PATCH_MANAGER_PASSWORD para rodar o smoke test."
  exit 1
fi

curl -ksSf "${BASE_URL}/health" >/dev/null

TOKEN="$(curl -ksSf \
  -H 'Content-Type: application/json' \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}" \
  "${BASE_URL}/api/v1/auth/login" | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')"

curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/auth/me" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/dashboard" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/machines" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/patches" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/schedules" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/reports" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/settings" >/dev/null
curl -ksSf -H "Authorization: Bearer ${TOKEN}" "${BASE_URL}/api/v1/agents/connected" >/dev/null

echo "Smoke test concluido com sucesso para ${BASE_URL}"
