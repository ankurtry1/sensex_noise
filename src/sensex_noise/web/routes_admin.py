from __future__ import annotations

import secrets
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, status
from fastapi.responses import HTMLResponse

from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import Settings, load_settings
from sensex_noise.ops.results import build_results_summary
from sensex_noise.ops.worker_status import build_worker_summary
from sensex_noise.web.admin_session import ADMIN_SESSION_COOKIE, valid_admin_session


router = APIRouter(prefix="/admin", tags=["admin"])

_ADMIN_UI = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sensex Noise Admin</title>
  <style>
    :root { color-scheme: light dark; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    body { margin: 0; background: #f6f7f9; color: #15171a; }
    main { max-width: 1120px; margin: 0 auto; padding: 24px; }
    h1 { font-size: 24px; margin: 0 0 16px; }
    section { background: #fff; border: 1px solid #d9dee7; border-radius: 8px; padding: 16px; margin: 0 0 16px; }
    label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; }
    input { width: min(520px, 100%); padding: 9px 10px; border: 1px solid #aab3c2; border-radius: 6px; }
    button { border: 1px solid #1f5eff; background: #1f5eff; color: white; border-radius: 6px; padding: 9px 12px; margin: 8px 8px 0 0; cursor: pointer; }
    button.secondary { background: #fff; color: #1f5eff; }
    button.danger { border-color: #b42318; background: #b42318; }
    .hint { color: #586174; margin: 8px 0 0; line-height: 1.4; }
    .alert { border: 1px solid #f1c27d; background: #fff8eb; color: #583a00; border-radius: 6px; padding: 10px; margin-top: 12px; }
    pre { background: #101418; color: #e6edf3; padding: 12px; border-radius: 6px; overflow: auto; max-height: 420px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; }
    .metric { border: 1px solid #e1e5ec; border-radius: 6px; padding: 12px; }
    .metric b { display: block; font-size: 12px; color: #586174; margin-bottom: 6px; }
    @media (prefers-color-scheme: dark) {
      body { background: #0f1216; color: #e6edf3; }
      section { background: #171b21; border-color: #2b313b; }
      input, button.secondary { background: #0f1216; color: #e6edf3; border-color: #454d5a; }
      .hint { color: #aab3c2; }
      .alert { background: #2a2112; border-color: #6f521e; color: #f7d99b; }
      .metric { border-color: #2b313b; }
      .metric b { color: #aab3c2; }
    }
  </style>
</head>
<body>
<main>
  <h1>Sensex Noise Admin</h1>
  <section>
    <p class="hint">After Kite login, this page works automatically in the same browser. The admin token field is only a fallback for maintenance.</p>
    <label for="token">Admin Token Fallback</label>
    <input id="token" type="password" autocomplete="current-password" placeholder="Optional">
    <div>
      <button class="secondary" onclick="saveToken()">Save Token Locally</button>
      <button class="secondary" onclick="window.location.href='/kite/login'">Open Kite Login</button>
      <button class="secondary" onclick="refreshAll()">Refresh</button>
      <button onclick="sendCommand('start')">Start Worker</button>
      <button class="danger" onclick="sendCommand('stop')">Stop Worker</button>
    </div>
    <div id="notice" class="alert" style="display:none"></div>
  </section>
  <section>
    <h2>Status</h2>
    <div class="grid" id="metrics"></div>
  </section>
  <section>
    <h2>Results</h2>
    <pre id="results">Not loaded</pre>
  </section>
  <section>
    <h2>Raw Status</h2>
    <pre id="raw">Not loaded</pre>
  </section>
</main>
<script>
const tokenInput = document.getElementById("token");
tokenInput.value = localStorage.getItem("sensexAdminToken") || "";
function token() { return tokenInput.value.trim(); }
function saveToken() { localStorage.setItem("sensexAdminToken", token()); refreshAll(); }
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;","\\"":"&quot;","'":"&#39;"}[c]));
}
async function api(path, options = {}) {
  const headers = Object.assign({}, options.headers || {});
  if (token()) headers.Authorization = `Bearer ${token()}`;
  const res = await fetch(path, Object.assign({}, options, {headers, credentials: "same-origin"}));
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch { data = {raw: text}; }
  if (!res.ok) throw new Error(`${res.status} ${JSON.stringify(data)}`);
  return data;
}
function metric(label, value) {
  return `<div class="metric"><b>${escapeHtml(label)}</b><span>${escapeHtml(value)}</span></div>`;
}
function notice(message) {
  const box = document.getElementById("notice");
  if (!message) {
    box.style.display = "none";
    box.textContent = "";
    return;
  }
  box.textContent = message;
  box.style.display = "block";
}
async function refreshAll() {
  try {
    notice("");
    const status = await api("/admin/status");
    const results = await api("/admin/results");
    const worker = status.worker || {};
    document.getElementById("metrics").innerHTML = [
      metric("Today Token", status.token_store?.has_today_token),
      metric("Worker", worker.worker_state),
      metric("Trading Date", worker.trading_date),
      metric("Last Heartbeat", worker.last_heartbeat_at),
      metric("Market Tick Lines", results.market_ticks?.total_line_count),
      metric("Trade Tick Lines", results.trade_ticks?.total_line_count),
      metric("Trade Journal Lines", results.journals?.trades?.line_count),
      metric("Event Journal Lines", results.journals?.events?.line_count)
    ].join("");
    document.getElementById("raw").textContent = JSON.stringify(status, null, 2);
    document.getElementById("results").textContent = JSON.stringify(results, null, 2);
  } catch (err) {
    document.getElementById("raw").textContent = String(err);
    if (String(err).includes("401")) {
      notice("Session not active. Open Kite Login first, complete login, then return here. You can also paste ADMIN_TOKEN as a fallback.");
    }
  }
}
async function sendCommand(command) {
  try {
    notice("");
    const data = await api(`/admin/worker/${command}`, {method: "POST"});
    document.getElementById("raw").textContent = JSON.stringify(data, null, 2);
    setTimeout(refreshAll, 1500);
  } catch (err) {
    document.getElementById("raw").textContent = String(err);
    if (String(err).includes("401")) {
      notice("Session not active. Complete Kite Login first, then click Start Worker.");
    }
  }
}
refreshAll();
</script>
</body>
</html>
"""


def get_settings() -> Settings:
    return load_settings()


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
    x_admin_token: Annotated[str | None, Header()] = None,
    admin_session: Annotated[str | None, Cookie(alias=ADMIN_SESSION_COOKIE)] = None,
) -> Settings:
    expected = settings.admin_token.strip()
    if not expected:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ADMIN_TOKEN is not configured",
        )

    if valid_admin_session(settings, admin_session):
        return settings

    supplied = x_admin_token or ""
    if authorization:
        scheme, _, value = authorization.partition(" ")
        if scheme.lower() == "bearer":
            supplied = value.strip()

    if not supplied or not secrets.compare_digest(supplied, expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return settings


@router.get("/ui", response_class=HTMLResponse)
def admin_ui() -> str:
    return _ADMIN_UI


@router.get("/status")
def status_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    record = TokenStore(settings.token_store_path).read_today()
    return {
        "token_store": {
            "has_today_token": record is not None,
            "metadata": record.safe_metadata() if record is not None else None,
        },
        "worker": build_worker_summary(settings),
        "paths": {
            "data_dir": str(settings.data_dir),
            "logs_dir": str(settings.logs_dir),
            "runtime_dir": str(settings.runtime_dir),
            "token_store_path": str(settings.token_store_path),
        },
    }


@router.get("/worker/status")
def worker_status_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    return build_worker_summary(settings)


@router.post("/worker/check")
def worker_check_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    record = TokenStore(settings.token_store_path).read_today()
    worker = build_worker_summary(settings)
    worker_state = str(worker.get("worker_state") or "unknown")
    return {
        "token_store": {
            "has_today_token": record is not None,
            "metadata": record.safe_metadata() if record is not None else None,
        },
        "worker": worker,
        "ready_to_start": record is not None and worker_state not in {"starting", "running", "stopping"},
    }


@router.get("/results")
def results_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    return build_results_summary(settings)


def _queue_worker_command(settings: Settings, command: str) -> dict[str, object]:
    if command not in {"start", "stop"}:
        raise ValueError(f"unsupported command: {command}")
    command_dir = settings.runtime_dir / "commands"
    command_dir.mkdir(parents=True, exist_ok=True)
    path = command_dir / f"{command}.request"
    path.write_text(
        (
            "{\n"
            f'  "command": "{command}",\n'
            f'  "created_at": "{datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")}"\n'
            "}\n"
        ),
        encoding="utf-8",
    )
    return {
        "status": "queued",
        "command": command,
        "command_path": str(path),
        "dispatcher": "sensex-worker-command.path",
    }


@router.post("/worker/start")
def worker_start_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    worker = build_worker_summary(settings)
    if str(worker.get("worker_state") or "unknown") in {"starting", "running"}:
        return {"status": "skipped", "reason": "worker already starting/running", "worker": worker}
    return _queue_worker_command(settings, "start")


@router.post("/worker/stop")
def worker_stop_view(settings: Annotated[Settings, Depends(require_admin)]) -> dict[str, object]:
    return _queue_worker_command(settings, "stop")
