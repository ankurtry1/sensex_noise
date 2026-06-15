#!/usr/bin/env bash
set -euo pipefail

# Dispatch start/stop requests written by the admin UI. This script is intended
# to run as the app user from a systemd path-triggered oneshot service.

REPO_DIR="${REPO_DIR:-/opt/sensex-noise}"
DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"
RUNTIME_DIR="${RUNTIME_DIR:-${DATA_DIR}/runtime}"
LOGS_DIR="${LOGS_DIR:-${DATA_DIR}/logs}"
COMMAND_DIR="${WORKER_COMMAND_DIR:-${RUNTIME_DIR}/commands}"
LOCK_PATH="${RUNTIME_DIR}/worker_command_dispatch.lock"
TODAY="$(TZ=Asia/Kolkata date +%F)"

cd "${REPO_DIR}"
mkdir -p "${COMMAND_DIR}" "${LOGS_DIR}" "${RUNTIME_DIR}"

exec 8>"${LOCK_PATH}"
flock -n 8 || exit 0

run_stop=false
run_start=false

if [[ -f "${COMMAND_DIR}/stop.request" ]]; then
  run_stop=true
  rm -f "${COMMAND_DIR}/stop.request"
fi

if [[ -f "${COMMAND_DIR}/start.request" ]]; then
  run_start=true
  rm -f "${COMMAND_DIR}/start.request"
fi

if [[ "${run_stop}" == "true" ]]; then
  ./deploy/scripts/stop_market_worker.sh >>"${LOGS_DIR}/worker-command-${TODAY}.log" 2>&1 || true
fi

if [[ "${run_start}" == "true" ]]; then
  if docker ps --format '{{.Names}}' | grep -qx 'sensex-noise-market-worker'; then
    echo "$(date -Is) start skipped: market worker already running" >>"${LOGS_DIR}/worker-command-${TODAY}.log"
  else
    nohup ./deploy/scripts/run_market_worker_once.sh \
      >"${LOGS_DIR}/market-worker-wrapper-${TODAY}.log" 2>&1 &
    echo "$(date -Is) start requested: pid=$!" >>"${LOGS_DIR}/worker-command-${TODAY}.log"
  fi
fi
