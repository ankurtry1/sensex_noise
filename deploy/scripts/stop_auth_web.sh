#!/usr/bin/env bash
set -euo pipefail

# Stop the Docker Compose services cleanly.

if [[ ! -f docker-compose.yml || ! -f docker-compose.prod.yml ]]; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

docker compose -f docker-compose.yml -f docker-compose.prod.yml down
