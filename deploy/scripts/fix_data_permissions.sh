#!/usr/bin/env bash
set -euo pipefail

# Normalize production data ownership so auth-web and market-worker can share
# token/runtime/log files without daily chown fixes.

APP_USER="${APP_USER:-sensexbot}"
DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run as root, for example: sudo $0" >&2
  exit 1
fi

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "App user not found: ${APP_USER}" >&2
  exit 1
fi

APP_GROUP="$(id -gn "${APP_USER}")"

install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${DATA_DIR}"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${DATA_DIR}/logs"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${DATA_DIR}/data"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${DATA_DIR}/data/tape"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${DATA_DIR}/runtime"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0755 "${DATA_DIR}/runtime/commands"
install -d -o "${APP_USER}" -g "${APP_GROUP}" -m 0700 "${DATA_DIR}/token-store"

chown -R "${APP_USER}:${APP_GROUP}" "${DATA_DIR}/logs" "${DATA_DIR}/data" "${DATA_DIR}/runtime"
chown -R "${APP_USER}:${APP_GROUP}" "${DATA_DIR}/token-store"
chmod 0755 "${DATA_DIR}" "${DATA_DIR}/logs" "${DATA_DIR}/data" "${DATA_DIR}/data/tape" "${DATA_DIR}/runtime"
chmod 0755 "${DATA_DIR}/runtime/commands"
chmod 0700 "${DATA_DIR}/token-store"

if [[ -f "${DATA_DIR}/token-store/kite_access_token.json" ]]; then
  chown "${APP_USER}:${APP_GROUP}" "${DATA_DIR}/token-store/kite_access_token.json"
  chmod 0600 "${DATA_DIR}/token-store/kite_access_token.json"
fi

cat <<EOF
Data permissions normalized.

APP_USER=${APP_USER}
APP_UID=$(id -u "${APP_USER}")
APP_GID=$(id -g "${APP_USER}")
DATA_DIR=${DATA_DIR}

Add APP_UID and APP_GID above to /opt/sensex-noise/.env.
EOF
