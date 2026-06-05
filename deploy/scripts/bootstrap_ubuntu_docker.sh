#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a fresh Ubuntu 22.04/24.04 VM for the Sensex Noise Docker deployment.
# This script installs Docker, creates the app/data directories, and optionally
# clones the repository when a repo URL is supplied as the first argument.
# It never writes secrets and does not create a production .env file.

APP_USER="${APP_USER:-sensexbot}"
APP_DIR="${APP_DIR:-/opt/sensex-noise}"
DATA_DIR="${DATA_DIR:-/var/lib/sensex-noise}"
REPO_URL="${1:-}"

if [[ ! -f /etc/os-release ]]; then
  echo "Cannot detect OS. This script supports Ubuntu 22.04/24.04." >&2
  exit 1
fi

# shellcheck disable=SC1091
. /etc/os-release
if [[ "${ID:-}" != "ubuntu" ]]; then
  echo "Unsupported OS: ${ID:-unknown}. Use Ubuntu 22.04 or 24.04." >&2
  exit 1
fi

if [[ "${VERSION_ID:-}" != "22.04" && "${VERSION_ID:-}" != "24.04" ]]; then
  echo "Unsupported Ubuntu version: ${VERSION_ID:-unknown}. Use 22.04 or 24.04." >&2
  exit 1
fi

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo or as root." >&2
  exit 1
fi

echo "Installing Docker and Docker Compose plugin..."
apt-get update
apt-get install -y ca-certificates curl git gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  > /etc/apt/sources.list.d/docker.list

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

if ! id "${APP_USER}" >/dev/null 2>&1; then
  echo "Creating app user: ${APP_USER}"
  adduser --disabled-password --gecos "" "${APP_USER}"
fi
usermod -aG docker "${APP_USER}"

echo "Creating persistent directories..."
mkdir -p "${APP_DIR}"
mkdir -p "${DATA_DIR}/logs" "${DATA_DIR}/runtime" "${DATA_DIR}/token-store"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}" "${DATA_DIR}"
chmod 750 "${DATA_DIR}" "${DATA_DIR}/runtime" "${DATA_DIR}/token-store"

if [[ -n "${REPO_URL}" ]]; then
  if [[ -d "${APP_DIR}/.git" ]]; then
    echo "Repository already exists at ${APP_DIR}; skipping clone."
  else
    echo "Cloning repository into ${APP_DIR}..."
    sudo -u "${APP_USER}" git clone "${REPO_URL}" "${APP_DIR}"
  fi
else
  echo "No repo URL supplied; skipping clone."
fi

cat <<EOF

Bootstrap complete.

Next manual steps:
1. Open a new login shell so Docker group membership applies:
   sudo -iu ${APP_USER}

2. If not cloned yet, clone the repo:
   git clone <repo-url> ${APP_DIR}
   cd ${APP_DIR}

3. Create production .env manually from .env.cloud.example:
   cp .env.cloud.example .env
   chmod 600 .env
   nano .env

4. Deploy auth web:
   ./deploy/scripts/deploy_auth_web.sh

Do not put Kite access tokens in .env. Daily tokens belong in TOKEN_STORE_PATH.
EOF
