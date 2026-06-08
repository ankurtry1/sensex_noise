#!/usr/bin/env bash
set -euo pipefail

# Stop only the market-worker container. Do not stop auth-web and do not delete data.

REPO_DIR="${REPO_DIR:-/opt/sensex-noise}"
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
TZ="${TZ:-Asia/Kolkata}"
export TZ

cd "${REPO_DIR}"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi

DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"
RUNTIME_DIR="${RUNTIME_DIR:-${DATA_DIR}/runtime}"
WORKER_STATUS_PATH="${WORKER_STATUS_PATH:-${RUNTIME_DIR}/worker_status.json}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"
export DATA_DIR RUNTIME_DIR WORKER_STATUS_PATH PYTHONPATH

mkdir -p "${RUNTIME_DIR}"

write_status() {
  "${PYTHON_BIN}" -m sensex_noise.ops.worker_status write --path "${WORKER_STATUS_PATH}" "$@" >/dev/null
}

notify() {
  "${PYTHON_BIN}" -m sensex_noise.ops.notifier "$@" || true
}

write_status --state stopping --set "last_error=null"
notify --event worker_stopping --status stopping --message "Market worker stop requested"

docker stop sensex-noise-market-worker >/dev/null 2>&1 || true
docker compose "${COMPOSE_FILES[@]}" --profile worker stop market-worker >/dev/null 2>&1 || true

remaining="$(docker ps -q --filter "label=com.docker.compose.project=sensex-noise" --filter "label=com.docker.compose.service=market-worker" --filter "status=running" || true)"
if [[ -n "${remaining}" ]]; then
  write_status --state failed --set "last_error=market-worker container is still running after stop request"
  notify --event worker_failure --status failed --message "Market worker did not stop cleanly"
  echo "Market worker container is still running after stop request." >&2
  exit 1
fi

write_status --state stopped --mark last_stopped_at --set "pid=null" --set "last_exit_code=0" --set "last_error=null"
notify --event worker_stopped --status stopped --message "Market worker stopped"
