#!/usr/bin/env bash
set -euo pipefail

# Run one market-worker session on the VM.
# This is intended for systemd or an explicit operator command as the sensexbot user.
# It never prints token contents and relies on scripts/run_market_day.py for trading logic.

REPO_DIR="${REPO_DIR:-/opt/sensex-noise}"
COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
TZ="${TZ:-Asia/Kolkata}"
export TZ

cd "${REPO_DIR}"

if [[ ! -f .env ]]; then
  echo "Missing ${REPO_DIR}/.env; cannot start market worker." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"
LOGS_DIR="${LOGS_DIR:-${DATA_DIR}/logs}"
RUNTIME_DIR="${RUNTIME_DIR:-${DATA_DIR}/runtime}"
TOKEN_STORE_PATH="${TOKEN_STORE_PATH:-${DATA_DIR}/token-store/kite_access_token.json}"
WORKER_STATUS_PATH="${WORKER_STATUS_PATH:-${RUNTIME_DIR}/worker_status.json}"
WRAPPER_LOCK_PATH="${WRAPPER_LOCK_PATH:-${RUNTIME_DIR}/market_worker_wrapper.lock}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"
export DATA_DIR LOGS_DIR RUNTIME_DIR TOKEN_STORE_PATH WORKER_STATUS_PATH PYTHONPATH

mkdir -p "${RUNTIME_DIR}" "${LOGS_DIR}" "$(dirname "${TOKEN_STORE_PATH}")"

write_status() {
  "${PYTHON_BIN}" -m sensex_noise.ops.worker_status write --path "${WORKER_STATUS_PATH}" "$@" >/dev/null
}

notify() {
  "${PYTHON_BIN}" -m sensex_noise.ops.notifier "$@" || true
}

token_check="$("${PYTHON_BIN}" - <<'PY'
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

path = Path(os.environ["TOKEN_STORE_PATH"])
today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
try:
    data = json.loads(path.read_text(encoding="utf-8"))
except Exception:
    print(json.dumps({"ok": False, "trading_date": today}))
    raise SystemExit(0)
ok = bool(str(data.get("access_token") or "").strip()) and data.get("trading_date") == today
print(json.dumps({"ok": ok, "trading_date": today}))
PY
)"
token_ok="$("${PYTHON_BIN}" -c 'import json,sys; print(str(json.load(sys.stdin)["ok"]).lower())' <<<"${token_check}")"
trading_date="$("${PYTHON_BIN}" -c 'import json,sys; print(json.load(sys.stdin)["trading_date"])' <<<"${token_check}")"

exec 9>"${WRAPPER_LOCK_PATH}"
if ! flock -n 9; then
  write_status --state failed --mark last_start_attempt_at --set "last_error=market worker wrapper is already running" --set "token_present=${token_ok}" --set "trading_date=${trading_date}"
  notify --event worker_failure --status duplicate --message "Market worker start skipped: wrapper already running"
  echo "Market worker wrapper is already running." >&2
  exit 3
fi

if docker ps -q --filter "label=com.docker.compose.project=sensex-noise" --filter "label=com.docker.compose.service=market-worker" --filter "status=running" | grep -q .; then
  write_status --state failed --mark last_start_attempt_at --set "last_error=market-worker container is already running" --set "token_present=${token_ok}" --set "trading_date=${trading_date}"
  notify --event worker_failure --status duplicate --message "Market worker start skipped: container already running"
  echo "Market worker container is already running." >&2
  exit 3
fi
docker rm -f sensex-noise-market-worker >/dev/null 2>&1 || true

if [[ "${token_ok}" != "true" ]]; then
  write_status --state failed --mark last_start_attempt_at --set "last_error=today token is missing" --set "token_present=false" --set "trading_date=${trading_date}"
  notify --event worker_failure --status missing_token --message "Market worker did not start because today's Kite token is missing"
  echo "Today's Kite token is missing; complete Kite authentication first." >&2
  exit 2
fi

write_status --state starting --mark last_start_attempt_at --set "last_error=null" --set "last_exit_code=null" --set "token_present=true" --set "trading_date=${trading_date}" --set "container_name=sensex-noise-market-worker"
notify --event worker_starting --status starting --message "Market worker start requested"

set +e
docker compose "${COMPOSE_FILES[@]}" --profile worker run --rm --name sensex-noise-market-worker market-worker &
worker_pid=$!
set -e

write_status --state running --mark last_started_at --mark last_heartbeat_at --set "pid=${worker_pid}" --set "token_present=true" --set "trading_date=${trading_date}" --set "container_name=sensex-noise-market-worker"
notify --event worker_started --status running --message "Market worker started"

heartbeat() {
  while kill -0 "${worker_pid}" 2>/dev/null; do
    write_status --state running --mark last_heartbeat_at --set "pid=${worker_pid}" --set "token_present=true" --set "trading_date=${trading_date}" --set "container_name=sensex-noise-market-worker"
    sleep 30
  done
}
heartbeat &
heartbeat_pid=$!

set +e
wait "${worker_pid}"
exit_code=$?
kill "${heartbeat_pid}" 2>/dev/null || true
wait "${heartbeat_pid}" 2>/dev/null || true
set -e

if [[ "${exit_code}" -eq 0 ]]; then
  write_status --state stopped --mark last_stopped_at --set "last_exit_code=0" --set "last_error=null" --set "pid=null" --set "token_present=true" --set "trading_date=${trading_date}"
  notify --event worker_stopped --status stopped --message "Market worker stopped cleanly"
else
  write_status --state failed --mark last_stopped_at --set "last_exit_code=${exit_code}" --set "last_error=market worker exited non-zero" --set "pid=null" --set "token_present=true" --set "trading_date=${trading_date}"
  notify --event worker_failure --status failed --message "Market worker exited with a non-zero status"
fi

exit "${exit_code}"
