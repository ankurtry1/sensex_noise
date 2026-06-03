# Cloud VM Deployment Guide

This guide runs the Sensex Noise auth web service on a single Ubuntu VM with Docker Compose. It does not enable scheduler automation, monitoring, live trading changes, or database migration.

The market worker remains manual and opt-in until the cloud auth flow is verified.

## Assumptions

- Ubuntu 22.04 or 24.04 VM.
- Repository: `https://github.com/ankurtry1/sensex_noise.git`
- App directory on VM: `/opt/sensex-noise`
- Persistent data directory on VM: `/var/lib/sensex-noise`
- Production env file is created manually from `.env.cloud.example`.
- The FastAPI app runs inside Docker as `sensex_noise.web.app:app`.

## 1. Provision Ubuntu VM

Create a small Ubuntu 22.04 or 24.04 VM with at least:

- 1 vCPU
- 1-2 GB RAM
- 20 GB disk
- SSH access

SSH into the server:

```bash
ssh ubuntu@YOUR_SERVER_IP
```

Update base packages:

```bash
sudo apt-get update
sudo apt-get upgrade -y
```

## 2. Install Docker and Compose Plugin

Install Docker from the official Docker apt repository:

```bash
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

. /etc/os-release
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu ${VERSION_CODENAME} stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Check Docker:

```bash
sudo docker version
sudo docker compose version
```

## 3. Create App User

Create a dedicated app user:

```bash
sudo adduser --disabled-password --gecos "" sensexbot
sudo usermod -aG docker sensexbot
```

Create application and data directories:

```bash
sudo mkdir -p /opt/sensex-noise
sudo mkdir -p /var/lib/sensex-noise/logs
sudo mkdir -p /var/lib/sensex-noise/runtime
sudo mkdir -p /var/lib/sensex-noise/token-store
sudo chown -R sensexbot:sensexbot /opt/sensex-noise /var/lib/sensex-noise
sudo chmod 750 /var/lib/sensex-noise /var/lib/sensex-noise/runtime /var/lib/sensex-noise/token-store
```

Start a new shell as the app user:

```bash
sudo -iu sensexbot
```

## 4. Clone Repository

Clone the repo:

```bash
git clone https://github.com/ankurtry1/sensex_noise.git /opt/sensex-noise
cd /opt/sensex-noise
```

If the repository is private, configure a GitHub deploy key or use an authenticated GitHub URL before cloning.

## 5. Create Production Env File

Create `.env` from the cloud example:

```bash
cp .env.cloud.example .env
chmod 600 .env
nano .env
```

Required production values:

```env
KITE_API_KEY=
KITE_API_SECRET=
ADMIN_TOKEN=
APP_BASE_URL=https://your-domain.example
DATA_DIR=/var/lib/sensex-noise
LOGS_DIR=/var/lib/sensex-noise/logs
RUNTIME_DIR=/var/lib/sensex-noise/runtime
TOKEN_STORE_PATH=/var/lib/sensex-noise/token-store/kite_access_token.json
```

Do not add `KITE_ACCESS_TOKEN` to `.env`. Daily access tokens are written to `TOKEN_STORE_PATH` after manual Kite authentication.

Generate a strong admin token:

```bash
openssl rand -hex 32
```

Use that value for `ADMIN_TOKEN`.

## 6. Build Image

Use the production override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
```

## 7. Start Auth Web

Start only the auth web service:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d auth-web
```

The production override binds the service to `127.0.0.1:8000` on the VM. This is intended for a later Nginx reverse proxy or SSH tunnel.

## 8. Check Health

From the VM:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## 9. Check Admin Status

From the VM:

```bash
set -a
. ./.env
set +a

curl -H "Authorization: Bearer $ADMIN_TOKEN" http://127.0.0.1:8000/admin/status
```

Expected behavior:

- Shows whether today's Kite token exists.
- Shows configured data/runtime/log/token-store paths.
- Does not show the access token, Kite API secret, or admin token.

## 10. View Logs

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f auth-web
```

Tail recent logs:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml logs --tail=100 auth-web
```

## 11. Stop Auth Web

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml down
```

## 12. Manual Kite Auth Flow

Set the Kite developer console redirect URL to the deployed callback URL:

```text
https://your-domain.example/kite/callback
```

After the auth web service is running, open:

```text
https://your-domain.example/kite/login
```

Complete manual Kite login. On callback, the app exchanges the request token and stores the daily access token at:

```text
/var/lib/sensex-noise/token-store/kite_access_token.json
```

The token file should remain on the server and must not be copied into Git.

## 13. Manual Market Worker

Do not run this until cloud auth is verified and market hours behavior is intended.

Run the worker once manually:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile worker run --rm market-worker
```

The worker reads today's token from `TOKEN_STORE_PATH`. If the token is missing or stale, it exits without starting the market runtime.

## 14. Update Deployment

Pull new code and rebuild:

```bash
cd /opt/sensex-noise
git pull --ff-only
docker compose -f docker-compose.yml -f docker-compose.prod.yml build
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d auth-web
```

## 15. Later Nginx and HTTPS Plan

This phase does not implement Nginx or HTTPS. Later, use this outline:

1. Point `your-domain.example` DNS `A` record to the VM public IP.
2. Install Nginx:

   ```bash
   sudo apt-get install -y nginx
   ```

3. Reverse proxy HTTPS traffic to the local auth web service:

   ```nginx
   server {
       server_name your-domain.example;

       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. Install Certbot and issue a certificate:

   ```bash
   sudo apt-get install -y certbot python3-certbot-nginx
   sudo certbot --nginx -d your-domain.example
   ```

5. Set `APP_BASE_URL=https://your-domain.example` in `.env`.
6. Set Kite developer console redirect URL to:

   ```text
   https://your-domain.example/kite/callback
   ```

7. Restart auth web:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d auth-web
   ```

## 16. Files That Must Stay Out of Git

Do not commit:

- `.env`
- `.env.*` except committed example files
- runtime token-store files
- `/var/lib/sensex-noise`
- `runtime/`
- `logs/`
- `data/tape/`
- refreshed `data/instruments.csv`
- generated market data
