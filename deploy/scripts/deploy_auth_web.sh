#!/usr/bin/env bash
set -euo pipefail

# Build and start only the auth-web service on the VM.
# Requires a manually-created .env file. Values are validated but never printed.

COMPOSE_FILES=(-f docker-compose.yml -f docker-compose.prod.yml)
REQUIRED_KEYS=(
  KITE_API_KEY
  KITE_API_SECRET
  ADMIN_TOKEN
  APP_BASE_URL
  DATA_DIR
  LOGS_DIR
  RUNTIME_DIR
  TOKEN_STORE_PATH
)

if [[ ! -f docker-compose.yml || ! -f docker-compose.prod.yml ]]; then
  echo "Run this script from the repository root." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "Missing .env. Create it manually from .env.cloud.example before deploying." >&2
  exit 1
fi

if grep -q '^KITE_ACCESS_TOKEN=' .env; then
  echo "KITE_ACCESS_TOKEN must not be stored in .env. Remove it before deploying." >&2
  exit 1
fi

missing=0
for key in "${REQUIRED_KEYS[@]}"; do
  if grep -q "^${key}=[^[:space:]]" .env; then
    echo "${key}: present"
  else
    echo "${key}: missing_or_empty" >&2
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  echo "Fix missing .env keys before deploying." >&2
  exit 1
fi

echo "Building Docker image..."
docker compose "${COMPOSE_FILES[@]}" build

echo "Starting auth-web..."
docker compose "${COMPOSE_FILES[@]}" up -d auth-web

echo "Checking local health endpoint..."
curl -fsS http://127.0.0.1:8000/health
echo

cat <<'EOF'

Auth web is running.

Admin status test:
  set -a
  . ./.env
  set +a
  curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/admin/status

Logs:
  docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f auth-web

Stop:
  ./deploy/scripts/stop_auth_web.sh
EOF
