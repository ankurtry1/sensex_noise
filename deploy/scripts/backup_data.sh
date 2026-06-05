#!/usr/bin/env bash
set -euo pipefail

# Create a timestamped backup of lightweight persistent data.
# Secrets are excluded by default, including .env and token-store files.
# Large tick/tape data is excluded unless INCLUDE_TICK_DATA=true is set.

DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/sensex-noise}"
INCLUDE_TICK_DATA="${INCLUDE_TICK_DATA:-false}"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
ARCHIVE="${BACKUP_DIR}/sensex-noise-data-${TIMESTAMP}.tar.gz"

if [[ ! -d "${DATA_DIR}" ]]; then
  echo "Data directory not found: ${DATA_DIR}" >&2
  exit 1
fi

mkdir -p "${BACKUP_DIR}"

exclude_args=(
  --exclude='.env'
  --exclude='.env.*'
  --exclude='token-store'
  --exclude='token-store/*'
  --exclude='runtime/*.lock'
)

if [[ "${INCLUDE_TICK_DATA}" != "true" ]]; then
  exclude_args+=(
    --exclude='data/tape'
    --exclude='data/tape/*'
    --exclude='logs/ticks'
    --exclude='logs/ticks/*'
  )
fi

echo "Creating backup archive: ${ARCHIVE}"
tar -C "${DATA_DIR}" "${exclude_args[@]}" -czf "${ARCHIVE}" .
chmod 600 "${ARCHIVE}"

echo "Backup complete."
echo "Archive: ${ARCHIVE}"
echo "Token-store files and .env files were excluded."
