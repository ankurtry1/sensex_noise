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
COMMAND_LOG="${LOGS_DIR}/worker-command-${TODAY}.log"

cd "${REPO_DIR}"
mkdir -p "${COMMAND_DIR}" "${LOGS_DIR}" "${RUNTIME_DIR}"

log_command() {
  echo "$(date -Is) $*" >>"${COMMAND_LOG}"
  if [[ "$(id -u)" -eq 0 ]] && id sensexbot >/dev/null 2>&1; then
    chown sensexbot:sensexbot "${COMMAND_LOG}" || true
  fi
}

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
  systemctl stop sensex-market-worker.service >>"${COMMAND_LOG}" 2>&1 || true
  systemctl start sensex-market-worker-stop.service >>"${COMMAND_LOG}" 2>&1 || true
  log_command "stop requested"
fi

if [[ "${run_start}" == "true" ]]; then
  if systemctl is-active --quiet sensex-market-worker.service || docker ps --format '{{.Names}}' | grep -qx 'sensex-noise-market-worker'; then
    log_command "start skipped: market worker already running"
  else
    systemctl start sensex-market-worker.service >>"${COMMAND_LOG}" 2>&1
    log_command "start requested via systemd"
  fi
fi
