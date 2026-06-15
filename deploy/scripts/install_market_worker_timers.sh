#!/usr/bin/env bash
set -euo pipefail

# Install systemd service/timer templates for market-worker scheduling.
# Timers are only enabled when --enable is supplied.

ENABLE_TIMERS=false
ENABLE_CONTROLS=false
SET_TIMEZONE=false

for arg in "$@"; do
  case "${arg}" in
    --enable)
      ENABLE_TIMERS=true
      ;;
    --enable-controls)
      ENABLE_CONTROLS=true
      ;;
    --set-timezone)
      SET_TIMEZONE=true
      ;;
    *)
      echo "Unknown argument: ${arg}" >&2
      echo "Usage: $0 [--enable] [--enable-controls] [--set-timezone]" >&2
      exit 2
      ;;
  esac
done

if [[ ! -d deploy/systemd ]]; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

if [[ "${SET_TIMEZONE}" == "true" ]]; then
  sudo timedatectl set-timezone Asia/Kolkata
fi

current_tz="$(timedatectl show -p Timezone --value 2>/dev/null || true)"
if [[ "${current_tz}" != "Asia/Kolkata" ]]; then
  echo "Warning: VM timezone is '${current_tz:-unknown}', expected Asia/Kolkata." >&2
  echo "Run again with --set-timezone if you want this script to set it." >&2
fi

sudo install -m 0644 deploy/systemd/sensex-market-worker.service /etc/systemd/system/sensex-market-worker.service
sudo install -m 0644 deploy/systemd/sensex-market-worker.timer /etc/systemd/system/sensex-market-worker.timer
sudo install -m 0644 deploy/systemd/sensex-market-worker-stop.service /etc/systemd/system/sensex-market-worker-stop.service
sudo install -m 0644 deploy/systemd/sensex-market-worker-stop.timer /etc/systemd/system/sensex-market-worker-stop.timer
sudo install -m 0644 deploy/systemd/sensex-worker-command.service /etc/systemd/system/sensex-worker-command.service
sudo install -m 0644 deploy/systemd/sensex-worker-command.path /etc/systemd/system/sensex-worker-command.path

sudo systemctl daemon-reload

if [[ "${ENABLE_TIMERS}" == "true" ]]; then
  sudo systemctl enable --now sensex-market-worker.timer sensex-market-worker-stop.timer
  echo "Market-worker timers enabled."
else
  echo "Market-worker timers installed but not enabled. Re-run with --enable to enable them."
fi

if [[ "${ENABLE_CONTROLS}" == "true" ]]; then
  sudo systemctl enable --now sensex-worker-command.path
  echo "Worker command path enabled."
else
  echo "Worker command path installed but not enabled. Re-run with --enable-controls to enable GUI start/stop."
fi

systemctl list-timers --all --no-pager 'sensex-market-worker*'
systemctl status sensex-worker-command.path --no-pager || true
