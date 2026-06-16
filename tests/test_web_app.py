from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from sensex_noise.auth.kite_auth import KiteSession
from sensex_noise.auth.token_store import TokenStore
from sensex_noise.config import load_settings
from sensex_noise.web.admin_session import ADMIN_SESSION_COOKIE, new_admin_session
from sensex_noise.web import routes_kite
from sensex_noise.web.app import app


def _seed_web_env(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KITE_API_KEY", "test-api-key")
    monkeypatch.setenv("KITE_API_SECRET", "test-api-secret")
    monkeypatch.setenv("ADMIN_TOKEN", "admin-secret")
    monkeypatch.setenv("APP_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ENABLE_SENSEX_OPTION_TAPE_RECORDER", "false")
    monkeypatch.setenv("SENSEX_TAPE_WRITE_LEGACY_OPTIONS_LOG", "true")
    monkeypatch.setenv("BACKGROUND_TICK_QUEUE_MAXSIZE", "20000")
    monkeypatch.setenv("JOURNAL_QUEUE_MAXSIZE", "50000")


def test_health_is_public(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_status_requires_admin_token(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    client = TestClient(app)

    unauthorized = client.get("/admin/status")
    authorized = client.get("/admin/status", headers={"Authorization": "Bearer admin-secret"})

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    payload = authorized.json()
    assert payload["token_store"]["has_today_token"] is False
    assert payload["token_store"]["metadata"] is None
    assert payload["worker"]["worker_state"] == "unknown"
    assert payload["worker"]["token_present"] is False
    assert payload["paths"]["data_dir"] == str(tmp_path)
    assert "test-api-secret" not in str(payload)
    assert "admin-secret" not in str(payload)


def test_admin_status_accepts_kite_login_session_cookie(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    client = TestClient(app)
    client.cookies.set(ADMIN_SESSION_COOKIE, new_admin_session(load_settings()))

    response = client.get("/admin/status")

    assert response.status_code == 200
    assert response.json()["token_store"]["has_today_token"] is False


def test_admin_status_returns_503_when_admin_token_missing(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    monkeypatch.setenv("ADMIN_TOKEN", "")

    response = TestClient(app).get("/admin/status")

    assert response.status_code == 503


def test_admin_worker_status_is_protected_and_secret_free(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    worker_status_path = tmp_path / "runtime" / "worker_status.json"
    worker_status_path.parent.mkdir(parents=True)
    worker_status_path.write_text(
        '{"worker_state": "running", "pid": 321, "token_present": true, "trading_date": "2026-06-08"}',
        encoding="utf-8",
    )
    client = TestClient(app)

    unauthorized = client.get("/admin/worker/status")
    response = client.get("/admin/worker/status", headers={"X-Admin-Token": "admin-secret"})

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    payload = response.json()
    assert payload["worker_state"] == "running"
    assert payload["pid"] == 321
    assert payload["token_present"] is False
    assert "test-api-secret" not in str(payload)
    assert "admin-secret" not in str(payload)


def test_admin_worker_check_reports_readiness(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    client = TestClient(app)

    response = client.post("/admin/worker/check", headers={"Authorization": "Bearer admin-secret"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_store"]["has_today_token"] is False
    assert payload["ready_to_start"] is False


def test_admin_ui_serves_control_page(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)

    response = TestClient(app).get("/admin/ui")

    assert response.status_code == 200
    assert "Sensex Noise Admin" in response.text
    assert "Start Worker" in response.text
    assert "Stop Worker" in response.text
    assert "Open Kite Login" in response.text
    assert "admin-secret" not in response.text


def test_admin_worker_start_stop_queue_command_files(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    client = TestClient(app)
    headers = {"Authorization": "Bearer admin-secret"}

    start = client.post("/admin/worker/start", headers=headers)
    stop = client.post("/admin/worker/stop", headers=headers)

    assert start.status_code == 200
    assert stop.status_code == 200
    assert start.json()["status"] == "queued"
    assert stop.json()["status"] == "queued"
    assert (tmp_path / "runtime" / "commands" / "start.request").exists()
    assert (tmp_path / "runtime" / "commands" / "stop.request").exists()
    assert "admin-secret" not in start.text
    assert "admin-secret" not in stop.text


def test_admin_results_summarizes_tick_and_trade_files(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    tick_dir = tmp_path / "logs" / "ticks" / today
    trade_tick_dir = tmp_path / "logs" / "trade_ticks" / today
    tick_dir.mkdir(parents=True)
    trade_tick_dir.mkdir(parents=True)
    (tick_dir / "index.jsonl").write_text('{"a": 1}\n{"a": 2}\n', encoding="utf-8")
    (trade_tick_dir / "trade-1.jsonl").write_text('{"b": 1}\n', encoding="utf-8")
    (tmp_path / "logs").mkdir(exist_ok=True)
    (tmp_path / "logs" / "trades.jsonl").write_text('{"trade": 1}\n', encoding="utf-8")
    client = TestClient(app)

    response = client.get("/admin/results", headers={"Authorization": "Bearer admin-secret"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["trading_date"] == today
    assert payload["market_ticks"]["total_line_count"] == 2
    assert payload["trade_ticks"]["total_line_count"] == 1
    assert payload["journals"]["trades"]["line_count"] == 1


def test_kite_login_redirect_sets_signed_state(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    monkeypatch.setattr(routes_kite, "build_login_url", lambda api_key: "https://kite.test/login?api_key=abc")

    response = TestClient(app).get("/kite/login", follow_redirects=False)

    assert response.status_code == 307
    assert "https://kite.test/login?api_key=abc&state=" in response.headers["location"]
    assert "kite_auth_state=" in response.headers["set-cookie"]


def test_kite_callback_stores_token_without_returning_secret(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)
    monkeypatch.setattr(routes_kite, "build_login_url", lambda api_key: "https://kite.test/login?api_key=abc")

    def fake_exchange_request_token(*, api_key: str, api_secret: str, request_token: str) -> KiteSession:
        assert api_key == "test-api-key"
        assert api_secret == "test-api-secret"
        assert request_token == "request-token-1"
        return KiteSession(access_token="stored-secret-token", user_id="USER123")

    monkeypatch.setattr(routes_kite, "exchange_request_token", fake_exchange_request_token)
    client = TestClient(app)
    login_response = client.get("/kite/login", follow_redirects=False)
    state = login_response.cookies["kite_auth_state"]

    response = client.get(f"/kite/callback?request_token=request-token-1&state={state}", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/ui?kite=ok"
    assert "stored-secret-token" not in response.text
    assert ADMIN_SESSION_COOKIE in response.cookies
    assert TokenStore(tmp_path / "runtime" / "kite_access_token.json").read_today().access_token == "stored-secret-token"

    admin_response = client.get("/admin/status")
    assert admin_response.status_code == 200
    assert admin_response.json()["token_store"]["metadata"]["user_id"] == "USER123"


def test_kite_callback_rejects_missing_state(monkeypatch, tmp_path) -> None:
    _seed_web_env(monkeypatch, tmp_path)

    response = TestClient(app).get("/kite/callback?request_token=request-token-1")

    assert response.status_code == 400
