#!/usr/bin/env bash
set -euo pipefail

# Retention cleanup for old logs and tape data.
# Default is dry-run. Set DRY_RUN=false to delete matched files.
# The script skips paths containing today's YYYY-MM-DD date string.

DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
DRY_RUN="${DRY_RUN:-true}"
TODAY="$(date +%F)"

if ! [[ "${RETENTION_DAYS}" =~ ^[0-9]+$ ]]; then
  echo "RETENTION_DAYS must be a non-negative integer." >&2
  exit 1
fi

targets=(
  "${DATA_DIR}/logs"
  "${DATA_DIR}/data/tape"
)

echo "Retention days: ${RETENTION_DAYS}"
echo "Dry run: ${DRY_RUN}"
echo "Skipping paths containing today's date: ${TODAY}"

for target in "${targets[@]}"; do
  if [[ ! -d "${target}" ]]; then
    echo "Skipping missing directory: ${target}"
    continue
  fi

  find "${target}" -type f -mtime +"${RETENTION_DAYS}" -print0 |
    while IFS= read -r -d '' file; do
      if [[ "${file}" == *"${TODAY}"* ]]; then
        echo "SKIP current-day path: ${file}"
        continue
      fi

      if [[ "${DRY_RUN}" == "false" ]]; then
        rm -f -- "${file}"
        echo "DELETED ${file}"
      else
        echo "WOULD_DELETE ${file}"
      fi
    done
done

if [[ "${DRY_RUN}" != "false" ]]; then
  echo "Dry-run only. Re-run with DRY_RUN=false to delete old files."
fi
